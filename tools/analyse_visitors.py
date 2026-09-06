#!/usr/bin/env python3
"""Visitor statistics for www.petergrecian.co.uk from the cv-access-logs history.

The DynamoDB table `cv-access-logs` has one item per request since 2026-01-20
with path, IP, user-agent and referer — the only historical source that carries
the user-agent (CloudWatch only ever had path and IP, in separate records).

Reads the jsonl(.gz) dump of a table scan and writes CSVs plus a summary. The
classification is deliberately shape-based, not a classifier: bots ask for one
path and leave, ask for paths that do not exist, and never fetch the page's
assets; a browser loads an HTML page and then its CSS/favicon from the same IP
within seconds, and often follows a link to a second page.
"""

import argparse, csv, glob, gzip, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

SESSION_GAP = timedelta(minutes=30)

# Ours by construction: known, enumerable, and not visitors.
MACHINE_PATHS = ('/calendaralarm/api', '/pi-fleet/api', '/gardencam/timing',
                 '/gardencam/capture', '/event')
# Note "GoogleOther" and "Google-InspectionTool" carry NO "bot" token and wear a
# full Chrome UA — they are why the first pass counted 724 "humans" in a day.
MACHINE_UA = re.compile(
    r'bot|crawl|spider|slurp|curl|wget|python-requests|python-urllib|okhttp|'
    r'health-check|healthcheck|uptime|monitor|scanner|scrapy|libwww|java/|go-http|'
    r'headless|phantom|facebookexternalhit|preview|fetcher|semrush|ahrefs|mj12|'
    r'dataprovider|censys|masscan|zgrab|nmap|palo alto|expanse|internet-measurement|'
    r'googleother|google-inspectiontool|googleimageproxy|apis-google|adsbot|'
    r'yandex|baidu|duckduck|petalsearch|applebot|amazonbot|gptbot|claudebot|ccbot|'
    r'perplexity|bytespider|dotbot|seznam|sogou|exabot|ia_archiver|archive\.org|'
    r'node-fetch|axios|httpx|aiohttp|postman|restsharp|http-client|guzzle|'
    r'route53|feedfetcher|screaming frog|siteaudit|netcraft|paloalto',
    re.I)

# Crawler networks. A UA can lie; the address it comes from is harder to fake,
# and these are the operators that publish their ranges.
MACHINE_NETS = ('66.249.', '64.233.', '72.14.', '209.85.', '35.247.',   # Google
                '157.55.', '40.77.', '207.46.', '20.15.', '52.167.',    # Bing
                '5.255.', '37.9.', '95.108.', '87.250.',                # Yandex
                '17.241.', '17.58.',                                    # Apple
                '142.250.', '74.125.', '66.102.', '172.217.', '216.58.',  # Google proxies
                '15.177.')                                              # Route53

# Peter's own address. He is the site's most frequent visitor by a wide margin,
# which makes "a human arrived" useless as an alert unless he is excluded.
OWNER_IPS = ('81.96.235.31',)
BROWSER_UA = re.compile(r'Mozilla/5\.0.*(Chrome|Safari|Firefox|Edg|OPR)/', re.I)
ASSET = re.compile(r'/favicon|/tick\.png|\.css|\.js$|/thumbs/|/fullres|apple-touch|\.png$|\.svg$|\.ico$')

# Paths the site actually serves (from the route list in lambda/mywebsite.py).
# Anything else is enumeration — the shape that says "not a visitor".
REAL_PREFIXES = ('/', '/ai-config', '/astro', '/calendaralarm', '/contents', '/cv',
                 '/event', '/gardencam', '/gitinfo', '/glacier', '/gotg',
                 '/lambda-stats', '/manim', '/memspeed', '/pi-fleet', '/privacy',
                 '/rcr', '/site-test', '/skycam', '/springcam', '/srfcplus',
                 '/starcam', '/stereo', '/stereo-nav', '/t3', '/us-vs-the-machines')
REAL_FILES = ('/robots.txt', '/favicon.ico', '/favicon.png', '/favicon.svg',
              '/tick.png', '/apple-touch-icon.png', '/sitemap.xml')


def is_real(path):
    return (path in REAL_PREFIXES or path in REAL_FILES
            or any(path.startswith(p + '/') for p in REAL_PREFIXES if p != '/'))


def load(paths):
    for p in paths:
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def norm(rec):
    ts = rec.get('timestamp', '')
    try:
        dt = datetime.fromisoformat(ts[:26])
    except ValueError:
        return None
    path = (rec.get('path') or '').split('?')[0]
    ua = rec.get('user_agent') or ''
    # The logged 'ip' is the whole X-Forwarded-For chain: client first, then the
    # Cloudflare edge that relayed it. The edge address rotates per request, so
    # keeping the chain shatters one visitor into a visit per hop.
    ip = (rec.get('ip') or '').split(',')[0].strip()
    return {
        'dt': dt, 'date': dt.date().isoformat(), 'hour': dt.hour,
        'path': path, 'ip': ip, 'ua': ua,
        'ref': rec.get('referer') or '', 'host': rec.get('host') or '',
        'machine_path': any(path.startswith(m) for m in MACHINE_PATHS),
        'bot_ua': bool(MACHINE_UA.search(ua)) or ip.startswith(MACHINE_NETS),
        'browser_ua': (bool(BROWSER_UA.search(ua)) and not MACHINE_UA.search(ua)
                       and not ip.startswith(MACHINE_NETS)),
        'asset': bool(ASSET.search(path)),
        'real': is_real(path),
    }


def sessionise(rows):
    by_ip = defaultdict(list)
    for r in rows:
        if r['ip'] and not r['machine_path']:
            by_ip[r['ip']].append(r)
    visits = []
    for ip, rs in by_ip.items():
        rs.sort(key=lambda r: r['dt'])
        cur = [rs[0]]
        for prev, nxt in zip(rs, rs[1:]):
            if nxt['dt'] - prev['dt'] > SESSION_GAP:
                visits.append(cur); cur = [nxt]
            else:
                cur.append(nxt)
        visits.append(cur)

    out = []
    for rs in visits:
        pages = [r for r in rs if not r['asset']]
        assets = [r for r in rs if r['asset']]
        uas = Counter(r['ua'] for r in rs if r['ua'])
        ua = uas.most_common(1)[0][0] if uas else ''
        probes = [r for r in rs if not r['real']]
        v = {
            'ip': rs[0]['ip'], 'start': rs[0]['dt'].isoformat(timespec='seconds'),
            'end': rs[-1]['dt'].isoformat(timespec='seconds'),
            'seconds': int((rs[-1]['dt'] - rs[0]['dt']).total_seconds()),
            'requests': len(rs), 'pages': len(pages), 'assets': len(assets),
            'distinct_pages': len({r['path'] for r in pages}),
            'probes': len(probes),
            'browser_ua': any(r['browser_ua'] for r in rs),
            'bot_ua': any(r['bot_ua'] for r in rs),
            'ua': ua[:200], 'ref': next((r['ref'] for r in rs if r['ref']), '')[:200],
            'entry': pages[0]['path'] if pages else rs[0]['path'],
            'path_list': '|'.join(dict.fromkeys(r['path'] for r in rs))[:300],
        }
        # A human: a real browser that either fetched the page's assets or
        # followed a link to a second page — and was not enumerating.
        # A human: a real browser that asked for at least one actual page and
        # then either fetched that page's assets or followed a link to a second
        # one — and was not enumerating. A lone favicon fetch is not a visit.
        v['human'] = (v['browser_ua'] and not v['bot_ua'] and v['probes'] == 0
                      and v['pages'] > 0
                      and (v['assets'] > 0 or v['distinct_pages'] >= 2))
        v['owner'] = v['ip'] in OWNER_IPS
        out.append(v)
    return sorted(out, key=lambda v: v['start'])


def write_csv(path, rows, fields):
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
    print(f'wrote {path} ({len(rows)} rows)', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--out', default='/home/peter/mywebsite/analysis/access-history')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    files = [f for p in a.inputs for f in glob.glob(p)]
    rows = [r for r in (norm(x) for x in load(files)) if r]
    rows.sort(key=lambda r: r['dt'])
    print(f'{len(rows)} requests', file=sys.stderr)

    visits = sessionise(rows)
    humans = [v for v in visits if v['human']]
    strangers = [v for v in humans if not v['owner']]
    write_csv(os.path.join(a.out, 'visits.csv'), visits,
              ['ip', 'start', 'end', 'seconds', 'requests', 'pages', 'assets',
               'distinct_pages', 'probes', 'browser_ua', 'bot_ua', 'human',
               'owner', 'entry', 'ref', 'ua', 'path_list'])
    write_csv(os.path.join(a.out, 'stranger_visits.csv'), strangers,
              ['ip', 'start', 'end', 'seconds', 'requests', 'pages', 'assets',
               'distinct_pages', 'entry', 'ref', 'ua', 'path_list'])
    write_csv(os.path.join(a.out, 'human_visits.csv'), humans,
              ['ip', 'start', 'end', 'seconds', 'requests', 'pages', 'assets',
               'distinct_pages', 'entry', 'ref', 'ua', 'path_list'])

    daily = defaultdict(lambda: Counter())
    for r in rows:
        d = daily[r['date']]
        d['requests'] += 1
        d['machine'] += r['machine_path']
        d['bot_ua'] += r['bot_ua']
        d['probes'] += (not r['real'])
    for v in humans:
        daily[v['start'][:10]]['human_visits'] += 1
    write_csv(os.path.join(a.out, 'daily.csv'),
              [dict(date=d, **daily[d]) for d in sorted(daily)],
              ['date', 'requests', 'machine', 'bot_ua', 'probes', 'human_visits'])

    summary = {
        'requests': len(rows),
        'span': [rows[0]['dt'].isoformat(), rows[-1]['dt'].isoformat()],
        'days': len(daily),
        'machine_path_requests': sum(r['machine_path'] for r in rows),
        'bot_ua_requests': sum(r['bot_ua'] for r in rows),
        'probe_requests': sum(not r['real'] for r in rows),
        'distinct_ips': len({r['ip'] for r in rows if r['ip']}),
        'visits': len(visits),
        'human_visits': len(humans),
        'human_ips': len({v['ip'] for v in humans}),
        'human_visits_per_week': round(len(humans) / max(1, len(daily)) * 7, 1),
        'owner_visits': len(humans) - len(strangers),
        'stranger_visits': len(strangers),
        'stranger_ips': len({v['ip'] for v in strangers}),
        'stranger_visits_per_week': round(len(strangers) / max(1, len(daily)) * 7, 1),
        'top_stranger_entry': Counter(v['entry'] for v in strangers).most_common(15),
        'top_paths': Counter(r['path'] for r in rows).most_common(25),
        'top_human_entry': Counter(v['entry'] for v in humans).most_common(25),
        'top_human_ua': Counter(v['ua'][:90] for v in humans).most_common(15),
        'top_referers': Counter(v['ref'] for v in humans if v['ref']).most_common(15),
        'top_probe_paths': Counter(r['path'] for r in rows if not r['real']).most_common(25),
        'top_bot_ua': Counter(r['ua'][:90] for r in rows if r['bot_ua']).most_common(15),
    }
    with open(os.path.join(a.out, 'summary.json'), 'w') as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2)[:4000])


if __name__ == '__main__':
    main()
