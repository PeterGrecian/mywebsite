"""Crawl the site from /contents; report pages lacking a top-of-page backlink."""
import re, sys, urllib.request
from html.parser import HTMLParser
BASE = "https://www.petergrecian.co.uk"
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.links=[]; s.inbody=False; s.cur=None; s.text=""
    def handle_starttag(s, t, a):
        if t=="body": s.inbody=True
        if t=="a" and s.inbody: s.cur=dict(a).get("href","")
        s.text_pos = None
    def handle_data(s, d):
        if s.cur is not None: s.links.append((s.cur, d.strip()))
        s.cur = None if s.cur is not None and d.strip() else s.cur
    def handle_endtag(s, t):
        if t=="a": s.cur=None
def shape(p):
    p = re.sub(r"\d{4}-\d{2}(-\d{2})?", "D", p)
    p = re.sub(r"/[0-9a-f]{6,}|/\d+", "/N", p)
    return p
seen, shapes, q = set(), {}, ["/contents", "/astro"]
while q:
    path = q.pop(0)
    if path in seen: continue
    seen.add(path)
    s = shape(path)
    if s in shapes: continue
    try:
        r = urllib.request.urlopen(urllib.request.Request(BASE+path, headers={"User-Agent":"Mozilla/5.0 backlink-audit"}), timeout=20)
        if "html" not in r.headers.get("content-type",""): continue
        html = r.read().decode("utf8","replace")
    except Exception as e:
        shapes[s] = (path, f"ERR {e}"); continue
    p = P(); p.feed(html)
    first = [l for l in p.links if l[0] and not l[0].startswith("#")][:4]
    back = any(("←" in t or "←" in t) for _, t in p.links[:3])
    shapes[s] = (path, "ok " if back else "MISSING", first[:2])
    for h, _ in p.links:
        h = h.split("?")[0].split("#")[0]
        if h.startswith(BASE): h = h[len(BASE):]
        if h.startswith("/") and not h.startswith("//") and not re.search(r"\.(png|jpg|mp4|json|svg|ico|webm|gif)$", h):
            q.append(h)
for s,(v) in sorted(shapes.items()):
    print(v[1] if len(v)>1 else "", v[0], v[2] if len(v)>2 else "")
