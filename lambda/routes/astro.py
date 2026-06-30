"""Astro hub page — lists the project's astronomy cameras."""


CAMERAS = [
    {
        "path": "/astro/astrocam",
        "title": "Astro Camera",
        "desc": "Pi 4 + Camera Module v2 (IMX219). Nightly star-trail and pole-derotated stacks with hot/cold pixel masking.",
        "status": "live",
    },
    {
        "path": "/astro/eclipticam",
        "title": "Ecliptic Camera",
        "desc": "Two-camera Pi (OV5647 v1 + IMX708 Wide) — day and night astro along the ecliptic.",
        "status": "live",
    },
    {
        "path": "/starcam",
        "title": "Star Camera (historical)",
        "desc": "Zenith-pointing OV5647 — nightly stacks, plate-solved frames, derotation experiments.",
        "status": "live",
    },
]


def _card(cam):
    badge = "" if cam["status"] == "live" else '<span class="badge">coming soon</span>'
    return f'''<a class="cam-card" href="{cam["path"]}">
  <div class="cam-title">{cam["title"]}{badge}</div>
  <p class="cam-desc">{cam["desc"]}</p>
</a>
'''


def render_astro_hub(*, theme_css_js):
    cards = "".join(_card(c) for c in CAMERAS)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Astro</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 800px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1.5rem 0 0.3rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .cam-card {{ display: block; background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; text-decoration: none; color: inherit; }}
    .cam-card:hover {{ opacity: 0.85; }}
    .cam-title {{ font-size: 1.05rem; font-weight: 600; color: var(--accent); }}
    .cam-desc {{ font-size: 0.85rem; color: var(--text-secondary); margin: 0.4rem 0 0; line-height: 1.5; }}
    .badge {{ display: inline-block; margin-left: 0.5rem; padding: 0.1rem 0.5rem; font-size: 0.7rem; font-weight: 400; color: var(--text-secondary); background: var(--divider, #2C2C2E); border-radius: 6px; vertical-align: middle; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Astro</h1>
    <div class="subtitle">scientific astronomy cameras — measurements, not timelapses</div>
{cards}
    <div class="footer">
      <a href="/astro/storage">Storage status</a> &middot;
      <a href="/contents">Home</a>
    </div>
  </div>
</body>
</html>'''


def render_astro_stub(*, theme_css_js, title, image_url=None, caption=None):
    image_html = ""
    if image_url:
        cap = f'<div class="caption">{caption}</div>' if caption else ""
        image_html = f'<a href="{image_url}"><img class="sample" src="{image_url}" alt="{title} sample"></a>{cap}'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 900px; margin: 2rem auto; text-align: center; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    .tag {{ color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 1.5rem; }}
    .sample {{ width: 100%; height: auto; border-radius: 12px; background: #000; display: block; }}
    .caption {{ color: var(--text-secondary); font-size: 0.8rem; margin-top: 0.5rem; }}
    .nav {{ margin-top: 2rem; font-size: 0.85rem; }}
    .nav a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="tag">coming soon — sample frame</div>
    {image_html}
    <div class="nav"><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Live per-camera night pages (unify-cameras deliverables).
# Reads astro-berrylands-eu-west-1/<camera>/nights/<night>/ — summary.json
# (schema 2 from astro/present/summary.py), brightness.png, max.jpg,
# derot.jpg; eclipticam files carry a v1_/v3w_ stem.


def _stat(label, value):
    return (f'<div class="stat"><div class="stat-v">{value}</div>'
            f'<div class="stat-l">{label}</div></div>')


def _hhmm(iso):
    """HH:MM from an ISO timestamp string, or '?'."""
    try:
        return iso.split("T")[1][:5]
    except (AttributeError, IndexError):
        return "?"


def _section(sec):
    """One subcam section: hero image(s) + stats strip."""
    s = sec.get("summary") or {}
    urls = sec.get("urls") or {}
    label = sec.get("label")

    heading = f'<h2>{label}</h2>' if label else ""

    imgs = []
    # Each sweep gets its OWN poster (poster-<name>.jpg, the mid-frame of
    # that clip) so the preview is a frame from the video itself. Fall
    # back to the shared thumb.jpg, then max.jpg, for older nights that
    # predate per-video posters.
    shared_poster = urls.get("thumb.jpg") or urls.get("max.jpg", "")
    for key, poster_key, cap in (
        ("sweep-colour.mp4", "poster-colour.jpg",
         "colour sweep — 10 min stack sliding 1 min per frame, 60 fps; "
         "story of the night in 5 seconds"),
        ("sweep-mono.mp4", "poster-mono.jpg",
         "monochrome sweep — same window, greyscale (science view)"),
        ("sweep-diff.mp4", "poster-diff.jpg",
         "difference sweep — max(frame) − window mean; the sky floor, "
         "hot pixels, and cloud-glow cancel, leaving only trails and "
         "transients"),
        ("sweep-detrans.mp4", "poster-detrans.jpg",
         "detrans sweep — each 10 min window undistorted (k1,k2) and "
         "de-translated by the sky velocity, registering the 60 s "
         "streaks into one sharp high-SNR streak; stars stay tight as "
         "the night drifts past"),
        ("sweep-detrans-deep.mp4", "poster-detrans-deep.jpg",
         "detrans deep — registered frames averaged then background-"
         "subtracted (max SNR); pulls the faintest stars onto a clean "
         "dark sky, per 10 min window through the night"),
    ):
        url = urls.get(key)
        if url:
            poster = urls.get(poster_key) or shared_poster
            imgs.append(
                f'<video controls loop preload="metadata" playsinline '
                f'poster="{poster}"><source src="{url}" type="video/mp4">'
                f'Your browser cannot play this clip.</video>'
                f'<div class="caption">{cap}</div>')
    for key, cap in (("derot.jpg", "pole-derotated stack (darkest window)"),
                     ("max.jpg", "max stack — star trails"),
                     ("brightness.png", "per-frame brightness (log&#8322;)")):
        url = urls.get(key)
        if url:
            imgs.append(f'<a href="{url}"><img src="{url}" alt="{cap}"></a>'
                        f'<div class="caption">{cap}</div>')

    stats = []
    if s.get("n_frames") is not None:
        stacked = s.get("n_stacked")
        v = (f'{stacked} / {s["n_frames"]}' if stacked is not None
             else f'{s["n_frames"]}')
        stats.append(_stat("frames stacked / captured", v))
    derot = s.get("derot")
    if derot:
        w = derot.get("window_utc") or [None, None]
        stats.append(_stat("derot window (UTC)",
                           f'{_hhmm(w[0])}&ndash;{_hhmm(w[1])}'))
        p = derot.get("pole_xy") or [0, 0]
        stats.append(_stat("pole (px)", f'({p[0]:.0f}, {p[1]:.0f})'))
    badpix = s.get("badpix")
    if badpix:
        stats.append(_stat("bad pixels",
                           f'{badpix.get("bad_pct", 0):.3f}%'))
    stats_html = f'<div class="stats">{"".join(stats)}</div>' if stats else ""

    return f'{heading}{stats_html}{"".join(imgs)}'


def render_astro_camera_calendar(*, theme_css_js, title, camera,
                                 nights_with_meta,
                                 combined_brightness_url=None,
                                 moon_net_url=None):
    """Calendar of nights for a camera, newest first.

    nights_with_meta: list of {"night": "YYYY-MM-DD", "thumb_url": ...|None,
                               "summary": dict|None}
    combined_brightness_url: presigned URL of the multi-night overlay
        plot (or None — section is hidden if absent).
    moon_net_url: presigned URL of the accumulated moon-net image
        (or None — section is hidden if absent).
    Each card links to /astro/<camera>/night/<night>.
    Mirrors /starcam's per-night index in spirit but smaller scope.
    """
    combined_html = ""
    if combined_brightness_url:
        combined_html = (
            f'<a href="{combined_brightness_url}">'
            f'<img class="combined" src="{combined_brightness_url}" '
            f'alt="per-night brightness curves overlaid"></a>'
            f'<div class="caption">per-night brightness curves '
            f'(log&#8322; stops above pedestal vs BST clock)</div>')

    moon_net_html = ""
    if moon_net_url:
        moon_net_html = (
            f'<a href="{moon_net_url}">'
            f'<img class="moon-net" src="{moon_net_url}" '
            f'alt="accumulated moon tracks across the fixed field"></a>'
            f'<div class="caption">moon net &mdash; each clear night the '
            f'moon traces a different known-position track across the fixed '
            f'sensor; the threads accumulate into a self-scanning '
            f'astrometric net</div>')

    if not nights_with_meta:
        cards_html = '<p class="empty">No nights published yet.</p>'
    else:
        cards = []
        for n in nights_with_meta:
            night = n["night"]
            thumb = n.get("thumb_url") or ""
            s = n.get("summary") or {}
            n_stacked = s.get("n_stacked")
            n_frames = s.get("n_frames")
            stats = (f'{n_stacked} of {n_frames} frames stacked'
                     if n_stacked is not None and n_frames is not None
                     else "")
            poster = (f'<img src="{thumb}" alt="{night}" loading="lazy">'
                      if thumb else
                      '<div class="no-thumb">no preview</div>')
            verdict = (s.get("verdict") or "").lower()
            verdict_badge = ""
            if verdict in ("clear", "cloudy", "no-data"):
                verdict_badge = (
                    f'<span class="verdict verdict-{verdict}">{verdict}</span>')
            cards.append(
                f'<a class="night-card" href="/astro/{camera}/night/{night}">'
                f'<div class="night-thumb">{poster}</div>'
                f'<div class="night-meta"><div class="night-date">{night}'
                f'{verdict_badge}</div>'
                f'<div class="night-stats">{stats}</div></div></a>')
        cards_html = f'<div class="night-grid">{"".join(cards)}</div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .night-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }}
    .night-card {{ display: block; background: var(--card-bg); border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; }}
    .night-card:hover {{ opacity: 0.85; }}
    .night-thumb {{ aspect-ratio: 2304 / 1064; background: #000; overflow: hidden; }}
    .night-thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .no-thumb {{ color: var(--text-secondary); font-size: 0.85rem; padding: 2rem; text-align: center; }}
    .night-meta {{ padding: 0.6rem 0.8rem; }}
    .night-date {{ font-weight: 600; }}
    .night-stats {{ color: var(--text-secondary); font-size: 0.8rem; margin-top: 0.15rem; }}
    .verdict {{ display: inline-block; margin-left: 0.5rem; padding: 0.05rem 0.4rem; font-size: 0.7rem; font-weight: 500; border-radius: 6px; vertical-align: middle; text-transform: lowercase; }}
    .verdict-clear {{ background: #1f3a1f; color: #6fcf6a; }}
    .verdict-cloudy {{ background: #3a2f1f; color: #d6a04a; }}
    .verdict-no-data {{ background: var(--divider, #2C2C2E); color: var(--text-secondary); }}
    .combined {{ width: 100%; height: auto; border-radius: 12px; background: #fff; display: block; margin-bottom: 0.3rem; }}
    .moon-net {{ width: 100%; height: auto; border-radius: 12px; background: #000; display: block; margin-bottom: 0.3rem; }}
    .caption {{ color: var(--text-secondary); font-size: 0.8rem; margin: 0 0 1.5rem; text-align: center; }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="subtitle">night-by-night colour sweeps and stacks</div>
    {combined_html}
    {moon_net_html}
    {cards_html}
    <div class="footer"><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def _gib(n):
    """Human GiB/TiB from an int byte count."""
    n = int(n or 0)
    if n >= 1 << 40:
        return f"{n / (1 << 40):.1f} TB"
    if n >= 1 << 30:
        return f"{n / (1 << 30):.0f} GB"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.0f} MB"
    return f"{n} B"


def render_astro_storage(*, theme_css_js, capacity, inventory, month=None):
    """Storage status page: capacity bars + data inventory + archive tier.

    capacity:  [{host, fs, size_gb, used_gb, avail_gb, pct, updated_at}]
    inventory: [{night, loc, camera, host, path, storage_class, online,
                 bytes:{...}, verdict?, updated_at?, ...}]
    Both come straight from DynamoDB (numbers are Decimal — coerce to int).

    month: 'YYYY-MM' to show only that month's calendar/detail, or None for
    the latest month. Capacity/tiers/keepers are global on every page.
    """
    import datetime as _dt

    def _i(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    # --- Capacity bars, on a common ABSOLUTE scale --------------------------
    # Each disk's bar width is its total size against a shared full-scale axis
    # (default 1 TB = full width), so disks are visually comparable and you can
    # see at a glance what will fit where. The filled portion is used space;
    # the empty remainder of the bar is free space on that disk.
    cap = sorted(capacity, key=lambda c: _i(c.get("size_gb")), reverse=True)
    # Full-scale axis: at least 1 TB, or the biggest disk if larger.
    scale_gb = max([1024] + [_i(c.get("size_gb")) for c in cap])
    cap_rows = []
    for c in cap:
        size = _i(c.get("size_gb"))
        used = _i(c.get("used_gb"))
        avail = _i(c.get("avail_gb"))
        pct = _i(c.get("pct"))
        colour = ("var(--error, #FF3B30)" if pct >= 90 else
                  "var(--warning, #FF9500)" if pct >= 75 else
                  "var(--accent, #007AFF)")
        track_pct = 100.0 * size / scale_gb          # disk size vs axis
        used_pct = (100.0 * used / size) if size else 0  # used within the disk
        cap_rows.append(
            f'<div class="cap">'
            f'<div class="cap-head"><span class="cap-host">{c.get("host","?")}'
            f' <span class="cap-fs">{c.get("fs","")}</span></span>'
            f'<span class="cap-num">{used} used &middot; '
            f'<b>{avail} GB free</b> &middot; {size} GB &middot; {pct}%</span></div>'
            f'<div class="axis"><div class="bar" style="width:{track_pct:.1f}%">'
            f'<div class="bar-fill" style="width:{used_pct:.1f}%;'
            f'background:{colour}"></div></div></div></div>')
    axis_tb = scale_gb / 1024
    cap_html = (
        f'<div class="axis-label">scale: full width = {axis_tb:.0f} TB</div>'
        + ("".join(cap_rows) or '<p class="empty">No capacity data.</p>'))

    # --- Inventory grouped by night, newest first -----------------------
    SC_LABEL = {"local": "local", "usb-stick": "USB stick",
                "deep-archive": "Deep Archive"}
    by_night = {}
    for it in inventory:
        by_night.setdefault(it.get("night", "?"), []).append(it)

    # month paging: calendar + detail show one month; default to the latest.
    months = sorted({n[:7] for n in by_night if len(n) >= 7}, reverse=True)
    cur_month = month if month in months else (months[0] if months else None)
    month_nights = sorted((n for n in by_night
                           if cur_month and n.startswith(cur_month)),
                          reverse=True)

    # archive-tier tallies
    n_local = sum(1 for it in inventory if it.get("storage_class") == "local")
    n_stick = sum(1 for it in inventory if it.get("storage_class") == "usb-stick")
    n_cold = sum(1 for it in inventory if it.get("storage_class") == "deep-archive")
    nights_set = set(by_night)
    cold_nights = {it["night"] for it in inventory
                   if it.get("storage_class") == "deep-archive"}
    at_risk = sorted(
        n for n in nights_set
        if n not in cold_nights and any(
            it.get("storage_class") == "local" for it in by_night[n]))

    inv_rows = []
    for night in month_nights:
        locs = by_night[night]
        cells = []
        # drift flag: >1 local copy whose sizes differ
        local_sizes = [sum(_i(v) for v in (it.get("bytes") or {}).values())
                       for it in locs if it.get("storage_class") == "local"]
        drift = len(local_sizes) > 1 and len(set(local_sizes)) > 1
        has_cold = any(it.get("storage_class") == "deep-archive" for it in locs)
        for it in sorted(locs, key=lambda x: x.get("storage_class", "")):
            sc = it.get("storage_class", "local")
            total = sum(_i(v) for v in (it.get("bytes") or {}).values())
            cells.append(
                f'<div class="loc loc-{sc}">'
                f'<span class="loc-where">{it.get("host","?")}'
                f'<span class="loc-path">{it.get("path","")}</span></span>'
                f'<span class="loc-tags"><span class="sc sc-{sc}">'
                f'{SC_LABEL.get(sc, sc)}</span> {_gib(total)}</span></div>')
        flags = ""
        if drift:
            flags += '<span class="flag flag-drift">size drift</span>'
        if not has_cold and any(it.get("storage_class") == "local" for it in locs):
            flags += '<span class="flag flag-risk">no cold copy</span>'
        cam = locs[0].get("camera", "?")
        inv_rows.append(
            f'<div class="night-row"><div class="night-hd">'
            f'<span class="nr-night">{night}</span>'
            f'<span class="nr-cam">{cam}</span>{flags}</div>'
            f'{"".join(cells)}</div>')
    inv_html = "".join(inv_rows) or '<p class="empty">No inventory.</p>'

    # --- Keeper computation: clearest CLEAR night per ISO week --------------
    # Retention policy (project-deep-archive-backlog): the clearest clear
    # night of each ISO week is a "keeper" (kept raw + → Glacier); the rest
    # are "squashable". verdict comes from inventory rows when present; weeks
    # with no clear night get no keeper. Falls back to biggest night/week
    # when verdict is absent (until the reporter records it).
    def _night_verdict(locs):
        for it in locs:
            v = (it.get("verdict") or "").lower()
            if v:
                return v
        return ""

    def _night_bytes(locs):
        return max((sum(_i(v) for v in (it.get("bytes") or {}).values())
                    for it in locs), default=0)

    week_nights = {}  # isoweek -> [(night, bytes, verdict)]
    for night, locs in by_night.items():
        try:
            wk = _dt.date.fromisoformat(night).isocalendar()[:2]  # (year, week)
        except ValueError:
            continue
        week_nights.setdefault(wk, []).append(
            (night, _night_bytes(locs), _night_verdict(locs)))

    keepers = set()
    have_verdict = any(v for nights in week_nights.values()
                       for _, _, v in nights)
    for wk, nights in week_nights.items():
        clear = [n for n in nights if n[2] == "clear"]
        pool = clear if clear else (nights if not have_verdict else [])
        if pool:
            keepers.add(max(pool, key=lambda n: n[1])[0])  # biggest in pool

    # --- Calendar table: night -> where stored + shrunk + keeper -----------
    # "Shrunk" = squashed format present (raw_sum8 / binned_sum2 bytes), per
    # COLD_STORAGE.md — the ~0.17x reduced per-frame products that replace raw.
    SHRUNK_KEYS = ("raw_sum8", "binned_sum2")
    def _yes(b):
        return '<span class="yes">✓</span>' if b else '<span class="no">·</span>'

    cal_rows = []
    for night in month_nights:
        locs = by_night[night]
        cam = locs[0].get("camera", "?")
        on_local = any(it.get("storage_class") == "local" for it in locs)
        on_stick = any(it.get("storage_class") == "usb-stick" for it in locs)
        on_cold = any(it.get("storage_class") == "deep-archive" for it in locs)
        hosts = sorted({it.get("host", "?") for it in locs
                        if it.get("storage_class") == "local"})
        shrunk = any(k in (it.get("bytes") or {})
                     for it in locs for k in SHRUNK_KEYS)
        biggest = _night_bytes(locs)
        keep = night in keepers
        keep_cell = ('<span class="keep">★ keeper</span>' if keep
                     else '<span class="squash">squashable</span>')
        cal_rows.append(
            f'<tr><td class="c-night">{night}</td>'
            f'<td class="c-cam">{cam}</td>'
            f'<td>{", ".join(hosts) if hosts else "&mdash;"}</td>'
            f'<td class="c-ctr">{_yes(on_local)}</td>'
            f'<td class="c-ctr">{_yes(on_stick)}</td>'
            f'<td class="c-ctr">{_yes(on_cold)}</td>'
            f'<td class="c-ctr">{_yes(shrunk)}</td>'
            f'<td class="c-keep">{keep_cell}</td>'
            f'<td class="c-sz">{_gib(biggest)}</td></tr>')
    cal_html = (
        '<table class="cal"><thead><tr>'
        '<th>night</th><th>cam</th><th>local host(s)</th>'
        '<th>local</th><th>USB</th><th>cold</th><th>shrunk</th>'
        '<th>retention</th><th>size</th>'
        '</tr></thead><tbody>' + ("".join(cal_rows) or
        '<tr><td colspan="9" class="empty">No inventory this month.</td></tr>')
        + '</tbody></table>')

    # month nav
    month_links = []
    for mo in months:
        cls = ' class="cur"' if mo == cur_month else ""
        month_links.append(f'<a{cls} href="/astro/storage/{mo}">{mo}</a>')
    month_nav = (f'<div class="months">{"".join(month_links)}</div>'
                 if month_links else "")

    # last-updated: newest updated_at across inventory + capacity
    ts = [_i(it.get("updated_at")) for it in inventory] + \
         [_i(c.get("updated_at")) for c in capacity]
    ts = [t for t in ts if t > 0]
    if ts:
        updated_str = _dt.datetime.fromtimestamp(
            max(ts), _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    else:
        updated_str = "unknown"

    risk_html = ""
    if at_risk:
        risk_html = (
            f'<div class="risk-note">⚠ {len(at_risk)} night(s) are '
            f'<b>local-only with no Deep Archive copy</b> — do not free local '
            f'storage for these until archived: {", ".join(at_risk)}</div>')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Astro — Storage</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    h2 {{ font-size: 1.05rem; margin: 1.75rem 0 0.6rem; color: var(--text-secondary); }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .cap {{ margin-bottom: 0.8rem; }}
    .cap-head {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 0.85rem; margin-bottom: 0.25rem; }}
    .cap-host {{ font-weight: 600; }}
    .cap-fs {{ color: var(--text-secondary); font-weight: 400; font-size: 0.75rem; }}
    .cap-num {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .axis-label {{ color: var(--text-secondary); font-size: 0.72rem; margin-bottom: 0.4rem; }}
    .axis {{ width: 100%; height: 14px; }}
    .bar {{ height: 14px; background: var(--divider, #2C2C2E); border-radius: 4px; overflow: hidden; min-width: 2px; }}
    .bar-fill {{ height: 100%; border-radius: 4px 0 0 4px; }}
    .tiers {{ display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; margin: 0.5rem 0 0.5rem; }}
    .tier {{ background: var(--card-bg); border-radius: 12px; padding: 0.5rem 0.9rem; text-align: center; min-width: 90px; }}
    .tier-v {{ font-size: 1.1rem; font-weight: 600; }}
    .tier-l {{ font-size: 0.7rem; color: var(--text-secondary); }}
    .risk-note {{ background: #3a1f1f; color: #ff9a90; border-radius: 12px; padding: 0.7rem 0.9rem; font-size: 0.82rem; margin: 0.75rem 0; }}
    .night-row {{ background: var(--card-bg); border-radius: 12px; padding: 0.6rem 0.8rem; margin-bottom: 0.5rem; }}
    .night-hd {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem; }}
    .nr-night {{ font-weight: 600; }}
    .nr-cam {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .loc {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 0.8rem; padding: 0.15rem 0; border-top: 1px solid var(--divider, #2C2C2E); }}
    .loc-where {{ color: var(--text); }}
    .loc-path {{ color: var(--text-secondary); font-size: 0.72rem; margin-left: 0.4rem; word-break: break-all; }}
    .loc-tags {{ color: var(--text-secondary); white-space: nowrap; }}
    .sc {{ display: inline-block; padding: 0.05rem 0.4rem; font-size: 0.68rem; border-radius: 6px; margin-right: 0.3rem; }}
    .sc-local {{ background: #1f3a1f; color: #6fcf6a; }}
    .sc-usb-stick {{ background: #2f2f3a; color: #9a9aff; }}
    .sc-deep-archive {{ background: #1f2f3a; color: #6ab0ff; }}
    .flag {{ display: inline-block; padding: 0.05rem 0.4rem; font-size: 0.68rem; border-radius: 6px; }}
    .flag-drift {{ background: #3a2f1f; color: #d6a04a; }}
    .flag-risk {{ background: #3a1f1f; color: #ff9a90; }}
    .cal {{ width: 100%; border-collapse: collapse; font-size: 0.7rem; }}
    .cal th {{ text-align: left; color: var(--text-secondary); font-weight: 500; font-size: 0.64rem; padding: 0.25rem 0.4rem; border-bottom: 1px solid var(--divider, #2C2C2E); }}
    .cal td {{ padding: 0.25rem 0.4rem; border-bottom: 1px solid var(--divider, #2C2C2E); }}
    .c-night {{ font-weight: 600; white-space: nowrap; }}
    .c-cam {{ color: var(--text-secondary); }}
    .c-ctr {{ text-align: center; }}
    .c-keep {{ white-space: nowrap; }}
    .c-sz {{ text-align: right; color: var(--text-secondary); white-space: nowrap; }}
    .keep {{ color: #f0c040; font-weight: 600; }}
    .squash {{ color: var(--text-secondary); }}
    .months {{ text-align: center; margin-bottom: 0.6rem; }}
    .months a {{ display: inline-block; margin: 0.1rem 0.25rem; padding: 0.15rem 0.5rem; font-size: 0.75rem; color: var(--accent); background: var(--card-bg); border-radius: 8px; text-decoration: none; }}
    .months a.cur {{ color: var(--text); background: var(--divider, #2C2C2E); }}
    .updated {{ text-align: center; color: var(--text-secondary); font-size: 0.72rem; margin-bottom: 1rem; }}
    .yes {{ color: #6fcf6a; font-weight: 600; }}
    .no {{ color: var(--text-secondary); }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Storage</h1>
    <div class="subtitle">where the astro data lives — capacity, location, and archive tier</div>
    <div class="updated">last updated {updated_str}</div>

    <h2>Capacity</h2>
    {cap_html}

    <h2>Archive tier</h2>
    <div class="tiers">
      <div class="tier"><div class="tier-v">{n_local}</div><div class="tier-l">local copies</div></div>
      <div class="tier"><div class="tier-v">{n_stick}</div><div class="tier-l">USB stick</div></div>
      <div class="tier"><div class="tier-v">{n_cold}</div><div class="tier-l">Deep Archive</div></div>
    </div>
    {risk_html}

    <h2>Calendar — {cur_month or "—"}</h2>
    {month_nav}
    {cal_html}

    <h2>Inventory detail — {cur_month or "—"}</h2>
    {inv_html}

    <div class="footer"><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def render_astro_player(*, camera, night, sources):
    """Advanced multi-source player for one night's astro outputs.

    sources: list of presigned URLs (deliverables + experiments). The
    first source loads on open; ↑/↓ or 1-9 cycle. Labels in the
    source picker are derived from the URL filename by the underlying
    player (e.g. 'sweep-colour.mp4', 'mci-colour-60.mp4').

    Delegates to render_skycam_player from routes.gardencam — same
    code, same affordances (scrub, frame-step, clip in/out, speed,
    loop, share-URL, fullscreen, PIP, AirPlay, Cast). Per the
    astro-website-player project memory we reuse skycam patterns
    rather than build parallel ones.
    """
    from .gardencam import render_skycam_player
    return render_skycam_player(key=None, srcs=sources)


def render_astro_camera_page(*, theme_css_js, title, camera, night,
                             sections, nights, is_dashboard):
    """Camera dashboard / per-night page.

    sections: [{label|None, summary|None, urls: {basename: presigned}}]
    nights:   ['YYYY-MM-DD', ...] newest first (for the nav strip)
    """
    nav_links = []
    for n in nights[:14]:
        cls = ' class="cur"' if n == night else ""
        nav_links.append(f'<a{cls} href="/astro/{camera}/night/{n}">{n}</a>')
    nights_nav = (f'<div class="nights">{"".join(nav_links)}</div>'
                  if nav_links else "")
    subtitle = ("latest night" if is_dashboard else "night") + f" &middot; {night}"
    player_link = (
        f'<div class="player-link">'
        f'<a href="/astro/{camera}/night/{night}/player">'
        f'⚙ advanced player &mdash; frame-step, clip, compare</a>'
        f'</div>')

    body = "".join(_section(sec) for sec in sections) or \
        '<p class="empty">No published data for this night.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — {night}</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    h2 {{ font-size: 1.05rem; margin: 1.5rem 0 0.5rem; color: var(--text-secondary); }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem; }}
    .nights {{ text-align: center; margin-bottom: 1.25rem; }}
    .nights a {{ display: inline-block; margin: 0.15rem 0.3rem; padding: 0.2rem 0.55rem; font-size: 0.8rem; color: var(--accent); background: var(--card-bg); border-radius: 8px; text-decoration: none; }}
    .nights a.cur {{ color: var(--text); background: var(--divider, #2C2C2E); }}
    .player-link {{ text-align: center; margin: 0.5rem 0 1.25rem; }}
    .player-link a {{ display: inline-block; padding: 0.4rem 0.9rem; color: var(--accent); background: var(--card-bg); border-radius: 8px; text-decoration: none; font-size: 0.85rem; }}
    .player-link a:hover {{ opacity: 0.85; }}
    img, video {{ width: 100%; height: auto; border-radius: 12px; background: #000; display: block; }}
    .caption {{ color: var(--text-secondary); font-size: 0.8rem; margin: 0.4rem 0 1.25rem; text-align: center; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-bottom: 1rem; }}
    .stat {{ background: var(--card-bg); border-radius: 12px; padding: 0.5rem 0.9rem; text-align: center; }}
    .stat-v {{ font-size: 1rem; font-weight: 600; }}
    .stat-l {{ font-size: 0.7rem; color: var(--text-secondary); }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
    {nights_nav}
    {player_link}
    {body}
    <div class="footer"><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''
