import sys, os, json, re
sys.path.insert(0, "tests")
import golden_sweep as g
paths = sorted(json.load(open(g.GOLDEN_PATH)).keys())
with g._pinned_clock():
    mod = g._build_module()
    os.chdir(g.LAMBDA_DIR)
    out = sys.stdout
    for p in paths:
        sys.stdout = open(os.devnull, "w")
        try:
            r = mod.lambda_handler(g._event(p), g._context())
        except Exception as e:
            r = {"statusCode": "EXC "+type(e).__name__}
        sys.stdout = out
        b = r.get("body") or ""
        if r.get("statusCode") != 200 or "html" not in (r.get("headers") or {}).get("Content-Type",""):
            continue
        m = re.search(r'class="site-back".*?href="([^"]*)"[^>]*>&larr; ([^<]*)', b)
        if m: print(f"ADDED  {p:55} -> {m.group(1)} ({m.group(2)})")
        else:
            bm = re.search(r'<body\b[^>]*>', b, re.I)
            fl = re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>\s*([^<]{0,20})', b[bm.end():]) if bm else None
            print(f"NONE   {p:55} body={'y' if bm else 'n'} first={fl.groups() if fl else None}")
