"""visitor_alert + visitor_digest: the signal, the owner rule, dedupe, the
daily cap, and the alert sent once a visit is over.

A fake table stands in for DynamoDB, implementing just the calls the modules
rely on, and a fake log client for CloudWatch; sending is captured, so no test
can post a real alert.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError

BROWSER = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15'
PAGE = 'https://www.petergrecian.co.uk/'


def _conditional_failed():
    return ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'op')


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key):
        item = self.items.get((Key['day'], Key['ip']))
        return {'Item': item} if item else {}

    def put_item(self, Item, ConditionExpression=None):
        key = (Item['day'], Item['ip'])
        if ConditionExpression and key in self.items:
            raise _conditional_failed()
        self.items[key] = dict(Item)

    def query(self, ExpressionAttributeValues, **kw):
        day = ExpressionAttributeValues[':d']
        return {'Items': [dict(v) for (d, _), v in sorted(self.items.items()) if d == day]}

    def update_item(self, Key, ExpressionAttributeValues=None, **kw):
        key = (Key['day'], Key['ip'])
        if kw.get('UpdateExpression') == 'REMOVE pending':
            if 'pending' not in self.items.get(key, {}):
                raise _conditional_failed()
            del self.items[key]['pending']
            return {}
        item = self.items.setdefault(key, dict(Key))
        if item.get('n', 0) > ExpressionAttributeValues[':cap']:
            raise _conditional_failed()
        item['n'] = item.get('n', 0) + 1
        return {'Attributes': {'n': item['n']}}


class FakeResource:
    def __init__(self):
        self.table = FakeTable()

    def Table(self, name):
        return self.table


@pytest.fixture
def va(monkeypatch):
    import visitor_alert
    import visitor_digest
    sent = []
    rdns = {}
    monkeypatch.setattr(visitor_alert, '_rdns', lambda ip: rdns.get(ip, ''))
    visitor_alert.rdns_names = rdns
    visitor_alert._OWNER_MARKED.clear()
    res = FakeResource()
    visitor_alert.sent = sent
    visitor_alert.res = res
    visitor_alert.DAILY_CAP = visitor_digest.DAILY_CAP
    return visitor_alert


def _event(path, ip='203.0.113.5', ua=BROWSER, ref='', auth=None):
    headers = {'User-Agent': ua, 'X-Forwarded-For': f'{ip}, 172.70.1.1',
               'CF-IPCountry': 'FR'}
    if ref:
        headers['Referer'] = ref
    if auth:
        headers['Authorization'] = auth
    return {'path': path, 'headers': headers, 'requestContext': {'stage': ''}}


def _record(va, path, status=200, **kw):
    va.check(_event(path, **kw), path,
             {'statusCode': status, 'headers': {'Content-Type': 'text/html; charset=utf-8'}},
             lambda: va.res)


HUMAN_VISIT = [(0, '/', 200, ''), (60, '/biog', 200, PAGE)]


class FakeLogs:
    """CloudWatch's filter_log_events, for records given as (seconds, path, status, ref)."""
    def __init__(self, base, by_ip=None):
        self.base, self.by_ip = base, by_ip or {}

    def filter_log_events(self, filterPattern, **kw):
        ip = filterPattern.split('$.ip = "')[1].split('"')[0]
        events = []
        for secs, path, status, ref in self.by_ip.get(ip, HUMAN_VISIT):
            rec = {'evt': 'access', 'ip': ip, 'path': path, 'status': status, 'ref': ref,
                   'ts': (self.base + timedelta(seconds=secs)).isoformat()}
            events.append({'message': json.dumps(rec)})
        return {'events': events}


def _digest(va, logs=None, later=timedelta(hours=2), owner='', private=None):
    """Run the digest as if `later` after now, sending into va.sent."""
    import visitor_digest
    visitor_digest.process(va.res.table, logs or FakeLogs(datetime.now(timezone.utc)),
                           datetime.now(timezone.utc) + later, owner_of=lambda ip: owner,
                           send=lambda t, d='': va.sent.append((t, d)),
                           private=lambda: private or visitor_digest.ALWAYS_PRIVATE)


def _hit(va, path, status=200, **kw):
    """A request, then the digest once its visit is over."""
    _record(va, path, status, **kw)
    _digest(va)


def test_favicon_from_a_browser_alerts_once_per_day(va):
    _hit(va, '/favicon.svg', ref=PAGE)
    _hit(va, '/favicon.png', ref=PAGE)
    _hit(va, '/astro', ref='https://www.petergrecian.co.uk/')
    assert len(va.sent) == 1
    title, detail = va.sent[0]
    assert 'FR (203.0.113.5)' in title          # client IP, not the XFF chain


def test_link_follow_alerts_but_landing_alone_does_not(va):
    _hit(va, '/')
    assert va.sent == []
    _hit(va, '/', ref='https://www.petergrecian.co.uk/')   # same page, a reload
    assert va.sent == []
    _hit(va, '/biog', ref='https://www.petergrecian.co.uk/')
    assert len(va.sent) == 1


@pytest.mark.parametrize('ua', ['calendaralarm-poller/1.0', 'curl/8.14.1',
                                'Mozilla/5.0 (compatible; Googlebot/2.1)',
                                'Mozilla/5.0 (compatible; CensysInspect/1.1)',
                                'Mozilla/5.0 (compatible; InternetMeasurement/1.0)', ''])
def test_tools_and_bots_never_alert(va, ua):
    _hit(va, '/favicon.ico', ua=ua, ref=PAGE)
    assert va.sent == []


def test_scanner_with_spoofed_referer_on_404_does_not_alert(va):
    _hit(va, '/wp-admin/', status=404, ref='https://www.petergrecian.co.uk/')
    assert va.sent == []


def test_googlebot_range_without_bot_token_is_excluded(va):
    _hit(va, '/favicon.ico', ip='66.249.64.106', ref=PAGE,
         ua='Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36')
    assert va.sent == []


def test_authenticated_ip_is_the_owner_for_the_day(va):
    _hit(va, '/my-contents', auth='Basic eDp5')
    _hit(va, '/favicon.png', ref=PAGE)
    assert va.sent == []


def test_failed_auth_does_not_make_an_owner(va):
    _hit(va, '/my-contents', status=401, auth='Basic eDp5')
    _hit(va, '/favicon.png', ref=PAGE)
    assert len(va.sent) == 1


def test_permanent_owner_row_suppresses(va):
    va.res.table.items[('owner', '203.0.113.5')] = {'day': 'owner', 'ip': '203.0.113.5'}
    _hit(va, '/favicon.png', ref=PAGE)
    assert va.sent == []


def test_daily_cap_then_one_capped_message_then_silence(va):
    for i in range(va.DAILY_CAP + 5):
        _hit(va, '/favicon.png', ip=f'198.51.100.{i}', ref=PAGE)
    assert len(va.sent) == va.DAILY_CAP + 1
    assert 'capped' in va.sent[-1][0]


def test_a_failure_never_raises(va):
    def broken():
        raise RuntimeError('dynamodb down')
    va.check(_event('/favicon.png'), '/favicon.png', {'statusCode': 200}, broken)


def test_manifest_fetch_with_page_referer_is_not_a_link_follow(va):
    va.check(_event('/ytpods/manifest.webmanifest', ref='https://www.petergrecian.co.uk/ytpods'),
             '/ytpods/manifest.webmanifest',
             {'statusCode': 200, 'headers': {'Content-Type': 'application/manifest+json'}},
             lambda: va.res)
    assert va.sent == []


# 2026-10-24: a census probe fetched only the favicon, with no Referer; a GCP
# VM fetched / and then the favicon with the favicon itself as Referer.
@pytest.mark.parametrize('ref', ['', 'https://petergrecian.co.uk/favicon.ico',
                                 'https://example.com/'])
def test_favicon_without_a_page_referer_does_not_alert(va, ref):
    _hit(va, '/favicon.ico', ref=ref)
    assert va.sent == []


def test_scanner_rdns_suppresses(va):
    va.rdns_names['203.0.113.5'] = 'sh-ams-nl-gd17-wk103d.internet-census.org'
    _hit(va, '/favicon.ico', ref=PAGE)
    assert va.sent == []
    _hit(va, '/favicon.ico', ip='198.51.100.1', ref=PAGE)   # cap slot not used up
    assert '1/10' in va.sent[0][1]


def test_nothing_is_sent_until_the_visit_is_over(va):
    _record(va, '/favicon.ico', ref=PAGE)
    assert va.sent == []
    base = datetime.now(timezone.utc)
    logs = FakeLogs(base)
    _digest(va, logs, later=timedelta(minutes=10))       # still within QUIET
    assert va.sent == []
    _digest(va, logs, later=timedelta(minutes=40))
    assert len(va.sent) == 1
    _digest(va, logs, later=timedelta(minutes=55))       # and only once
    assert len(va.sent) == 1


def test_a_visit_still_browsing_waits_then_reports_at_max_wait(va):
    _record(va, '/favicon.ico', ref=PAGE)
    base = datetime.now(timezone.utc)
    logs = FakeLogs(base, {'203.0.113.5': [(3 * 3600 - 60, '/', 200, ''),
                                           (3 * 3600, '/cv', 200, PAGE)]})
    _digest(va, logs, later=timedelta(hours=2))
    assert va.sent == []
    _digest(va, logs, later=timedelta(hours=3, minutes=1))
    assert len(va.sent) == 1


def test_alert_says_how_many_pages_which_how_long_and_from_where(va):
    _record(va, '/cv', ref=PAGE)
    base = datetime.now(timezone.utc)
    logs = FakeLogs(base, {'203.0.113.5': [
        (0, '/', 200, 'https://www.google.com/search?q=x'),
        (1, '/favicon.ico', 200, PAGE),
        (2, '/contents/app-icon-192.png', 200, PAGE),
        (60, '/cv', 200, PAGE),
        (120, '/cv', 200, PAGE),
        (180, '/astro', 200, 'https://www.petergrecian.co.uk/cv'),
        (181, '/missing', 404, PAGE)]})
    _digest(va, logs, owner='Example Telecom')
    title, detail = va.sent[0]
    assert title.startswith('Website visitor: 4 pages in 3 min, FR (203.0.113.5)')
    assert 'Pages: / > /cv > /astro\n' in detail       # no assets, repeats collapsed
    assert 'Arrived from: https://www.google.com/search?q=x' in detail
    assert 'Network: Example Telecom' in detail
    assert '7 requests, 1 failed' in detail


def _visit(va, ip, records, **kw):
    _record(va, '/favicon.ico', ip=ip, ref=PAGE, **kw)
    _digest(va, FakeLogs(datetime.now(timezone.utc), {ip: records}))


def test_the_palo_alto_scan_of_2026_10_31_is_held(va):
    _visit(va, '205.169.39.53', [
        (0, '/', 200, ''), (1, '/contents/manifest.webmanifest', 200, PAGE),
        (8, '/contents/app-icon-192.png', 200, PAGE), (8, '/favicon.ico', 200, PAGE)])
    assert va.sent == []
    row = va.res.table.items[next(k for k in va.res.table.items if k[1] == '205.169.39.53')]
    assert 'pending' not in row                 # decided once, not retried


def test_a_crawler_walking_the_links_is_held(va):
    _visit(va, '198.51.100.7', [(0, '/', 200, ''), (1, '/biog', 200, PAGE),
                                (2, '/t3', 200, PAGE), (3, '/astro', 200, PAGE)])
    assert va.sent == []


def test_reloading_one_page_slowly_is_held(va):
    _visit(va, '198.51.100.8', [(0, '/', 200, ''), (10, '/', 200, ''), (20, '/', 200, '')])
    assert va.sent == []


def test_a_cloud_address_is_held_however_slowly_it_reads(va):
    va.rdns_names['198.51.100.9'] = '9.100.51.198.bc.googleusercontent.com'
    _visit(va, '198.51.100.9', HUMAN_VISIT)
    assert va.sent == []


def test_held_visits_do_not_use_up_the_cap(va):
    _visit(va, '198.51.100.10', [(0, '/', 200, '')])
    _visit(va, '198.51.100.11', HUMAN_VISIT)
    assert '1/10' in va.sent[0][1]


def test_private_pages_do_not_make_a_visit_human(va):
    _visit(va, '198.51.100.12', [(0, '/ytpods', 200, ''), (60, '/ytpods/refresh', 200, PAGE),
                                 (120, '/groceries', 200, PAGE), (180, '/', 200, PAGE)])
    assert va.sent == []        # only one public page among them


def test_private_pages_are_left_out_of_the_alert(va):
    _visit(va, '198.51.100.13', [(0, '/', 200, ''), (30, '/ytpods', 200, PAGE),
                                 (60, '/biog', 200, PAGE)])
    title, detail = va.sent[0]
    assert title.startswith('Website visitor: 2 pages in 1 min')
    assert 'Pages: / > /biog\n' in detail


def test_contents_table_flags_are_private_and_prefixes_are_whole_segments(va):
    import visitor_digest

    class Contents:
        def scan(self):
            return {'Items': [{'path': 'pi-fleet', 'auth_required': True},
                              {'path': 'biog', 'auth_required': False}]}
    private = visitor_digest.private_paths(Contents())
    assert '/pi-fleet' in private and '/biog' not in private and '/ytpods' in private
    s = visitor_digest.summarise(
        [{'path': p, 'status': 200, 'ref': '', 'ts': '2026-10-31T11:00:00+00:00'}
         for p in ('/pi-fleet/x', '/pi-fleetish', '/contents', '/my-contents')], private)
    assert s['trail'] == ['/pi-fleetish', '/contents']


def test_unreadable_contents_table_falls_back(va):
    import visitor_digest

    class Broken:
        def scan(self):
            raise RuntimeError('denied')
    assert '/ytpods' in visitor_digest.private_paths(Broken())


def test_message_reads_plainly():
    import visitor_digest
    ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36')
    base = datetime(2026, 10, 31, 11, 3, 17, tzinfo=timezone.utc)
    s = visitor_digest.summarise([
        {'path': '/', 'status': 200, 'ref': '', 'ts': base.isoformat()},
        {'path': '/biog', 'status': 200, 'ref': PAGE,
         'ts': (base + timedelta(seconds=90)).isoformat()}])
    title, detail = visitor_digest.message(
        {'ip': '192.0.2.1', 'country': 'US', 'city': 'Dallas', 'region': 'Texas', 'ua': ua},
        s, 'Example Telecom', 1)
    assert title == 'Website visitor: 2 pages in 2 min, Dallas, Texas, US (192.0.2.1)'
    assert 'Pages: / > /biog\n' in detail
    assert 'Arrived from: no referrer' in detail
    assert 'Browser: Chrome 117 on Windows' in detail


def test_city_is_used_when_cloudflare_sends_it(va):
    event = _event('/favicon.ico', ref=PAGE)
    event['headers'].update({'CF-IPCity': 'Dallas', 'CF-Region': 'Texas', 'CF-IPCountry': 'US'})
    va.check(event, '/favicon.ico', {'statusCode': 200, 'headers': {}}, lambda: va.res)
    _digest(va)
    assert 'Dallas, Texas, US (203.0.113.5)' in va.sent[0][0]


def test_forged_ip_never_reaches_the_log_filter(va):
    _record(va, '/favicon.ico', ip='x") || ($.ip = "*', ref=PAGE)
    _digest(va)
    assert va.sent == []


def test_one_bad_row_does_not_stop_the_rest(va):
    _record(va, '/favicon.ico', ip='198.51.100.1', ref=PAGE)
    _record(va, '/favicon.ico', ip='198.51.100.2', ref=PAGE)

    class Flaky(FakeLogs):
        def filter_log_events(self, filterPattern, **kw):
            if '198.51.100.1' in filterPattern:
                raise RuntimeError('throttled')
            return super().filter_log_events(filterPattern, **kw)
    _digest(va, Flaky(datetime.now(timezone.utc)))
    assert len(va.sent) == 1 and '198.51.100.2' in va.sent[0][0]
    _digest(va)                                     # the failed one is retried
    assert len(va.sent) == 2
