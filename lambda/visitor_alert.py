"""'A human visited the website': one Slack line per stranger per day.

Called from lambda_handler after every response. Almost every request is
rejected by pure string checks before any I/O, so the hot path costs nothing;
only a request that looks like a person costs DynamoDB calls.

The signal (measured on a week of access logs, 2026-10-08..15: 12 alerts,
at most 4 a day). Humans fetch a page's favicon, or follow a link: a 200 page
whose Referer is another page of this site. Scanners send a Referer too, but
their paths 404, so status 200 is required. Bots that request one path and
leave never trigger either way.

Excluded by rule, before the signal is looked at:
  - anything without a browser UA, or with a bot/tool token: this covers the
    calendaralarm poller, pi-fleet reporting, the strand startup probe
    (curl), and the crawlers that do say so;
  - Googlebot's range 66.249.x, whose Nexus 5X UA carries no bot token;
  - the owner. Any request that authenticated (Authorization header, response
    not 401) marks its client IP as the owner's for the day; rows with day
    'owner' are permanent owner IPs, seeded by hand and kept out of git
    because the repo is public.

Two suppression rules, ruled by towhom 2026-10-15:
  - dedupe: one alert per client IP per London day, by conditional put.
    The client IP is the FIRST entry of X-Forwarded-For, never the chain:
    the Cloudflare hop rotates per request.
  - a hard cap of DAILY_CAP alerts a day, then one 'capped' message, counted
    by a conditional increment, whatever the detection thinks. It does not
    rely on the WAF still blocking scanners upstream.

Severity is `info` (Slack only, no xMatters): this must never wake anyone.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TABLE = 'mywebsite-visitor-alerts'
ALERT_ENDPOINT = 'https://b5wgk4mp4g.execute-api.eu-west-1.amazonaws.com/alert'
DAILY_CAP = 10
SITE_HOST = 'petergrecian.co.uk'

_FAVICONS = frozenset({'/favicon.ico', '/favicon.png', '/favicon.svg'})
_BOT_UA = re.compile(
    r'bot|crawl|spider|slurp|curl|wget|python|go-http|java|okhttp|axios|'
    r'node-fetch|httpx|aiohttp|libwww|headless|lighthouse|petal|semrush|'
    r'censys|scan|sniff|research|preview|facebookexternal|calendaralarm|'
    r'pi-fleet|inspection|googleother|google-|associationservice|redirectmap',
    re.I)
_CRAWLER_PREFIXES = ('66.249.',)

# Per-container memo of owner IPs already written today, so an authenticated
# session costs one put per container, not one per request.
_OWNER_MARKED = set()


def _header(headers, name):
    return headers.get(name) or headers.get(name.lower()) or ''


def client_ip(headers):
    return _header(headers, 'X-Forwarded-For').split(',')[0].strip()


def _london_day(now):
    from zoneinfo import ZoneInfo
    return now.astimezone(ZoneInfo('Europe/London')).strftime('%Y-%m-%d')


def signal(route, status, headers, ctype='text/html'):
    """'favicon' or 'link' if this request looks like a person, else None.

    'link' needs an HTML response: a manifest or icon fetch carries the
    page's Referer too, and is the browser, not a click.
    """
    if status != 200:
        return None
    ua = _header(headers, 'User-Agent')
    if not ua.startswith('Mozilla/') or _BOT_UA.search(ua):
        return None
    ip = client_ip(headers)
    if not ip or ip.startswith(_CRAWLER_PREFIXES):
        return None
    if route in _FAVICONS:
        return 'favicon'
    ref = urllib.parse.urlparse(_header(headers, 'Referer'))
    if 'text/html' in ctype and (ref.hostname or '').endswith(SITE_HOST) \
            and (ref.path or '/') != route:
        return 'link'
    return None


def check(event, route, response, dynamodb_resource):
    """Entry point. Never raises: an alert must never break a page."""
    try:
        headers = event.get('headers') or {}
        status = (response or {}).get('statusCode', 500)
        now = datetime.now(timezone.utc)
        if _header(headers, 'Authorization') and status != 401:
            _mark_owner(dynamodb_resource, client_ip(headers), now)
            return
        rh = (response or {}).get('headers') or {}
        kind = signal(route, status, headers, rh.get('Content-Type') or rh.get('content-type') or '')
        if kind:
            _maybe_alert(dynamodb_resource, headers, route, kind, now)
    except Exception as e:
        print(f'visitor alert failed: {e}')


def _mark_owner(dynamodb_resource, ip, now):
    day = _london_day(now)
    if not ip or (day, ip) in _OWNER_MARKED:
        return
    dynamodb_resource().Table(TABLE).put_item(Item={
        'day': day, 'ip': ip, 'kind': 'owner',
        'ttl': int((now + timedelta(days=3)).timestamp())})
    _OWNER_MARKED.add((day, ip))


def _maybe_alert(dynamodb_resource, headers, route, kind, now):
    from botocore.exceptions import ClientError
    table = dynamodb_resource().Table(TABLE)
    ip = client_ip(headers)
    day = _london_day(now)
    ttl = int((now + timedelta(days=3)).timestamp())

    if 'Item' in table.get_item(Key={'day': 'owner', 'ip': ip}):
        return
    # Dedupe: the first trigger of the day for this IP wins the put. An owner
    # row for today (written on authentication) also blocks it.
    try:
        table.put_item(
            Item={'day': day, 'ip': ip, 'kind': kind, 'path': route,
                  'ts': now.isoformat(), 'ttl': ttl},
            ConditionExpression='attribute_not_exists(ip)')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return
        raise

    # Cap: increment the day's counter only while it is at most DAILY_CAP.
    # Alerts 1..DAILY_CAP go out; number DAILY_CAP+1 sends one 'capped'
    # line; after that the condition fails and nothing is sent.
    try:
        n = table.update_item(
            Key={'day': day, 'ip': '#count'},
            UpdateExpression='SET #ttl = :ttl ADD #n :one',
            ConditionExpression='attribute_not_exists(#n) OR #n <= :cap',
            ExpressionAttributeNames={'#ttl': 'ttl', '#n': 'n'},   # TTL is reserved
            ExpressionAttributeValues={':one': 1, ':cap': DAILY_CAP, ':ttl': ttl},
            ReturnValues='UPDATED_NEW')['Attributes']['n']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return
        raise

    if n > DAILY_CAP:
        _send(f'Visitor alerts capped at {DAILY_CAP} for {day}; '
              f'the rest of today is in the access log.', '')
        return
    country = _header(headers, 'CF-IPCountry')
    ref = _header(headers, 'Referer')
    ua = _header(headers, 'User-Agent')
    _send(f'A visitor on www.petergrecian.co.uk: {route}'
          + (f' ({country})' if country else ''),
          f'{kind} | ip {ip} | ref {ref or "-"} | ua {ua[:160]} | {n}/{DAILY_CAP} today')


def _send(title, detail):
    payload = {'source': 'mywebsite', 'severity': 'info', 'title': title}
    if detail:
        payload['detail'] = detail
    req = urllib.request.Request(
        ALERT_ENDPOINT, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=3) as r:
        r.read()
