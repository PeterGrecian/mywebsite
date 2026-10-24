"""visitor_alert: the signal, the owner rule, dedupe and the daily cap.

A fake table stands in for DynamoDB, implementing just the conditional put
and conditional increment the module relies on; _send is captured, so no
test can post a real alert.
"""
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

    def update_item(self, Key, ExpressionAttributeValues, **kw):
        key = (Key['day'], Key['ip'])
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
    sent = []
    monkeypatch.setattr(visitor_alert, '_send', lambda t, d: sent.append((t, d)))
    rdns = {}
    monkeypatch.setattr(visitor_alert, '_rdns', lambda ip: rdns.get(ip, ''))
    visitor_alert.rdns_names = rdns
    visitor_alert._OWNER_MARKED.clear()
    res = FakeResource()
    visitor_alert.sent = sent
    visitor_alert.res = res
    return visitor_alert


def _event(path, ip='203.0.113.5', ua=BROWSER, ref='', auth=None):
    headers = {'User-Agent': ua, 'X-Forwarded-For': f'{ip}, 172.70.1.1',
               'CF-IPCountry': 'FR'}
    if ref:
        headers['Referer'] = ref
    if auth:
        headers['Authorization'] = auth
    return {'path': path, 'headers': headers, 'requestContext': {'stage': ''}}


def _hit(va, path, status=200, **kw):
    va.check(_event(path, **kw), path,
             {'statusCode': status, 'headers': {'Content-Type': 'text/html; charset=utf-8'}},
             lambda: va.res)


def test_favicon_from_a_browser_alerts_once_per_day(va):
    _hit(va, '/favicon.svg', ref=PAGE)
    _hit(va, '/favicon.png', ref=PAGE)
    _hit(va, '/astro', ref='https://www.petergrecian.co.uk/')
    assert len(va.sent) == 1
    title, detail = va.sent[0]
    assert '/favicon.svg' in title and '(FR)' in title
    assert 'ip 203.0.113.5 ' in detail          # client IP, not the XFF chain


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
    assert '1/' in va.sent[0][1]


def test_cloud_rdns_is_labelled_not_suppressed(va):
    va.rdns_names['203.0.113.5'] = '140.87.122.34.bc.googleusercontent.com'
    _hit(va, '/favicon.ico', ref=PAGE)
    assert '(140.87.122.34.bc.googleusercontent.com, GCP)' in va.sent[0][1]


def test_no_rdns_is_said(va):
    _hit(va, '/favicon.ico', ref=PAGE)
    assert '(no rDNS)' in va.sent[0][1]
