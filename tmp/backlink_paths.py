import sys, os, re
sys.path.insert(0, "tests")
import golden_sweep as g
paths = sys.argv[1:]
with g._pinned_clock():
    mod = g._build_module(); os.chdir(g.LAMBDA_DIR); out = sys.stdout
    for p in paths:
        sys.stdout = open(os.devnull, "w")
        try: r = mod.lambda_handler(g._event(p), g._context())
        except Exception as e: r = {"statusCode": "EXC "+repr(e)[:80]}
        sys.stdout = out
        b = r.get("body") or ""
        m = re.search(r'class="site-back".*?href="([^"]*)"[^>]*>&larr; ([^<]*)', b)
        print(r.get("statusCode"), p, "->", m.groups() if m else None)
