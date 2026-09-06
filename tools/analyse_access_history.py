#!/usr/bin/env python3
"""Rebuild visitor statistics from the exported /aws/lambda/mywebsite history.

The pre-2026-09-06 handler logged free text, one fact per record: the path in
one line, the client IP in another, the duration in Lambda's own REPORT line.
They join only on RequestId, which is what this script does — it turns the
export back into one row per request, then answers the visitor questions.

Usage:
    analyse_access_history.py <dir-of-exported-.gz> [--out analysis/access-history]

The export is produced by `aws logs create-export-task` against the log group;
after 2026-09-06 the handler emits one JSON line per request and none of this
parsing is needed for new data.
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

START_RE = re.compile(r'START RequestId: ([0-9a-f-]{36})')
PATH_RE = re.compile(r'path = (.*?), stage = ')
XFF_RE = re.compile(r'X-Forwarded-For = (.*)')
REPORT_RE = re.compile(r'REPORT RequestId: ([0-9a-f-]{36})\s+Duration: ([\d.]+) ms')
REF_RE = re.compile(r'referer = (.*)')
# Exported lines are "<iso8601> <message>"; the message may itself be multi-line.
TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s(.*)$', re.S)

# Traffic that is ours by construction — known, enumerable, not a visitor.
KNOWN_MACHINE_PATHS = (
    '/calendaralarm/api/rules',   # the pip poller, once a minute
    '/pi-fleet/api',              # the fleet reporting in
    '/gardencam/timing',          # the page's own beacon
)
# Assets a browser fetches for itself. A client that asks for one of these has
# rendered a page; a scanner enumerating paths never does.
ASSET_HINTS = ('/favicon', '/tick.png', '.css', '.js', '/thumbs/', '/fullres', 'apple-touch')

SESSION_GAP = timedelta(minutes=30)


def parse_export(root):
    """Yield one dict per request, joining the free-text records on RequestId."""
    files = []
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            if n.endswith('.gz'):
                files.append(os.path.join(dirpath, n))
    print(f'{len(files)} exported files', file=sys.stderr)

    reqs = {}
    for i, f in enumerate(files):
        if i % 200 == 0:
            print(f'  {i}/{len(files)} files, {len(reqs)} requests', file=sys.stderr)
        with gzip.open(f, 'rt', errors='replace') as fh:
            current = None
            for line in fh:
                m = TS_RE.match(line)
                if m:
                    ts, msg = m.group(1), m.group(2)
                else:
                    ts, msg = None, line
                sm = START_RE.search(msg)
                if sm:
                    current = sm.group(1)
                    reqs.setdefault(current, {'req': current, 'ts': ts})
                    continue
                rm = REPORT_RE.search(msg)
                if rm:
                    r = reqs.setdefault(rm.group(1), {'req': rm.group(1), 'ts': ts})
                    r['ms'] = float(rm.group(2))
                    current = None
                    continue
                if current is None:
                    continue
                r = reqs[current]
                pm = PATH_RE.search(msg)
                if pm:
                    r['path'] = pm.group(1)
                    if ts and not r.get('ts'):
                        r['ts'] = ts
                    continue
                xm = XFF_RE.search(msg)
                if xm:
                    # client first, Cloudflare's own address second
                    r['ip'] = xm.group(1).split(',')[0].strip()
                    continue
                fm = REF_RE.search(msg)
                if fm:
                    r['ref'] = fm.group(1).strip()
    return [r for r in reqs.values() if r.get('ts')]


def classify(rows):
    for r in rows:
        p = r.get('path') or ''
        r['machine'] = any(p.startswith(k) for k in KNOWN_MACHINE_PATHS)
        r['asset'] = any(h in p for h in ASSET_HINTS)
    return rows


def sessionise(rows):
    """Group a visitor's requests into visits: same IP, gaps under 30 minutes."""
    by_ip = defaultdict(list)
    for r in rows:
        if r.get('ip') and not r['machine']:
            by_ip[r['ip']].append(r)
    visits = []
    for ip, rs in by_ip.items():
        rs.sort(key=lambda r: r['dt'])
        cur = [rs[0]]
        for prev, nxt in zip(rs, rs[1:]):
            if nxt['dt'] - prev['dt'] > SESSION_GAP:
                visits.append((ip, cur))
                cur = [nxt]
            else:
                cur.append(nxt)
        visits.append((ip, cur))

    out = []
    for ip, rs in visits:
        paths = [r.get('path') or '' for r in rs]
        pages = [p for p in paths if not any(h in p for h in ASSET_HINTS)]
        assets = [p for p in paths if any(h in p for h in ASSET_HINTS)]
        out.append({
            'ip': ip,
            'start': rs[0]['dt'],
            'end': rs[-1]['dt'],
            'requests': len(rs),
            'pages': len(pages),
            'assets': len(assets),
            'distinct_pages': len(set(pages)),
            'first_path': paths[0],
            'paths': '|'.join(dict.fromkeys(paths))[:400],
            # A browser fetches the page's assets; a scanner asks once and leaves.
            'human': bool(assets) or len(set(pages)) >= 2,
        })
    return sorted(out, key=lambda v: v['start'])


def write_csv(path, rows, fields):
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'wrote {path} ({len(rows)} rows)', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('export_dir')
    ap.add_argument('--out', default='analysis/access-history')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows = parse_export(a.export_dir)
    for r in rows:
        r['dt'] = datetime.strptime(r['ts'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        r['date'] = r['dt'].date().isoformat()
    rows.sort(key=lambda r: r['dt'])
    classify(rows)

    write_csv(os.path.join(a.out, 'requests.csv'), rows,
              ['ts', 'date', 'req', 'path', 'ip', 'ms', 'ref', 'machine', 'asset'])

    visits = sessionise(rows)
    for v in visits:
        v['start'] = v['start'].isoformat()
        v['end'] = v['end'].isoformat()
    write_csv(os.path.join(a.out, 'visits.csv'), visits,
              ['ip', 'start', 'end', 'requests', 'pages', 'assets',
               'distinct_pages', 'human', 'first_path', 'paths'])

    daily = Counter(r['date'] for r in rows)
    daily_machine = Counter(r['date'] for r in rows if r['machine'])
    daily_human = Counter(v['start'][:10] for v in visits if v['human'])
    days = sorted(daily)
    write_csv(os.path.join(a.out, 'daily.csv'),
              [{'date': d, 'requests': daily[d], 'machine': daily_machine[d],
                'human_visits': daily_human.get(d, 0)} for d in days],
              ['date', 'requests', 'machine', 'human_visits'])

    summary = {
        'requests': len(rows),
        'first': rows[0]['ts'], 'last': rows[-1]['ts'],
        'days': len(days),
        'machine_requests': sum(1 for r in rows if r['machine']),
        'distinct_ips': len({r.get('ip') for r in rows if r.get('ip')}),
        'visits': len(visits),
        'human_visits': sum(1 for v in visits if v['human']),
        'human_ips': len({v['ip'] for v in visits if v['human']}),
        'top_paths': Counter((r.get('path') or '') for r in rows).most_common(30),
        'top_human_paths': Counter(
            v['first_path'] for v in visits if v['human']).most_common(30),
    }
    with open(os.path.join(a.out, 'summary.json'), 'w') as fh:
        json.dump(summary, fh, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith('top')}, indent=2))


if __name__ == '__main__':
    main()
