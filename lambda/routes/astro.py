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
    .cam-card {{ display: block; background: var(--card-bg); padding: 1rem; margin-bottom: 0.75rem; text-decoration: none; color: inherit; }}
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
    .sample {{ width: 100%; height: auto; background: #000; display: block; }}
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
                                 moon_net_url=None,
                                 sun_net_url=None):
    """Calendar of nights for a camera, newest first.

    nights_with_meta: list of {"night": "YYYY-MM-DD", "thumb_url": ...|None,
                               "summary": dict|None}
    combined_brightness_url: presigned URL of the multi-night overlay
        plot (or None — section is hidden if absent).
    moon_net_url: presigned URL of the accumulated moon-net image
        (or None — section is hidden if absent).
    sun_net_url: presigned URL of the accumulated sun-net image
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

    sun_net_html = ""
    if sun_net_url:
        sun_net_html = (
            f'<a href="{sun_net_url}">'
            f'<img class="sun-net" src="{sun_net_url}" '
            f'alt="accumulated sun tracks across the fixed field"></a>'
            f'<div class="caption">sun net &mdash; daytime solar tracks '
            f'(ND-filtered) across the same fixed sensor; a wide-baseline '
            f'companion to the moon net for pinning pointing &amp; '
            f'distortion</div>')

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
    .night-card {{ display: block; background: var(--card-bg); overflow: hidden; text-decoration: none; color: inherit; }}
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
    .combined {{ width: 100%; height: auto; background: #fff; display: block; margin-bottom: 0.3rem; }}
    .moon-net, .sun-net {{ width: 100%; height: auto; background: #000; display: block; margin-bottom: 0.3rem; }}
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
    {sun_net_html}
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


def render_astro_storage(*, theme_css_js, capacity, inventory, month=None,
                         show_all=False):
    """Storage status page: capacity bars + data inventory + archive tier.

    capacity:  [{host, fs, size_gb, used_gb, avail_gb, pct, updated_at}]
    inventory: [{night, loc, camera, host, path, storage_class, online,
                 bytes:{...}, verdict?, updated_at?, ...}]
    Both come straight from DynamoDB (numbers are Decimal — coerce to int).

    month: 'YYYY-MM' to show only that month's calendar/detail, or None for
    the latest month. Capacity/tiers/keepers are global on every page.
    """
    import datetime as _dt
    import re as _re

    def _i(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    # Not shown here (the reporter stopped emitting these 2026-07-05, but
    # rows linger until each host has pruned): skycam (not astro data),
    # day-mode frames and the date-level deliverables (derived/disposable
    # — they stay on disk but are storage-page noise, peter 2026-07-05).
    inventory = [it for it in inventory
                 if it.get("camera") != "skycam"
                 and it.get("layout") != "mode:day"
                 and not str(it.get("camera", "")).endswith("-deliverables")]

    # Camera abbreviations are hardware-versioned (peter 2026-07-29): the grid
    # is denser and the version is meaningful (av3s + eos coming). Anything not
    # mapped falls through to its raw name so nothing silently disappears.
    CAM_ABBR = {
        "starcam": "sv1",          # star camera v1
        "astrocam": "av2",         # astro camera v2 (av3s soon)
        "eclipticam-v3w": "ev3w",  # the main eclipticam
        "eclipticam-v1": "ev1",    # rare
        # future, mapped ahead of first data so they render tidily on arrival:
        "astrocam-v3s": "av3s",
        "eos": "eos", "canon": "eos", "canon-eos": "eos",
    }

    def _cam_abbr(cam):
        c = str(cam or "?")
        if c in CAM_ABBR:
            return CAM_ABBR[c]
        # sweep/derived variants: eclipticam-v3w_sweep-colour -> ev3w-swcolour
        if "_sweep" in c:
            base = c.split("_sweep")[0]
            tail = c.split("_sweep", 1)[1].lstrip("-") or "sweep"
            return f'{CAM_ABBR.get(base, base)}-sw{tail[:4]}'
        return c

    # Sweeps/derivatives are hidden by default ("clean" grid = real captures);
    # ?all=1 reveals them. They live on the per-camera pages regardless.
    if not show_all:
        inventory = [it for it in inventory
                     if "_sweep" not in str(it.get("camera", ""))]

    def _tilde(p):
        """Display-only: /home/<user>/... -> ~/..."""
        return _re.sub(r"^/home/[^/]+/", "~/", str(p or ""))

    # Data-format legend for the starcam CSV/cold rows, whose `bytes` map
    # carries per-product keys instead of a scanner `fmt`. Dims/cadence are
    # starcam's (OV5647, raw ~3 s cadence measured from frame timestamps;
    # sum8 = 8 summed raws, sum2 = 2 summed 2x2-binned — see COLD_STORAGE.md).
    PRODUCT_DESC = {
        "raw_bayer": "raw mosaic 2592×1944 fits.fz ≈3 s",
        "binned": "bin2 1296×972 fits.fz ≈3 s",
        "raw_sum8": "sum8 mosaic 2592×1944 ≈24 s",
        "binned_sum2": "sum2 bin2 1296×972 ≈6 s",
    }

    def _res_label(rc):
        # 'full implied' for raw at native res; rows written by reporters
        # older than 2026-07-05 still carry the long label.
        return {"full mosaic": "mosaic"}.get(str(rc), str(rc))

    def _fmt_desc(it):
        """Human format line for one location row: the scanner's `fmt`
        (file type, dims, resolution class, frame count, cadence) when
        present, else the per-product breakdown from the bytes keys."""
        f = it.get("fmt") or {}
        if f:
            parts = [str(f.get("ext", "")).lstrip(".")]
            dims = f.get("dims") or []
            if len(dims) == 2:
                parts.append(f"{_i(dims[0])}×{_i(dims[1])}")
            if f.get("res_class"):
                parts.append(_res_label(f["res_class"]))
            if f.get("n_frames"):
                parts.append(f"{_i(f['n_frames'])} frames")
            if f.get("cadence_s"):
                parts.append(f"≈{_i(f['cadence_s'])} s/frame")
            return " · ".join(p for p in parts if p)
        b = it.get("bytes") or {}
        return " + ".join(PRODUCT_DESC[k] for k in PRODUCT_DESC if _i(b.get(k)))

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
        removable = ' <span class="removable">⏏ removable</span>' \
            if c.get("removable") else ""
        cap_rows.append(
            f'<div class="cap">'
            f'<div class="cap-head"><span class="cap-host">{c.get("host","?")}'
            f' <span class="cap-fs">{c.get("fs","")}</span>{removable}</span>'
            f'<span class="cap-num">{used} used &middot; '
            f'<b>{avail} GB free</b> &middot; {size} GB &middot; {pct}%</span></div>'
            f'<div class="axis"><div class="bar" style="width:{track_pct:.1f}%">'
            f'<div class="bar-fill" style="width:{used_pct:.1f}%;'
            f'background:{colour}"></div></div></div></div>')
    axis_tb = scale_gb / 1024
    cap_html = (
        f'<div class="axis-label">scale: full width = {axis_tb:.0f} TB</div>'
        + ("".join(cap_rows) or '<p class="empty">No capacity data.</p>'))

    # --- Inventory grouped by (night, camera), newest first -----------------
    # Grouping by night alone lumped DIFFERENT cameras' rows together: the
    # size-drift flag then compared astrocam's night against eclipticam's
    # and fired on every multi-camera night. Copies only means anything
    # within one camera's data.
    SC_LABEL = {"local": "local", "usb-stick": "USB stick",
                "deep-archive": "Deep Archive"}

    def _kind(it):
        # day vs night capture of the same date are DIFFERENT data, not
        # copies of each other (eclipticam records mode in the layout).
        return "day" if it.get("layout") == "mode:day" else "night"

    by_nc = {}
    for it in inventory:
        by_nc.setdefault(
            (it.get("night", "?"), it.get("camera", "?"), _kind(it)),
            []).append(it)

    # month paging: calendar + detail show one month; default to the latest.
    months = sorted({k[0][:7] for k in by_nc if len(k[0]) >= 7}, reverse=True)
    cur_month = month if month in months else (months[0] if months else None)
    # newest night first, cameras alphabetical within a night, day before night
    month_groups = sorted(
        sorted(k for k in by_nc if cur_month and k[0].startswith(cur_month)),
        key=lambda k: k[0], reverse=True)

    def _cam_label(cam, kind):
        a = _cam_abbr(cam)
        return f"{a}·day" if kind == "day" else a

    # archive-tier tallies
    n_local = sum(1 for it in inventory if it.get("storage_class") == "local")
    n_stick = sum(1 for it in inventory if it.get("storage_class") == "usb-stick")
    n_cold = sum(1 for it in inventory if it.get("storage_class") == "deep-archive")

    def _night_bytes(locs):
        return max((sum(_i(v) for v in (it.get("bytes") or {}).values())
                    for it in locs), default=0)

    # --- Filesystem matrix: rows = night×camera, columns = filesystems ------
    # The page's job (peter 2026-07-29): answer "which filesystem is this
    # night on?" at a glance. Each column is one filesystem, abbreviated;
    # a row ticks the columns where that (night,camera) actually lives.
    # Columns are matched in order — first match wins — so every location
    # maps to exactly one column. `col` values are short abbreviations;
    # hover (title) gives the full host:path and storage class.
    #
    # To add a filesystem: append a (col, label, host, path_prefix, sc) row.
    # host/path_prefix/sc of None = wildcard. `title` is the tooltip.
    # Display order (peter 2026-07-29): live capture hosts first (mup, ecl),
    # then the consolidated store bs, then the rest. Matching is by
    # host+prefix+sc (disjoint), so column ORDER here is display-only and does
    # not affect which column a row lands in.
    FS_COLUMNS = [
        # col     full label                     host          path prefix              sc
        ("bs",   "muppet /mnt/bigstore",        "muppet",     "/mnt/bigstore",         "local"),
        ("mup",  "muppet ~ (home)",             "muppet",     "/home",                 "local"),
        ("ecl",  "eclipticam /mnt/ssd",         "eclipticam", None,                    "local"),
        ("bd",   "muppet /mnt/bigdisk",         "muppet",     "/mnt/bigdisk",          "local"),
        ("bd2",  "muppet /mnt/bigdisk2",        "muppet",     "/mnt/bigdisk2",         "local"),
        ("pd",   "muppet /mnt/photodisk",       "muppet",     "/mnt/photodisk",        "local"),
        ("pup",  "puppy ~ (home)",              "puppy",      None,                    "local"),
        ("ab",   "muppet ASTROBACKUP (USB)",    "muppet",     None,                    "usb-stick"),
        ("s3",   "AWS S3 Deep Archive",         "aws",        None,                    "deep-archive"),
    ]

    def _fs_col(it):
        """Which matrix column an inventory row belongs to (first match)."""
        host = it.get("host", "")
        path = str(it.get("path", ""))
        sc = it.get("storage_class", "local")
        for col, _label, chost, cprefix, csc in FS_COLUMNS:
            if chost is not None and host != chost:
                continue
            if csc is not None and sc != csc:
                continue
            if cprefix is not None and not path.startswith(cprefix):
                continue
            return col
        return None  # unmatched — surfaces as an "other" tick

    # Show ALL defined location columns, always (peter 2026-07-29: "we need
    # more columns for the locations"). With abbreviations the full set fits,
    # and an always-present column makes a MISSING copy visible — the point of
    # the grid. Unused-this-month columns get a dim header.
    used_cols = set()
    for night, cam, kind in month_groups:
        for it in by_nc[(night, cam, kind)]:
            c = _fs_col(it)
            if c:
                used_cols.add(c)
    col_order = [c for (c, *_r) in FS_COLUMNS]   # every column, in defined order
    col_meta = {c: (label, sc) for (c, label, _h, _p, sc) in FS_COLUMNS}

    # how many rows (cameras) each day has, so the day cell can rowspan them.
    from collections import Counter as _Counter
    day_rowcount = _Counter(k[0] for k in month_groups)
    day_seen = set()   # nights whose day cell has already been emitted

    mx_rows = []
    for night, cam, kind in month_groups:
        locs = by_nc[(night, cam, kind)]
        # map column -> bytes on that fs (for the cell tooltip)
        col_bytes = {}
        for it in locs:
            c = _fs_col(it)
            if not c:
                continue
            col_bytes.setdefault(c, 0)
            col_bytes[c] += sum(_i(v) for v in (it.get("bytes") or {}).values())
        n_copies = len(col_bytes)  # how many distinct filesystems hold it
        cells = []
        for ci, c in enumerate(col_order):
            zb = "mx-za" if ci % 2 == 0 else "mx-zb"  # vertical zebra per column
            if c in col_bytes:
                sc = col_meta[c][1]
                cells.append(
                    f'<td class="mx-hit mx-{sc} {zb}" '
                    f'title="{col_meta[c][0]} — {_gib(col_bytes[c])}">✓</td>')
            else:
                cells.append(f'<td class="mx-miss {zb}">·</td>')
        # one-copy nights are the fragile ones — flag the row
        lonely = ' mx-lonely' if n_copies <= 1 else ''
        biggest = _night_bytes(locs)
        # night column: just the day-of-month — the month is fixed by the
        # selector/radio above, so 'YYYY-MM-' is redundant. Full date on hover.
        # The day cell rowspans across all that day's camera rows (emit once).
        day = night[8:10] if len(night) >= 10 else night
        if night in day_seen:
            day_cell = ""
        else:
            day_seen.add(night)
            span = day_rowcount[night]
            rs = f' rowspan="{span}"' if span > 1 else ""
            day_cell = f'<td class="mx-night"{rs} title="{night}">{day}</td>'
        mx_rows.append(
            f'<tr class="mx-row{lonely}">'
            + day_cell
            + f'<td class="mx-cam">{_cam_label(cam, kind)}</td>'
            f'<td class="mx-n">{n_copies}</td>'
            + "".join(cells)
            + f'<td class="mx-sz">{_gib(biggest)}</td></tr>')

    head_cols = "".join(
        f'<th class="mx-col {"mx-za" if ci % 2 == 0 else "mx-zb"}'
        f'{"" if c in used_cols else " mx-col-empty"}" '
        f'title="{col_meta[c][0]}">{c}</th>'
        for ci, c in enumerate(col_order))
    legend = " &middot; ".join(f"<b>{c}</b> {col_meta[c][0]}" for c in col_order)

    # --- Per-camera format footnotes ---------------------------------------
    # Format is a property of the CAMERA, not each night, so it lives here as
    # a footnote (peter 2026-07-29: "v3w is 5 GB mosaic 60s exposures") rather
    # than repeating down every row. For each camera shown this month, derive
    # a one-line spec (resolution class · dims · exposure/cadence) plus a
    # typical night size (median of that camera's night totals).
    import statistics as _stats
    cam_specs = {}   # display-cam -> (spec_line, typical_bytes)
    for (night, cam, kind), locs in by_nc.items():
        dcam = _cam_label(cam, kind)
        # gather a representative fmt + this night's total bytes
        fmt = next((it.get("fmt") for it in locs if it.get("fmt")), None) or {}
        nb = _night_bytes(locs)
        spec = cam_specs.get(dcam, {"fmt": {}, "sizes": []})
        if fmt and not spec["fmt"]:
            spec["fmt"] = fmt
        if nb:
            spec["sizes"].append(nb)
        cam_specs[dcam] = spec

    cams_this_month = []
    for night, cam, kind in month_groups:
        dcam = _cam_label(cam, kind)
        if dcam not in cams_this_month:
            cams_this_month.append(dcam)

    def _cam_spec_line(dcam):
        spec = cam_specs.get(dcam) or {}
        f = spec.get("fmt") or {}
        parts = []
        if f.get("res_class"):
            parts.append(_res_label(f["res_class"]))
        dims = f.get("dims") or []
        if len(dims) == 2:
            parts.append(f"{_i(dims[0])}×{_i(dims[1])}")
        if _i(f.get("cadence_s")):
            parts.append(f"{_i(f['cadence_s'])} s exposures")
        if f.get("ext"):
            parts.append(str(f["ext"]).lstrip("."))
        sizes = spec.get("sizes") or []
        typ = _gib(int(_stats.median(sizes))) if sizes else ""
        spec_txt = " · ".join(parts) if parts else "—"
        return f"{spec_txt}{(' · ~' + typ + '/night') if typ else ''}"

    cam_notes = "".join(
        f'<div class="cam-note"><b>{dcam}</b> — {_cam_spec_line(dcam)}</div>'
        for dcam in cams_this_month)
    cam_notes_html = (f'<div class="cam-notes">{cam_notes}</div>'
                      if cam_notes else "")
    # clean/all toggle for sweep derivatives
    _mo_path = f"/{cur_month}" if cur_month else ""
    toggle = (f'<a href="/astro/storage{_mo_path}">clean ✓</a> · '
              f'<a href="/astro/storage{_mo_path}?all=1">+ derivatives</a>'
              if not show_all else
              f'<a href="/astro/storage{_mo_path}">clean</a> · '
              f'<a href="/astro/storage{_mo_path}?all=1">+ derivatives ✓</a>')
    cal_html = (
        '<table class="mx"><thead><tr>'
        '<th title="day of month">d</th><th>cam</th>'
        '<th class="mx-col" title="number of filesystems holding this night">#</th>'
        + head_cols +
        '<th class="mx-col">size</th>'
        '</tr></thead><tbody>' + ("".join(mx_rows) or
        f'<tr><td colspan="{len(col_order)+4}" class="empty">'
        'No inventory this month.</td></tr>')
        + '</tbody></table>'
        f'<div class="axis-label"><span class="mx-toggle">{toggle}</span><br>'
        f'{legend}<br>'
        'd = day of month · # = filesystems holding this night '
        '(dim column = none this month) · orange row = only ONE copy.</div>')

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
    .removable {{ font-size: 0.65rem; color: var(--accent); background: var(--card-bg); border-radius: 6px; padding: 0.05rem 0.35rem; }}
    .cap-num {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .axis-label {{ color: var(--text-secondary); font-size: 0.72rem; margin-bottom: 0.4rem; }}
    .axis {{ width: 100%; height: 14px; }}
    .bar {{ height: 14px; background: var(--divider, #2C2C2E); border-radius: 4px; overflow: hidden; min-width: 2px; }}
    .bar-fill {{ height: 100%; border-radius: 4px 0 0 4px; }}
    .tiers {{ display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; margin: 0.5rem 0 0.5rem; }}
    .tier {{ background: var(--card-bg); border-radius: 12px; padding: 0.5rem 0.9rem; text-align: center; min-width: 90px; }}
    .tier-v {{ font-size: 1.1rem; font-weight: 600; }}
    .tier-l {{ font-size: 0.7rem; color: var(--text-secondary); }}
    .night-row {{ background: var(--card-bg); border-radius: 12px; padding: 0.6rem 0.8rem; margin-bottom: 0.5rem; }}
    .night-hd {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem; }}
    .nr-night {{ font-weight: 600; }}
    .nr-cam {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .loc {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 0.8rem; padding: 0.15rem 0; border-top: 1px solid var(--divider, #2C2C2E); }}
    .loc-where {{ color: var(--text); }}
    .loc-path {{ color: var(--text-secondary); font-size: 0.72rem; margin-left: 0.4rem; word-break: break-all; }}
    .loc-tags {{ color: var(--text-secondary); white-space: nowrap; }}
    .loc-fmt {{ color: var(--text-secondary); font-size: 0.7rem; padding: 0.05rem 0 0.2rem; }}
    .sc {{ display: inline-block; padding: 0.05rem 0.4rem; font-size: 0.68rem; border-radius: 6px; margin-right: 0.3rem; }}
    .sc-local {{ background: #1f3a1f; color: #6fcf6a; }}
    .sc-usb-stick {{ background: #2f2f3a; color: #9a9aff; }}
    .sc-deep-archive {{ background: #1f2f3a; color: #6ab0ff; }}
    .flag {{ display: inline-block; padding: 0.05rem 0.4rem; font-size: 0.68rem; border-radius: 6px; }}
    .flag-drift {{ background: #3a2f1f; color: #d6a04a; }}
    /* filesystem matrix */
    .mx {{ width: 100%; border-collapse: collapse; font-size: 0.72rem; }}
    .mx th {{ color: var(--text-secondary); font-weight: 500; font-size: 0.66rem; padding: 0.2rem 0.3rem; border-bottom: 1px solid var(--divider, #2C2C2E); }}
    .mx th:nth-child(1), .mx th:nth-child(2) {{ text-align: left; }}
    .mx-col {{ text-align: center; }}
    .mx-col-empty {{ opacity: 0.35; }}
    /* vertical zebra: alternate columns tinted so the grid reads column-wise.
       fallback for older browsers, then currentColor mix (theme-aware). */
    .mx-za {{ background: transparent; }}
    .mx-zb {{ background: rgba(128,128,128,0.14); }}
    .mx-zb {{ background: color-mix(in srgb, currentColor 10%, transparent); }}
    .mx-toggle a {{ color: var(--accent); text-decoration: none; margin-right: 0.4rem; }}
    .mx td {{ padding: 0.2rem 0.3rem; border-bottom: 1px solid var(--divider, #2C2C2E); }}
    .mx-night {{ font-weight: 600; white-space: nowrap; vertical-align: middle; text-align: center; border-right: 1px solid var(--divider, #2C2C2E); }}
    .mx-cam {{ color: var(--text-secondary); white-space: nowrap; }}
    .mx-hit {{ text-align: center; font-weight: 600; }}
    .mx-local {{ color: #6fcf6a; }}
    .mx-usb-stick {{ color: #9a9aff; }}
    .mx-deep-archive {{ color: #6ab0ff; }}
    .mx-miss {{ text-align: center; color: var(--divider, #3a3a3c); }}
    .mx-n {{ text-align: center; color: var(--text-secondary); }}
    .mx-sz {{ text-align: right; color: var(--text-secondary); white-space: nowrap; }}
    .mx-lonely {{ background: rgba(255,149,0,0.12); }}
    .mx-lonely .mx-n {{ color: var(--warning, #FF9500); font-weight: 600; }}
    /* per-camera format footnotes */
    .cam-notes {{ margin-top: 0.6rem; }}
    .cam-note {{ font-size: 0.72rem; color: var(--text-secondary); padding: 0.1rem 0; }}
    .cam-note b {{ color: var(--text); }}
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

    <h2>Where each night lives — {cur_month or "—"}</h2>
    {month_nav}
    {cal_html}
    {cam_notes_html}

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
    img, video {{ width: 100%; height: auto; background: #000; display: block; }}
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
