"""Send each visitor alert once the visit is over, saying what the visit was.

lambda/visitor_alert.py spots a person on the first favicon or link-follow,
seconds into the visit, when there is nothing to report yet. It records a
'pending' row. This function runs every 15 minutes (its own Lambda, see
terraform/visitor_digest.tf), and for each pending row whose IP has been quiet
for QUIET, reads that IP's requests back from the access log and sends one
alert: how many pages, which ones, how long, how they arrived, where from.

Only visits that look like a person are sent (see looks_human), and only public
pages count towards that or appear in the alert. The rest are printed to this
function's log, so the rule can be checked against them.

The daily cap lives here, because this is what sends. Severity stays `info`.
"""
import ipaddress
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TABLE = 'mywebsite-visitor-alerts'
LOG_GROUP = '/aws/lambda/mywebsite'
ALERT_ENDPOINT = 'https://b5wgk4mp4g.execute-api.eu-west-1.amazonaws.com/alert'
DAILY_CAP = 10
SITE_HOST = 'petergrecian.co.uk'
LONDON = ZoneInfo('Europe/London')

QUIET = timedelta(minutes=30)     # no requests for this long: the visit is over
MAX_WAIT = timedelta(hours=3)     # report a very long visit anyway
LOOKBACK = timedelta(hours=1)     # requests before the signal belong to the visit
MAX_PAGES_LISTED = 12
CONTENTS_TABLE = 'mywebsite-contents'
# Not public, whatever the contents table says: these ask for a password or
# are not on it at all. The table's auth_required rows are added at run time.
ALWAYS_PRIVATE = ('/my-contents', '/calendaralarm', '/glacier', '/gardencam',
                  '/groceries', '/memspeed', '/srfcplus', '/ytpods')
MIN_DISTINCT_PAGES = 2
MIN_MEDIAN_GAP_S = 5

_ASSET = re.compile(
    r'\.(png|jpe?g|gif|webp|svg|ico|css|js|map|woff2?|webmanifest|json|txt|xml)$'
    r'|/favicon|apple-touch|/thumbs/', re.I)


def _browser(ua):
    """'Chrome 117 on Windows' from a User-Agent, or the UA itself if unknown."""
    os_name = next((name for token, name in (
        ('Windows', 'Windows'), ('iPhone', 'iPhone'), ('iPad', 'iPad'),
        ('Android', 'Android'), ('CrOS', 'ChromeOS'), ('Mac OS X', 'Mac'),
        ('Linux', 'Linux')) if token in ua), '')
    for token, name in (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'),
                        ('Chrome/', 'Chrome'), ('Version/', 'Safari')):
        m = re.search(re.escape(token) + r'(\d+)', ua)
        if m:
            return f'{name} {m.group(1)}' + (f' on {os_name}' if os_name else '')
    return ua[:160] or 'unknown'


def _span(seconds):
    if seconds < 60:
        return f'{int(seconds)} s'
    if seconds < 3600:
        return f'{round(seconds / 60)} min'
    return f'{seconds / 3600:.1f} h'


def private_paths(contents_table):
    """Paths that are not public: ALWAYS_PRIVATE plus the auth_required rows."""
    paths = set(ALWAYS_PRIVATE)
    try:
        kwargs = {}
        while True:
            resp = contents_table.scan(**kwargs)
            paths |= {'/' + str(i['path']).strip('/') for i in resp.get('Items', [])
                      if i.get('auth_required') and i.get('path')}
            if not resp.get('LastEvaluatedKey'):
                return paths
            kwargs['ExclusiveStartKey'] = resp['LastEvaluatedKey']
    except Exception as e:
        print(f'contents table unreadable, using ALWAYS_PRIVATE only: {e}')
        return paths


def _is_page(r, private):
    """A public page that was really served: no assets, failures or private pages."""
    path = r.get('path', '')
    return (r.get('status', 500) < 400 and not _ASSET.search(path)
            and not any(path == p or path.startswith(p + '/') for p in private))


def summarise(requests, private=()):
    """Page list, counts and arrival from one IP's access-log records, in time order."""
    pages = [r['path'] for r in requests if _is_page(r, private)]
    trail = [p for i, p in enumerate(pages) if i == 0 or pages[i - 1] != p]
    arrived = next((r['ref'] for r in requests if r.get('ref')
                    and not (urllib.parse.urlparse(r['ref']).hostname or '').endswith(SITE_HOST)),
                   '')
    times = [datetime.fromisoformat(r['ts']) for r in requests]
    page_times = [datetime.fromisoformat(r['ts']) for r in requests if _is_page(r, private)]
    gaps = [(b - a).total_seconds() for a, b in zip(page_times, page_times[1:])]
    return {
        'median_gap': statistics.median(gaps) if gaps else 0,
        'pages': len(pages),
        'distinct': len(set(pages)),
        'trail': trail,
        'requests': len(requests),
        'failed': sum(1 for r in requests if r.get('status', 500) >= 400),
        'first': min(times) if times else None,
        'last': max(times) if times else None,
        'arrived': arrived,
    }


def looks_human(row, s):
    """A person reads: two different public pages, seconds apart, not from a data centre.

    Measured on 396 browser-like visits, 2026-10-17..27. Of 88 with two or more
    page loads, 77 had a median gap under 5 s (crawlers walking the links). The
    survivors that reloaded one page, or came from cloud addresses, were
    machines too. An outside Referer proved worthless as a sign of a person: of
    15 visits, most named referrer-spam sites or came from AWS.

    Blind spot: one page read for ten minutes looks the same from here as a
    scanner's one fetch, so a single-page reader is never reported.
    """
    return (s['distinct'] >= MIN_DISTINCT_PAGES
            and s['median_gap'] >= MIN_MEDIAN_GAP_S
            and not row.get('net'))


def message(row, s, owner, n):
    """(title, detail) for a finished visit."""
    place = ', '.join(x for x in (row.get('city'), row.get('region'), row.get('country')) if x) \
        or 'unknown location'
    secs = (s['last'] - s['first']).total_seconds() if s['first'] else 0
    plural = '' if s['pages'] == 1 else 's'
    # The IP keeps the title unique: the alerting Lambda drops a repeated title
    # within the hour, and two one-page visits from one country would collide.
    title = f"Website visitor: {s['pages']} page{plural} in {_span(secs)}, " \
            f"{place} ({row['ip']})"
    trail = s['trail'][:MAX_PAGES_LISTED]
    more = len(s['trail']) - len(trail)
    network = ', '.join(x for x in (row.get('rdns'), row.get('net'), owner) if x) or 'unknown'
    when = '?'
    if s['first']:
        when = f"{s['first'].astimezone(LONDON):%H:%M}-{s['last'].astimezone(LONDON):%H:%M}"
    lines = [
        'Pages: ' + (' > '.join(trail) + (f' > {more} more' if more > 0 else '') if trail
                     else 'none (only ' + row.get('path', '?') + ')'),
        f"Arrived from: {s['arrived'] or 'no referrer (typed, bookmark, or hidden)'}",
        f"Network: {network}",
        f"Browser: {_browser(row.get('ua', ''))}",
        f"Time: {when} London, {s['requests']} requests"
        + (f", {s['failed']} failed" if s['failed'] else ''),
        f"{n}/{DAILY_CAP} visitor alerts today",
    ]
    return title[:150], '\n'.join(lines)


def _network_owner(ip):
    """The registered owner of an IP from the public RDAP registry, or ''."""
    try:
        with urllib.request.urlopen(f'https://rdap.org/ip/{ip}', timeout=4) as r:
            d = json.load(r)
        for ent in d.get('entities', []):
            for item in (ent.get('vcardArray') or [None, []])[1]:
                if item[0] == 'fn':
                    return item[3]
        return d.get('name', '')
    except Exception as e:
        print(f'rdap failed for {ip}: {e}')
        return ''


def _requests(logs, ip, start, end):
    """Access-log records for ip between start and end, oldest first."""
    kwargs = {
        'logGroupName': LOG_GROUP,
        'startTime': int(start.timestamp() * 1000),
        'endTime': int(end.timestamp() * 1000),
        'filterPattern': f'{{ ($.evt = "access") && ($.ip = "{ip}") }}',
    }
    rows = []
    while True:
        resp = logs.filter_log_events(**kwargs)
        for ev in resp.get('events', []):
            try:
                rows.append(json.loads(ev['message'][ev['message'].index('{'):]))
            except ValueError:
                pass
        if not resp.get('nextToken'):
            break
        kwargs['nextToken'] = resp['nextToken']
    return sorted(rows, key=lambda r: r['ts'])


def _send(title, detail):
    payload = {'source': 'mywebsite', 'severity': 'info', 'title': title}
    if detail:
        payload['detail'] = detail
    req = urllib.request.Request(
        ALERT_ENDPOINT, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def _pending(table, day):
    kwargs = {'KeyConditionExpression': '#d = :d',
              'ExpressionAttributeNames': {'#d': 'day'},   # DAY is reserved
              'ExpressionAttributeValues': {':d': day}}
    while True:
        resp = table.query(**kwargs)
        for item in resp.get('Items', []):
            if item.get('pending'):
                yield item
        if not resp.get('LastEvaluatedKey'):
            return
        kwargs['ExclusiveStartKey'] = resp['LastEvaluatedKey']


def _claim(table, row):
    """Take the row off pending. False if another run already did."""
    from botocore.exceptions import ClientError
    try:
        table.update_item(Key={'day': row['day'], 'ip': row['ip']},
                          UpdateExpression='REMOVE pending',
                          ConditionExpression='attribute_exists(pending)')
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False
        raise


def _take_cap_slot(table, day, ttl):
    """Count this alert against the day. None once the cap and its notice are used."""
    from botocore.exceptions import ClientError
    try:
        return table.update_item(
            Key={'day': day, 'ip': '#count'},
            UpdateExpression='SET #ttl = :ttl ADD #n :one',
            ConditionExpression='attribute_not_exists(#n) OR #n <= :cap',
            ExpressionAttributeNames={'#ttl': 'ttl', '#n': 'n'},   # TTL is reserved
            ExpressionAttributeValues={':one': 1, ':cap': DAILY_CAP, ':ttl': ttl},
            ReturnValues='UPDATED_NEW')['Attributes']['n']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return None
        raise


def process(table, logs, now, owner_of=_network_owner, send=_send, private=lambda: ()):
    """Send every visit that has finished. One bad row never stops the rest.

    `private` is called only when there is a pending row, so an idle run reads
    nothing but the alerts table.
    """
    today = now.astimezone(LONDON)
    days = [(today - timedelta(days=d)).strftime('%Y-%m-%d') for d in (1, 0)]
    rows = [row for day in days for row in sorted(_pending(table, day), key=lambda r: r['ts'])]
    if not rows:
        return
    private_set = private()
    for row in rows:
        try:
            _process_row(table, logs, row, now, owner_of, send, private_set)
        except Exception as e:
            print(f"visitor digest failed for {row.get('ip')}: {e}")


def _process_row(table, logs, row, now, owner_of, send, private=()):
    ip = row['ip']
    try:
        ipaddress.ip_address(ip)    # X-Forwarded-For can be forged by the client
    except ValueError:
        print(f'visitor digest dropped a malformed ip: {ip[:60]!r}')
        _claim(table, row)
        return
    seen = datetime.fromisoformat(row['ts'])
    requests = _requests(logs, ip, seen - LOOKBACK, now)
    last = datetime.fromisoformat(requests[-1]['ts']) if requests else seen
    if now - last < QUIET and now - seen < MAX_WAIT:
        return          # still browsing: look again next run
    if not _claim(table, row):
        return
    s = summarise(requests, private)
    if not looks_human(row, s):
        print(f"visitor held, not human-looking: {ip} {row.get('country', '')} "
              f"{row.get('net', '')} pages={s['pages']} distinct={s['distinct']} "
              f"median_gap={s['median_gap']:.1f}s trail={s['trail'][:6]}")
        return
    n = _take_cap_slot(table, row['day'], int(row['ttl']))
    if n is None:
        return
    if n > DAILY_CAP:
        send(f"Visitor alerts capped at {DAILY_CAP} for {row['day']}; "
             f"the rest of the day is in the access log.", '')
        return
    owner = '' if row.get('rdns') and row.get('net') else owner_of(ip)
    send(*message(row, s, owner, n))


def lambda_handler(event, context):
    import boto3
    region = os.environ.get('AWS_REGION', 'eu-west-1')
    dynamodb = boto3.resource('dynamodb', region_name=region)
    process(dynamodb.Table(TABLE), boto3.client('logs', region_name=region),
            datetime.now(timezone.utc),
            private=lambda: private_paths(dynamodb.Table(CONTENTS_TABLE)))
