"""'A human visited the website': one Slack line per stranger per day.

Called from lambda_handler after every response. Almost every request is
rejected by pure string checks before any I/O, so the hot path costs nothing;
only a request that looks like a person costs DynamoDB calls.

The signal (measured on a week of access logs, 2026-10-08..15: 12 alerts,
at most 4 a day). Humans fetch a page's favicon, or follow a link: a 200 page
whose Referer is another page of this site. Scanners send a Referer too, but
their paths 404, so status 200 is required. Bots that request one path and
leave never trigger either way.

A favicon counts only when its Referer is a page of this site (re-measured
over 2026-09-24..10-24: of 41 non-owner favicon fetches that passed the UA
rules, the 16 with a page Referer look human; the 25 without one, or with the
favicon itself as Referer, were scanners, census probes and cloud VMs fetching
it to fingerprint the site).

Enrichment, deterministic and only on a would-be alert: reverse DNS of the
client IP, labelled by network when the name says (GCP, AWS, ...). A name
that belongs to a scanning project suppresses the alert; a cloud name only
labels it, since a person on a VPN can come from one.

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
  - a hard cap of alerts a day, then one 'capped' message, whatever the
    detection thinks. It does not rely on the WAF still blocking scanners
    upstream. This now lives in visitor_digest.py, which does the sending.

This module only records the visitor (a 'pending' row): it fires seconds into
a visit, too early to say what the visit was. visitor_digest.py sends the alert
once the IP goes quiet. Severity is `info` (Slack only, no xMatters): this must
never wake anyone.
"""
import re
import socket
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
from datetime import datetime, timedelta, timezone

TABLE = 'mywebsite-visitor-alerts'
SITE_HOST = 'petergrecian.co.uk'

_FAVICONS = frozenset({'/favicon.ico', '/favicon.png', '/favicon.svg'})
_BOT_UA = re.compile(
    r'bot|crawl|spider|slurp|curl|wget|python|go-http|java|okhttp|axios|'
    r'node-fetch|httpx|aiohttp|libwww|headless|lighthouse|petal|semrush|'
    r'censys|scan|sniff|research|preview|facebookexternal|calendaralarm|'
    r'pi-fleet|inspection|googleother|google-|associationservice|redirectmap|'
    r'measurement|census',
    re.I)
_CRAWLER_PREFIXES = ('66.249.',)

# Reverse-DNS suffix -> network label for the Slack line.
_NETWORKS = (('.googleusercontent.com', 'GCP'), ('.amazonaws.com', 'AWS'),
             ('.azure.com', 'Azure'), ('.cloudapp.net', 'Azure'),
             ('.linodeusercontent.com', 'Linode'), ('.vultrusercontent.com', 'Vultr'),
             ('.your-server.de', 'Hetzner'), ('.ovh.net', 'OVH'),
             ('.digitalocean.com', 'DigitalOcean'), ('.oraclecloud.com', 'Oracle'),
             ('.googlebot.com', 'Googlebot'))
# Reverse-DNS names of scanning projects: these never alert.
_SCANNER_RDNS = re.compile(
    r'internet-census|internet-measurement|censys|shodan|binaryedge|'
    r'shadowserver|stretchoid|onyphe|leakix|criminalip|recyber|'
    r'scan|probe|crawl|googlebot', re.I)
RDNS_TIMEOUT = 1.0

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
    ref = urllib.parse.urlparse(_header(headers, 'Referer'))
    from_page = (ref.hostname or '').endswith(SITE_HOST) \
        and (ref.path or '/') not in _FAVICONS
    if route in _FAVICONS:
        return 'favicon' if from_page else None
    if 'text/html' in ctype and from_page and (ref.path or '/') != route:
        return 'link'
    return None


def _rdns(ip):
    """Reverse DNS name of ip, or '' if none or it took over RDNS_TIMEOUT."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(socket.gethostbyaddr, ip).result(RDNS_TIMEOUT)[0]
    except Exception:
        return ''
    finally:
        pool.shutdown(wait=False)


def describe(ip):
    """(rdns, network label, is_scanner) for a client IP."""
    name = _rdns(ip)
    net = next((label for sfx, label in _NETWORKS if name.lower().endswith(sfx)), '')
    return name, net, bool(name and _SCANNER_RDNS.search(name))


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
    item = {'day': day, 'ip': ip, 'kind': kind, 'path': route,
            'ts': now.isoformat(), 'ttl': ttl}
    try:
        table.put_item(Item=item, ConditionExpression='attribute_not_exists(ip)')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return
        raise

    # After the dedupe, so a scanner costs one lookup a day.
    name, net, scanner = describe(ip)
    if scanner:
        print(f'visitor alert suppressed: {ip} is {name}')
        return

    # Nothing is sent from here: the visit has only just begun. visitor_digest
    # sends this row once the IP has gone quiet, with the pages it saw. City and
    # region arrive only with Cloudflare's visitor location headers switched on.
    table.put_item(Item={
        **item, 'pending': 1, 'rdns': name, 'net': net,
        'country': _header(headers, 'CF-IPCountry'),
        'city': _header(headers, 'CF-IPCity'),
        'region': _header(headers, 'CF-Region'),
        'ua': _header(headers, 'User-Agent')[:300]})
