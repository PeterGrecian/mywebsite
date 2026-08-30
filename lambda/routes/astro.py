"""Astro hub page — lists the project's astronomy cameras."""


# Ordered as the hub renders them: the cameras still taking data, then the
# cross-camera collections, then the retired ones under their own heading.
# Transients sits between the live cameras and the historical ones because it
# is fed by the live cameras and is the page's most-visited destination after
# them (Peter, 2026-08-28).
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
]


# Non-camera destinations under /astro — collections that cut ACROSS the
# cameras rather than belonging to one of them.
COLLECTIONS = [
    {
        "path": "/astro/photos",
        "title": "Photo Showcase",
        "desc": "Curated astrophotography captures — deep sky, Milky Way, star trails, polar derotations, and meteor fireballs with full equipment & exposure recipes.",
        "status": "live",
    },
    {
        "path": "/astro/transients",
        "title": "Transients",
        "desc": "Curated one-off captures — meteors and fireballs, lightning, aircraft, satellites, odd frames caught mid-inspection, and daylight test shots.",
        "status": "live",
    },
]


# Retired instruments. Their pages stay up — the data is still there and still
# linked from the nights — but they are no longer taking frames.
HISTORICAL = [
    {
        "path": "/astro/canon",
        "title": "EOS Camera",
        "desc": "Canon EOS 2000D DSLR — 30 s ISO-1600 fixed-focus subs, fixed mount. Nightly short-trail star-field stacks with hot/cold pixel masking.",
        "status": "live",
    },
    {
        "path": "/starcam",
        "title": "Star Camera",
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
    collections = "".join(_card(c) for c in COLLECTIONS)
    historical = ('<h2 class="section">Historical</h2>'
                  + "".join(_card(c) for c in HISTORICAL))
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
    .section {{ font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-secondary); margin: 1.6rem 0 0.6rem; }}
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
{collections}
{historical}
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
        # Serve the -web variant: 1280-wide, denoised, +faststart, ~5MB vs
        # 130-180MB full-res. This is what publish-night-cam builds them FOR
        # ("the website serves sweep-<name>-web.mp4; the full-res mp4 stays as
        # the high-quality/download copy") — the site had never used them, so
        # visitors pulled the full-res file, whose moov atom is at the END,
        # meaning playback could not start until the whole clip downloaded.
        # Fall back to full-res for older nights that predate the web encode.
        web_key = key.replace(".mp4", "-web.mp4")
        web_url = urls.get(web_key)
        url = web_url or urls.get(key)
        if url:
            poster = urls.get(poster_key) or shared_poster
            full = urls.get(key)
            # Offer the full-res as a download only when we're actually
            # playing the smaller web encode.
            dl = (f' &middot; <a class="dl" href="{full}">full-res</a>'
                  if web_url and full else "")
            imgs.append(
                f'<video controls loop preload="metadata" playsinline '
                f'poster="{poster}"><source src="{url}" type="video/mp4">'
                f'Your browser cannot play this clip.</video>'
                f'<div class="caption">{cap}{dl}</div>')
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
    anchor = s.get("anchor") or {}
    stops = anchor.get("stops") if isinstance(anchor, dict) else None
    if stops is None:
        stops = s.get("stops")
    if stops is not None:
        stats.append(_stat("brightness index", f'{stops:.2f} stops' if isinstance(stops, (int, float)) else f'{stops} stops'))
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


def _short_date(d):
    """'17 Aug' — %-d is glibc-only, so build the day number by hand."""
    return f'{d.day} {d.strftime("%b")}'


def astro_calendar_window(nights, *, week=None, month=None, show_all=False):
    """Pick which nights the calendar shows, plus its week/month nav lists.

    The calendar used to render every published night at once, which meant a
    presigned thumbnail per night and a page that got slower every night.
    It now shows one window at a time — the last 7 days by default — and
    links to the rest.

    nights: all published nights as 'YYYY-MM-DD' (any order).
    week:   'YYYY-MM-DD' start of a 7-day block (from the nav links).
    month:  'YYYY-MM'.
    show_all: render the full history (the /all escape hatch).

    Returns (selected, label, weeks, months):
      selected: nights to render, newest first
      label:    human description of the current window
      weeks:    [{'start', 'label', 'count', 'current'}] 7-day blocks
                anchored on the newest night, newest first
      months:   [{'key', 'label', 'count', 'current'}] months with nights
    """
    import datetime as _dt

    def _d(s):
        return _dt.date.fromisoformat(s)

    nights = sorted({n for n in nights if n}, reverse=True)
    if not nights:
        return [], '', [], []

    newest, oldest = _d(nights[0]), _d(nights[-1])

    # Weeks tile backwards from the newest night, so the default window is
    # always week block 0 and the blocks line up with the links.
    weeks = []
    for k in range((newest - oldest).days // 7 + 1):
        end = newest - _dt.timedelta(days=7 * k)
        start = end - _dt.timedelta(days=6)
        weeks.append({'start': start.isoformat(),
                      'label': f'{_short_date(start)}–{_short_date(end)}',
                      'count': sum(1 for n in nights
                                   if start <= _d(n) <= end)})

    months = [{'key': k, 'label': _d(f'{k}-01').strftime('%B %Y'),
               'count': sum(1 for n in nights if n.startswith(f'{k}-'))}
              for k in sorted({n[:7] for n in nights}, reverse=True)]

    current_week = current_month = None
    if show_all:
        selected, label = list(nights), 'all nights'
    elif month:
        selected = [n for n in nights if n.startswith(f'{month}-')]
        label = _d(f'{month}-01').strftime('%B %Y')
        current_month = month
    else:
        # Both the explicit week links and the default window are 7-day
        # blocks; the default is simply the one ending on the newest night.
        end = _d(week) + _dt.timedelta(days=6) if week else newest
        start = end - _dt.timedelta(days=6)
        selected = [n for n in nights if start <= _d(n) <= end]
        label = ('last 7 days' if not week
                 else f'{_short_date(start)}–{_short_date(end)}')
        current_week = start.isoformat()

    for w in weeks:
        w['current'] = (w['start'] == current_week)
    for m in months:
        m['current'] = (m['key'] == current_month)
    return selected, label, weeks, months


def _render_calendar_bar(camera, window_label, weeks, months):
    """One compact line: which window you're looking at, and a way out.

    The full week/month lists used to sit here as two rows of chips, which
    grew unboundedly and pushed the actual thumbnails below the fold. They
    now live on /astro/<cam>/nights; this is just the link to it.
    """
    if not window_label and not weeks:
        return ''
    more = ''
    # Only worth an index if there's history beyond the window on screen.
    if len(weeks) > 1 or len(months) > 1:
        more = (f'<a class="more-link" href="/astro/{camera}/nights">'
                f'browse all nights &rarr;</a>')
    return (f'<div class="calendar-bar">'
            f'<span class="window-label">{window_label}</span>{more}</div>')


def render_astro_nights_index(*, theme_css_js, title, camera, weeks, months,
                              total_nights=0):
    """Index of every published week and month for one camera.

    Deliberately thumbnail-free: it's a set of links, so it costs one S3
    read and no presigning at all, and stays the same size whether the
    camera has run for a month or a decade.
    """
    weeks, months = list(weeks), list(months)

    def _rows(items, href_of):
        if not items:
            return '<p class="empty">nothing published yet</p>'
        return ''.join(
            f'<a class="idx-row" href="{href_of(it)}">'
            f'<span class="idx-label">{it["label"]}</span>'
            f'<span class="idx-count">{it["count"]} '
            f'night{"" if it["count"] == 1 else "s"}</span></a>'
            for it in items)

    weeks_html = _rows(weeks, lambda w: f'/astro/{camera}/week/{w["start"]}')
    months_html = _rows(months, lambda m: f'/astro/{camera}/month/{m["key"]}')
    span = ''
    if weeks:
        span = (f'{total_nights} night{"" if total_nights == 1 else "s"} '
                f'across {len(months)} month'
                f'{"" if len(months) == 1 else "s"}')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} &mdash; all nights</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 700px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    h2 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-secondary); margin: 1.6rem 0 0.5rem; font-weight: 500; }}
    .idx-row {{ display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0.9rem; background: var(--card-bg); border-radius: 12px; margin-bottom: 0.35rem; text-decoration: none; color: inherit; }}
    .idx-row:hover {{ opacity: 0.85; }}
    .idx-label {{ color: var(--accent); }}
    .idx-count {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .empty {{ color: var(--text-secondary); font-size: 0.85rem; }}
    .all-link {{ display: block; text-align: center; padding: 0.7rem; margin-top: 1.2rem; background: var(--card-bg); border-radius: 12px; color: var(--accent); text-decoration: none; }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="subtitle">{span}</div>
    <h2>weeks</h2>
    {weeks_html}
    <h2>months</h2>
    {months_html}
    <a class="all-link" href="/astro/{camera}/all">every night on one page</a>
    <div class="footer"><a href="/astro/{camera}">&larr; last 7 days</a>
      &middot; <a href="/astro">Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def render_astro_camera_calendar(*, theme_css_js, title, camera,
                                 nights_with_meta,
                                 combined_brightness_url=None,
                                 moon_net_url=None,
                                 sun_net_url=None,
                                 window_label='', weeks=(), months=()):
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

    bar_html = _render_calendar_bar(camera, window_label, list(weeks),
                                    list(months))

    if not nights_with_meta:
        cards_html = ('<p class="empty">No nights in this window.</p>'
                      if weeks or months
                      else '<p class="empty">No nights published yet.</p>')
    else:
        cards = []
        for n in nights_with_meta:
            night = n["night"]
            thumb = n.get("thumb_url") or ""
            s = n.get("summary") or {}
            n_stacked = s.get("n_stacked")
            n_frames = s.get("n_frames")
            stops = s.get("stops")
            stats_parts = []
            if n_stacked is not None and n_frames is not None:
                stats_parts.append(f'{n_stacked}/{n_frames}')
            if stops is not None:
                stats_parts.append(f'{stops:.1f}' if isinstance(stops, (int, float)) else f'{stops}')
            stats = " &middot; ".join(stats_parts)
            poster = (f'<img src="{thumb}" alt="{night}" loading="lazy">'
                      if thumb else
                      '<div class="no-thumb">no preview</div>')
            cards.append(
                f'<a class="night-card" href="/astro/{camera}/night/{night}">'
                f'<div class="night-thumb">{poster}</div>'
                f'<div class="night-meta"><span class="night-date">{night}</span>'
                f'<span class="night-stats">{stats}</span></div></a>')
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
    .night-meta {{ display: flex; justify-content: space-between; align-items: baseline; padding: 0.45rem 0.65rem; }}
    .night-date {{ font-weight: 600; font-size: 0.85rem; }}
    .night-stats {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .combined {{ width: 100%; height: auto; background: #fff; display: block; margin-bottom: 0.3rem; }}
    .moon-net, .sun-net {{ width: 100%; height: auto; background: #000; display: block; margin-bottom: 0.3rem; }}
    .caption {{ color: var(--text-secondary); font-size: 0.8rem; margin: 0 0 1.5rem; text-align: center; }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    .calendar-bar {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin: 0.8rem 0 0.6rem; font-size: 0.85rem; }}
    .window-label {{ color: var(--text-secondary); }}
    .more-link {{ color: var(--accent); text-decoration: none; white-space: nowrap; }}
    .more-link:hover {{ opacity: 0.8; }}
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
    {bar_html}
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

    # --- Status flags: a compact string per (night,camera) -----------------
    # Peter 2026-07-29: want keeper/squashed/etc. back, but as a terse flag
    # string ("K", "S", "Kq", "--") that stays narrow and takes new statuses.
    # Flags, in fixed display order (see STATUS_LEGEND below):
    #   K keeper · q squashable · S squashed · C cold-archived
    # Keeper = clearest CLEAR night of its ISO week per camera (retention
    # policy). Squashed = reduced sum8/sum2 products present. Add a status by
    # appending to STATUS_LEGEND and emitting its letter in _status_flags.
    SHRUNK_KEYS = ("raw_sum8", "binned_sum2")
    STATUS_LEGEND = [("K", "keeper"), ("q", "squashable"),
                     ("S", "squashed"), ("C", "cold-archived")]

    def _night_verdict(locs):
        for it in locs:
            v = (it.get("verdict") or "").lower()
            if v:
                return v
        return ""

    def _row_shrunk(it):
        return bool(it.get("shrunk")) or any(
            k in (it.get("bytes") or {}) for k in SHRUNK_KEYS)

    week_nights = {}   # (camera, isoweek) -> [(night, bytes, verdict)]
    for (night, cam, kind), locs in by_nc.items():
        if kind == "day":
            continue
        try:
            wk = _dt.date.fromisoformat(night).isocalendar()[:2]
        except ValueError:
            continue
        week_nights.setdefault((cam, wk), []).append(
            (night, _night_bytes(locs), _night_verdict(locs)))
    keepers = set()    # (camera, night)
    for (cam, wk), nights in week_nights.items():
        clear = [n for n in nights if n[2] == "clear"]
        if clear:
            keepers.add((cam, max(clear, key=lambda n: n[1])[0]))
        elif not any(n[2] for n in nights):
            keepers.add((cam, max(nights, key=lambda n: n[1])[0]))

    def _status_flags(night, cam, kind, locs):
        if kind == "day":
            return "--"      # retention policy is night-sky only
        shrunk = any(_row_shrunk(it) for it in locs)
        cold = any(it.get("storage_class") == "deep-archive" for it in locs)
        keep = (cam, night) in keepers
        flags = ""
        if keep:
            flags += "K"
        if shrunk:
            flags += "S"
        elif not keep:
            flags += "q"     # squashable = not keeper, not yet squashed
        if cold:
            flags += "C"
        return flags or "--"

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
        status = _status_flags(night, cam, kind, locs)
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
            f'<td class="mx-st" title="{status}">{status}</td>'
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
    status_legend = " ".join(f"<b>{ch}</b> {lbl}" for ch, lbl in STATUS_LEGEND)
    cal_html = (
        '<table class="mx"><thead><tr>'
        '<th title="day of month">d</th><th>cam</th>'
        '<th class="mx-col" title="number of filesystems holding this night">#</th>'
        '<th class="mx-col" title="retention status">st</th>'
        + head_cols +
        '<th class="mx-col">size</th>'
        '</tr></thead><tbody>' + ("".join(mx_rows) or
        f'<tr><td colspan="{len(col_order)+5}" class="empty">'
        'No inventory this month.</td></tr>')
        + '</tbody></table>'
        f'<div class="axis-label"><span class="mx-toggle">{toggle}</span><br>'
        f'{legend}<br>'
        f'st: {status_legend} (– none) &middot; '
        '# = filesystems holding this night (dim col = none this month) &middot; '
        'orange row = only ONE copy.</div>')

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
    /* filesystem matrix — tuned for horizontal density */
    .mx {{ width: 100%; border-collapse: collapse; font-size: 0.7rem; }}
    .mx th {{ color: var(--text-secondary); font-weight: 500; font-size: 0.64rem; padding: 0.18rem 0.2rem; border-bottom: 1px solid var(--divider, #2C2C2E); }}
    .mx th:nth-child(1), .mx th:nth-child(2) {{ text-align: left; }}
    .mx td {{ padding: 0.18rem 0.2rem; }}
    .mx-col {{ text-align: center; }}
    .mx-st {{ text-align: center; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.66rem; color: var(--text-secondary); letter-spacing: -0.02em; }}
    .mx-col-empty {{ opacity: 0.35; }}
    /* vertical zebra: alternate columns tinted so the grid reads column-wise.
       fallback for older browsers, then currentColor mix (theme-aware). */
    .mx-za {{ background: transparent; }}
    .mx-zb {{ background: rgba(128,128,128,0.14); }}
    .mx-zb {{ background: color-mix(in srgb, currentColor 10%, transparent); }}
    .mx-toggle a {{ color: var(--accent); text-decoration: none; margin-right: 0.4rem; }}
    .mx td {{ border-bottom: 1px solid var(--divider, #2C2C2E); }}
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


def render_astro_disks(*, theme_css_js, capacity, inventory):
    """By-filesystem view: what astro data lives on each disk.

    Complements /astro/storage (by-night). Groups the inventory by filesystem
    and, within a disk, one line per camera with a compressed date-range and
    night count — e.g. "av2  0608-0727  (46)". Peter 2026-07-29.
    """
    import re as _re

    def _i(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    # Same filesystem taxonomy as the storage matrix (col, label, host,
    # path-prefix, sc). Kept in sync by hand; small enough not to factor out.
    FS = [
        ("bs",  "muppet /mnt/bigstore",     "muppet",     "/mnt/bigstore",  "local"),
        ("mup", "muppet ~ (home)",          "muppet",     "/home",          "local"),
        ("ecl", "eclipticam /mnt/ssd",      "eclipticam", None,             "local"),
        ("bd",  "muppet /mnt/bigdisk",      "muppet",     "/mnt/bigdisk",   "local"),
        ("bd2", "muppet /mnt/bigdisk2",     "muppet",     "/mnt/bigdisk2",  "local"),
        ("pd",  "muppet /mnt/photodisk",    "muppet",     "/mnt/photodisk", "local"),
        ("pup", "puppy ~ (home)",           "puppy",      None,             "local"),
        ("ab",  "muppet ASTROBACKUP (USB)", "muppet",     None,             "usb-stick"),
        ("s3",  "AWS S3 Deep Archive",      "aws",        None,             "deep-archive"),
    ]
    CAM_ABBR = {"starcam": "sv1", "astrocam": "av2",
                "eclipticam-v3w": "ev3w", "eclipticam-v1": "ev1",
                "astrocam-v3s": "av3s", "eos": "eos"}

    def _cam(c):
        return CAM_ABBR.get(str(c or "?"), str(c or "?"))

    def _fs_col(it):
        host = it.get("host", ""); path = str(it.get("path", ""))
        sc = it.get("storage_class", "local")
        for col, _l, ch, cp, cs in FS:
            if ch is not None and host != ch:
                continue
            if cs is not None and sc != cs:
                continue
            if cp is not None and not path.startswith(cp):
                continue
            return col
        return None

    # fs -> camera -> set(nights) and total bytes
    data = {}
    for it in inventory:
        if str(it.get("camera", "")).endswith("-deliverables"):
            continue
        if "_sweep" in str(it.get("camera", "")):
            continue
        col = _fs_col(it)
        if not col:
            continue
        cam = _cam(it.get("camera"))
        night = str(it.get("night", ""))
        if not _re.match(r"\d{4}-\d{2}-\d{2}", night):
            continue
        d = data.setdefault(col, {})
        e = d.setdefault(cam, {"nights": set(), "bytes": 0})
        e["nights"].add(night)
        e["bytes"] += sum(_i(v) for v in (it.get("bytes") or {}).values())

    def _mmdd(n):
        return n[5:7] + n[8:10]  # 2026-07-11 -> 0711

    # capacity lookup for the disk header (used/size)
    cap_by = {}
    for c in capacity:
        cap_by[(c.get("host"), c.get("fs"))] = c
    FS_MOUNT = {"bs": "/mnt/bigstore", "bd": "/mnt/bigdisk", "bd2": "/mnt/bigdisk2",
                "pd": "/mnt/photodisk", "ecl": "/mnt/ssd", "mup": "/", "pup": "/"}

    blocks = []
    for col, label, _h, _p, _sc in FS:
        d = data.get(col)
        if not d:
            continue
        # camera lines, sorted by abbrev
        lines = []
        for cam in sorted(d):
            ns = sorted(d[cam]["nights"])
            rng = (f"{_mmdd(ns[0])}–{_mmdd(ns[-1])}" if len(ns) > 1
                   else _mmdd(ns[0]))
            gib = d[cam]["bytes"] / (1024**3)
            sz = f"{gib:.0f} GB" if gib >= 1 else (f"{gib*1024:.0f} MB" if gib else "")
            lines.append(
                f'<div class="dk-cam"><span class="dk-c">{cam}</span>'
                f'<span class="dk-r">{rng}</span>'
                f'<span class="dk-n">({len(ns)})</span>'
                f'<span class="dk-sz">{sz}</span></div>')
        blocks.append(
            f'<div class="dk"><div class="dk-hd">'
            f'<span class="dk-col">{col}</span>'
            f'<span class="dk-label">{label}</span></div>'
            f'{"".join(lines)}</div>')
    disks_html = "".join(blocks) or '<p class="empty">No inventory.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Astro — Disks</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .dk {{ background: var(--card-bg); border-radius: 12px; padding: 0.6rem 0.9rem; margin-bottom: 0.6rem; }}
    .dk-hd {{ display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.3rem; border-bottom: 1px solid var(--divider, #2C2C2E); padding-bottom: 0.25rem; }}
    .dk-col {{ font-weight: 700; font-family: ui-monospace, Menlo, monospace; color: var(--accent); }}
    .dk-label {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .dk-cam {{ display: flex; gap: 0.6rem; align-items: baseline; font-size: 0.8rem; padding: 0.1rem 0; font-family: ui-monospace, Menlo, monospace; }}
    .dk-c {{ min-width: 3.2rem; font-weight: 600; }}
    .dk-r {{ min-width: 6rem; color: var(--text); }}
    .dk-n {{ min-width: 2.5rem; color: var(--text-secondary); }}
    .dk-sz {{ color: var(--text-secondary); text-align: right; flex: 1; }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Disks</h1>
    <div class="subtitle">what astro data lives on each filesystem — camera · date range · nights</div>
    {disks_html}
    <div class="footer"><a href="/astro/storage">by night &rarr;</a> &middot; <a href="/astro">Astro</a> &middot; <a href="/contents">Home</a></div>
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
    .caption a.dl {{ color: var(--accent); text-decoration: none; white-space: nowrap; }}
    .caption a.dl:hover {{ text-decoration: underline; }}
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


def render_colour_max_test(theme_css_js="", urls=None):
    urls = urls or {}
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Astro — Colour Max Stack Evaluation</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font, system-ui, sans-serif); background: var(--bg, #111); color: var(--text, #eee); margin: 0; padding: 1rem; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ font-size: 1.6rem; margin: 1rem 0 0.3rem; text-align: center; }}
    .intro {{ text-align: center; color: var(--text-secondary, #aaa); font-size: 0.9rem; max-width: 850px; margin: 0 auto 2rem; line-height: 1.5; }}
    h2 {{ font-size: 1.25rem; color: var(--accent, #4a9eff); margin: 2rem 0 0.8rem; border-bottom: 1px solid var(--divider, #333); padding-bottom: 0.3rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: var(--card-bg, #1a1a1a); border-radius: 8px; overflow: hidden; border: 1px solid var(--divider, #2a2a2a); }}
    .card img {{ width: 100%; height: auto; display: block; }}
    .card .caption {{ padding: 0.75rem 1rem; }}
    .card .title {{ font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }}
    .card .desc {{ font-size: 0.8rem; color: var(--text-secondary, #aaa); line-height: 1.4; }}
    a {{ color: var(--accent, #4a9eff); text-decoration: none; }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 3rem 0 1rem; color: var(--text-secondary, #888); }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Colour Max Stack Evaluation</h1>
    <div class="intro">
      Comparing <strong>Raw Luminance Max</strong> vs <strong>Frame-Average Normalised Max</strong> (where a pixel must be outstanding relative to the frame background: <code>L / mean(L)</code>) vs <strong>Per-Channel Max</strong>.
    </div>

    <h2>1. Eclipticam-v3w (Full Night — 2026-08-22)</h2>
    <div class="grid">
      <div class="card">
        <a href="{urls.get('eclipticam-v3w_2026-08-22_2_ratio_mean.jpg', '')}" target="_blank">
          <img src="{urls.get('eclipticam-v3w_2026-08-22_2_ratio_mean.jpg', '')}" alt="Eclipticam Ratio to Mean">
        </a>
        <div class="caption">
          <div class="title">Frame-Average Normalised Max (L / mean) &mdash; Best!</div>
          <div class="desc">Pixel must be outstanding relative to the frame average. Star trails extend right across the sky without being washed out by dawn/dusk sky brightness! Garden colours preserved.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('eclipticam-v3w_2026-08-22_1_raw_lum.jpg', '')}" target="_blank">
          <img src="{urls.get('eclipticam-v3w_2026-08-22_1_raw_lum.jpg', '')}" alt="Eclipticam Raw Lum">
        </a>
        <div class="caption">
          <div class="title">Raw Luminance Max (Dominated by Dawn/Dusk)</div>
          <div class="desc">Faint and mid-sky stars are overwritten by bright twilight sky diffuse glow.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('eclipticam-v3w_2026-08-22_per_channel.jpg', '')}" target="_blank">
          <img src="{urls.get('eclipticam-v3w_2026-08-22_per_channel.jpg', '')}" alt="Eclipticam Per Channel">
        </a>
        <div class="caption">
          <div class="title">Per-Channel Independent Max</div>
          <div class="desc">Maxes R, G, B independently per pixel across all frames.</div>
        </div>
      </div>
    </div>

    <h2>2. Astrocam (Full Night — 2026-08-22)</h2>
    <div class="grid">
      <div class="card">
        <a href="{urls.get('astrocam_2026-08-22_2_ratio_mean.jpg', '')}" target="_blank">
          <img src="{urls.get('astrocam_2026-08-22_2_ratio_mean.jpg', '')}" alt="Astrocam Ratio to Mean">
        </a>
        <div class="caption">
          <div class="title">Frame-Average Normalised Max (L / mean)</div>
          <div class="desc">Trails around Polaris are dense, sharp, and continuous. Distinct star colors (amber giants vs blue-white stars) are preserved.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('astrocam_2026-08-22_1_raw_lum.jpg', '')}" target="_blank">
          <img src="{urls.get('astrocam_2026-08-22_1_raw_lum.jpg', '')}" alt="Astrocam Raw Lum">
        </a>
        <div class="caption">
          <div class="title">Raw Luminance Max (Dawn/Dusk Dominated)</div>
          <div class="desc">Washed out by morning twilight.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('astrocam_2026-08-22_per_channel.jpg', '')}" target="_blank">
          <img src="{urls.get('astrocam_2026-08-22_per_channel.jpg', '')}" alt="Astrocam Per Channel">
        </a>
        <div class="caption">
          <div class="title">Per-Channel Independent Max</div>
          <div class="desc">Midnight window independent channel max.</div>
        </div>
      </div>
    </div>

    <h2>3. Canon EOS 2000D DSLR (2026-08-10)</h2>
    <div class="grid">
      <div class="card">
        <a href="{urls.get('canon_2026-08-10_lum_keyed.jpg', '')}" target="_blank">
          <img src="{urls.get('canon_2026-08-10_lum_keyed.jpg', '')}" alt="Canon Luminance Keyed">
        </a>
        <div class="caption">
          <div class="title">Luminance-Keyed RGB (Proposed)</div>
          <div class="desc">Pinpoint 30s star trails with rich stellar spectral colors.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('canon_2026-08-10_per_channel.jpg', '')}" target="_blank">
          <img src="{urls.get('canon_2026-08-10_per_channel.jpg', '')}" alt="Canon Per Channel">
        </a>
        <div class="caption">
          <div class="title">Per-Channel Independent Max</div>
          <div class="desc">Independent channel maxing across the 14-bit DSLR raws.</div>
        </div>
      </div>
      <div class="card">
        <a href="{urls.get('canon_2026-08-10_mono.jpg', '')}" target="_blank">
          <img src="{urls.get('canon_2026-08-10_mono.jpg', '')}" alt="Canon Monochrome Reference">
        </a>
        <div class="caption">
          <div class="title">Monochrome Max (Reference)</div>
          <div class="desc">Standard 2x2 binned mono max stack.</div>
        </div>
      </div>
    </div>

    <div class="footer"><a href="/astro">&larr; Astro Hub</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Transients — the curated general collection.
#
# Not a pipeline output: meteors, lightning, aircraft, satellites, screen
# grabs, and the daytime frames from the Canon focus work, published by
# hand with astro's bin/add-transient into transients/index.json. The
# Lambda reads that ONE manifest and presigns only the items it renders,
# the same shape as the per-camera calendar's fast path.

# Chip order + display labels for the categories the collection knows
# about. An unknown category still renders (titlecased, appended after
# these) — the gallery is meant to grow a category the day something new
# turns up in a frame.
TRANSIENT_CATEGORIES = [
    ("meteor", "Meteors"),
    ("lightning", "Lightning"),
    ("plane", "Aircraft"),
    ("satellite", "Satellites"),
    ("screen-grab", "Screen grabs"),
    ("daytime", "Daytime"),
    ("other", "Other"),
]


# How sure the classification is. A card that says "meteor" with no hedge
# is making a claim; these let it say how strong the claim is. Anything
# else the manifest carries is shown verbatim.
TRANSIENT_CONFIDENCE = {
    "confirmed": "confirmed",
    "likely": "likely",
    "possible": "possible",
    "unknown": "unclassified",
}


def _transient_label(cat):
    for slug, label in TRANSIENT_CATEGORIES:
        if slug == cat:
            return label
    return cat.replace("-", " ").title()


def transient_category_counts(items):
    """[(slug, label, count)] in chip order, known categories first,
    unknown ones appended alphabetically. Empty categories are dropped —
    a chip that filters to nothing is just a dead end."""
    counts = {}
    for e in items:
        counts[e.get("category") or "other"] = \
            counts.get(e.get("category") or "other", 0) + 1
    known = [s for s, _ in TRANSIENT_CATEGORIES]
    ordered = [s for s in known if counts.get(s)]
    ordered += sorted(s for s in counts if s not in known)
    return [(s, _transient_label(s), counts[s]) for s in ordered]


def render_astro_transients(*, theme_css_js, items, counts, selected=None):
    """Gallery of curated one-off captures.

    items: manifest entries (already filtered to `selected`), each with an
        added 'image_url' / 'thumb_url' presigned pair.
    counts: from transient_category_counts() over the UNFILTERED set, so
        the chips keep showing the whole collection while one is active.
    selected: category slug currently filtered to, or None for all.
    """
    total = sum(c for _s, _l, c in counts)
    chips = [
        f'<a class="chip{"" if selected else " on"}" href="/astro/transients">'
        f'All <span class="n">{total}</span></a>']
    for slug, label, n in counts:
        on = " on" if slug == selected else ""
        chips.append(f'<a class="chip{on}" href="/astro/transients/{slug}">'
                     f'{label} <span class="n">{n}</span></a>')
    chips_html = f'<div class="chips">{"".join(chips)}</div>'

    if not items:
        cards_html = ('<p class="empty">Nothing in this category yet.</p>'
                      if selected else
                      '<p class="empty">The collection is empty &mdash; '
                      'publish one with <code>astro/bin/add-transient</code>.</p>')
    else:
        cards = []
        for e in items:
            item_id = e.get("id") or ""
            thumb = e.get("thumb_url") or e.get("image_url") or ""
            full = e.get("image_url") or ""
            item_href = f"/astro/transients/{item_id}" if item_id else full
            # Meta line: date, clock time if we recorded one, camera.
            meta = [e.get("date") or ""]
            if e.get("time"):
                meta.append(e["time"])
            if e.get("camera"):
                meta.append(e["camera"])
            meta_html = " &middot; ".join(x for x in meta if x)
            caption = e.get("caption") or ""
            cap_paras = [p.strip() for p in caption.split("\n\n") if p.strip()] if caption else []
            cap_html = "".join(f'<p class="t-cap">{p}</p>' for p in cap_paras)

            rationale = e.get("rationale") or ""
            rat_paras = [p.strip() for p in rationale.split("\n\n") if p.strip()] if rationale else []
            why_paras = "".join(f'<p class="t-why">{p}</p>' for p in rat_paras)

            evidence = [x for x in (e.get("evidence") or []) if x]
            ev_html = f'<ul class="t-ev">{"".join(f"<li>{x}</li>" for x in evidence)}</ul>' if evidence else ""

            why_html = ""
            if why_paras or ev_html:
                why_html = f'<div class="t-reason">{why_paras}{ev_html}</div>'
            # A missing field reads as "unknown", not as silence: an
            # unhedged category label claims the classification is settled,
            # which is exactly what an entry with no confidence has not
            # established.
            conf = (e.get("confidence") or "unknown").lower()
            conf_html = ""
            if conf and conf != "confirmed":
                conf_html = (f'<span class="t-conf">'
                             f'{TRANSIENT_CONFIDENCE.get(conf, conf)}</span>')
            # A night link only when that night actually has a page.
            night_html = ""
            if e.get("night") and e.get("camera") in (
                    "astrocam", "eclipticam", "canon"):
                night_html = (
                    f'<a class="t-night" '
                    f'href="/astro/{e["camera"]}/night/{e["night"]}">'
                    f'night page &rarr;</a>')
            detail_link = f'<a class="t-view" href="{item_href}">Picture &amp; Analysis &rarr;</a>' if item_id else ''
            poster = (f'<img src="{thumb}" alt="{e.get("title", "")}" '
                      f'loading="lazy">' if thumb else
                      '<div class="no-thumb">no preview</div>')
            title_text = e.get("title", "")
            title_html = f'<a class="t-title-link" href="{item_href}">{title_text}</a>' if item_id else title_text
            cards.append(
                f'<figure class="t-card">'
                f'<a class="t-shot" href="{item_href}">{poster}</a>'
                f'<figcaption>'
                f'<div class="t-head">'
                f'<span class="t-title">{title_html}</span>'
                f'<span class="t-badge">'
                f'{_transient_label(e.get("category") or "other")}'
                f'{conf_html}</span>'
                f'</div>'
                f'<div class="t-meta">{meta_html}</div>'
                f'{cap_html}{why_html}'
                f'<div class="t-links">{night_html}{detail_link}</div>'
                f'</figcaption></figure>')
        cards_html = f'<div class="t-grid">{"".join(cards)}</div>'

    heading = ("Transients" if not selected
               else f"Transients &mdash; {_transient_label(selected)}")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transients</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1rem 0 0.2rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.2rem; line-height: 1.5; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: center; margin-bottom: 1.2rem; }}
    .chip {{ display: inline-block; padding: 0.25rem 0.7rem; border-radius: 999px; background: var(--card-bg); color: var(--text-secondary); text-decoration: none; font-size: 0.8rem; }}
    .chip:hover {{ opacity: 0.85; }}
    .chip.on {{ color: var(--accent); }}
    .chip .n {{ opacity: 0.6; font-size: 0.72rem; margin-left: 0.2rem; }}
    .t-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }}
    .t-card {{ margin: 0; background: var(--card-bg); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }}
    .t-shot {{ display: block; background: #000; overflow: hidden; }}
    .t-shot img {{ width: 100%; height: auto; display: block; transition: transform 0.3s ease; }}
    .t-shot:hover img {{ transform: scale(1.02); }}
    .no-thumb {{ color: var(--text-secondary); font-size: 0.85rem; padding: 2rem; text-align: center; }}
    figcaption {{ padding: 0.75rem 0.85rem 0.85rem; display: flex; flex-direction: column; flex: 1; }}
    .t-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }}
    .t-title {{ font-weight: 600; font-size: 0.95rem; }}
    .t-title-link {{ color: inherit; text-decoration: none; }}
    .t-title-link:hover {{ color: var(--accent); }}
    .t-badge {{ color: var(--text-secondary); font-size: 0.7rem; white-space: nowrap; }}
    .t-meta {{ color: var(--text-secondary); font-size: 0.78rem; margin-top: 0.2rem; }}
    .t-cap {{ font-size: 0.86rem; color: var(--text, #e0e0e0); line-height: 1.5; margin: 0.45rem 0 0; }}
    .t-cap + .t-cap {{ margin-top: 0.5rem; }}
    .t-conf {{ display: block; font-size: 0.66rem; opacity: 0.75; }}
    .t-reason {{ margin-top: 0.55rem; padding-top: 0.5rem; border-top: 1px solid var(--divider, #2C2C2E); }}
    .t-why {{ font-size: 0.86rem; color: var(--text, #e0e0e0); line-height: 1.5; margin: 0.3rem 0 0; }}
    .t-why + .t-why {{ margin-top: 0.5rem; }}
    .t-ev {{ font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; margin: 0.35rem 0 0; padding-left: 1.1rem; }}
    .t-ev li {{ margin-bottom: 0.15rem; }}
    .t-links {{ display: flex; justify-content: space-between; align-items: center; margin-top: 0.6rem; padding-top: 0.4rem; border-top: 1px solid rgba(255,255,255,0.04); font-size: 0.78rem; }}
    .t-night {{ color: var(--accent); text-decoration: none; }}
    .t-view {{ color: var(--accent); text-decoration: none; font-weight: 500; margin-left: auto; }}
    .t-view:hover {{ text-decoration: underline; }}
    .empty {{ text-align: center; color: var(--text-secondary); }}
    code {{ font-size: 0.85em; }}
    .footer {{ text-align: center; font-size: 0.85rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{heading}</h1>
    <div class="subtitle">A collection of short lived events.</div>
    {chips_html}
    {cards_html}
    <div class="footer"><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def render_astro_transient_detail(*, theme_css_js, item, prev_item=None, next_item=None):
    """Dedicated single-picture page for a curated transient capture."""
    title = item.get("title") or "Transient Capture"
    item_id = item.get("id") or ""
    cat = item.get("category") or "other"
    cat_label = _transient_label(cat)
    conf = (item.get("confidence") or "unknown").lower()
    conf_label = TRANSIENT_CONFIDENCE.get(conf, conf) if conf != "confirmed" else ""

    full_url = item.get("image_url") or item.get("thumb_url") or ""
    thumb_url = item.get("thumb_url") or full_url

    meta = [item.get("date") or ""]
    if item.get("time"):
        meta.append(item["time"])
    if item.get("camera"):
        meta.append(item["camera"])
    meta_str = " &middot; ".join(x for x in meta if x)

    caption = item.get("caption") or ""
    rationale = item.get("rationale") or ""
    evidence = [x for x in (item.get("evidence") or []) if x]

    night_link = ""
    if item.get("night") and item.get("camera") in ("astrocam", "eclipticam", "canon"):
        night_link = (f'<a class="hud-link" href="/astro/{item["camera"]}/night/{item["night"]}">'
                      f'Full Observing Night Page ({item["night"]}) &rarr;</a>')

    prev_link = ""
    if prev_item and prev_item.get("id"):
        p_id = prev_item["id"]
        p_title = prev_item.get("title", "Previous")
        prev_link = f'<a class="nav-btn prev" href="/astro/transients/{p_id}">&larr; {p_title}</a>'

    next_link = ""
    if next_item and next_item.get("id"):
        n_id = next_item["id"]
        n_title = next_item.get("title", "Next")
        next_link = f'<a class="nav-btn next" href="/astro/transients/{n_id}">{n_title} &rarr;</a>'

    caption = item.get("caption") or ""
    rationale = item.get("rationale") or ""
    all_paras = []
    if caption:
        all_paras.extend([p.strip() for p in caption.split("\n\n") if p.strip()])
    if rationale:
        all_paras.extend([p.strip() for p in rationale.split("\n\n") if p.strip()])
    prose_html = "".join(f'<p>{p}</p>' for p in all_paras)

    ev_block = ""
    if evidence:
        ev_items = "".join(f"<li>{x}</li>" for x in evidence)
        ev_block = f'''
        <div class="prose-block">
          <h2>Evidence &amp; Discriminator Points</h2>
          <ul class="ev-list">{ev_items}</ul>
        </div>
        '''

    conf_badge = f'<span class="t-badge-conf">{conf_label}</span>' if conf_label else ''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | Transients</title>
  <meta name="description" content="{caption[:160] if caption else title}" />
  {theme_css_js}
  <style>
    body {{
      font-family: var(--font, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
      background: var(--bg, #000);
      color: var(--text, #e0e0e0);
      margin: 0;
      padding: 1rem 1rem 3rem;
      line-height: 1.6;
    }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    .breadcrumbs {{
      font-size: 0.82rem;
      color: var(--text-secondary, #8e8e93);
      margin: 0.5rem 0 1.2rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .breadcrumbs a {{ color: var(--accent, #007aff); text-decoration: none; }}
    .breadcrumbs .sep {{ opacity: 0.4; }}
    .photo-header {{ margin-bottom: 1.2rem; }}
    .photo-tags {{ display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.4rem; }}
    .t-badge-main {{
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--accent, #007aff);
      background: rgba(0, 122, 255, 0.12);
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
    }}
    .t-badge-conf {{
      font-size: 0.72rem;
      color: var(--text-secondary, #8e8e93);
      background: var(--card-bg, #1c1c1e);
      padding: 0.15rem 0.5rem;
      border-radius: 999px;
    }}
    h1 {{ font-size: 2rem; margin: 0.2rem 0 0.3rem; font-weight: 700; }}
    .photo-meta {{ color: var(--text-secondary, #8e8e93); font-size: 0.88rem; }}
    .viewer-frame {{
      position: relative;
      background: #000;
      border-radius: 12px;
      border: 1px solid var(--divider, #2c2c2e);
      overflow: hidden;
      margin: 1.5rem 0 2rem;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
    }}
    .viewer-media {{ cursor: zoom-in; display: block; }}
    .viewer-media img {{
      width: 100%;
      height: auto;
      max-height: 80vh;
      object-fit: contain;
      display: block;
      margin: 0 auto;
    }}
    .viewer-hint {{
      position: absolute;
      bottom: 0.8rem;
      right: 0.8rem;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      color: var(--accent, #007aff);
      font-size: 0.75rem;
      padding: 0.3rem 0.7rem;
      border-radius: 6px;
      pointer-events: none;
    }}
    .zoom-modal {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.95);
      z-index: 100000;
      overflow: auto;
      backdrop-filter: blur(8px);
      align-items: center;
      justify-content: center;
    }}
    .zoom-modal.open {{ display: flex; }}
    .zoom-modal img {{
      max-width: 95vw;
      max-height: 95vh;
      object-fit: contain;
      cursor: zoom-out;
      border-radius: 4px;
    }}
    .modal-close {{
      position: fixed;
      top: 1.5rem;
      right: 1.5rem;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: #fff;
      font-size: 1.5rem;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100001;
    }}
    .prose-section {{ display: flex; flex-direction: column; gap: 1.2rem; margin-bottom: 2.5rem; }}
    .prose-block {{
      background: var(--card-bg, #161616);
      border: 1px solid var(--divider, #2c2c2e);
      border-radius: 10px;
      padding: 1.4rem 1.6rem;
    }}
    .prose-block h2 {{
      font-size: 1.05rem;
      margin: 0 0 0.6rem;
      font-weight: 600;
      color: var(--accent, #007aff);
    }}
    .prose-block p {{ margin: 0; font-size: 0.95rem; line-height: 1.65; color: var(--text, #e0e0e0); }}
    .prose-block p + p {{ margin-top: 1rem; }}
    .ev-list {{ margin: 0; padding-left: 1.2rem; font-size: 0.88rem; line-height: 1.55; color: var(--text-secondary, #8e8e93); }}
    .ev-list li {{ margin-bottom: 0.35rem; }}
    .hud-link {{ display: inline-block; margin-top: 0.8rem; color: var(--accent, #007aff); font-size: 0.85rem; text-decoration: none; }}
    .hud-link:hover {{ text-decoration: underline; }}
    .nav-bar {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin: 2rem 0 1rem;
      padding-top: 1.2rem;
      border-top: 1px solid var(--divider, #2c2c2e);
    }}
    .nav-btn {{
      display: inline-block;
      padding: 0.5rem 1rem;
      background: var(--card-bg, #161616);
      border: 1px solid var(--divider, #2c2c2e);
      border-radius: 6px;
      color: var(--accent, #007aff);
      text-decoration: none;
      font-size: 0.82rem;
    }}
    footer.site-footer {{ text-align: center; color: var(--text-secondary, #8e8e93); font-size: 0.85rem; margin-top: 2rem; }}
    footer.site-footer a {{ color: var(--accent, #007aff); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <nav class="breadcrumbs" aria-label="Breadcrumbs">
      <a href="/astro">Astro</a>
      <span class="sep">/</span>
      <a href="/astro/transients">Transients</a>
      <span class="sep">/</span>
      <span>{title}</span>
    </nav>

    <header class="photo-header">
      <div class="photo-tags">
        <span class="t-badge-main">{cat_label}</span>
        {conf_badge}
      </div>
      <h1>{title}</h1>
      <div class="photo-meta">{meta_str}</div>
    </header>

    <main>
      <div class="viewer-frame">
        <div class="viewer-media" id="media-zoom-trigger" title="Click for high-resolution zoom">
          <img src="{full_url}" alt="{title}" fetchpriority="high" />
        </div>
        <div class="viewer-hint">&x1F50D; Click to zoom</div>
      </div>

      <div class="zoom-modal" id="zoom-modal" role="dialog" aria-modal="true">
        <button class="modal-close" id="modal-close" aria-label="Close zoom modal">&times;</button>
        <img id="zoom-img" src="{full_url}" alt="{title}" />
      </div>

      <section class="prose-section">
        {f'<div class="prose-block">{prose_html}</div>' if prose_html else ''}
        {ev_block}
        {f'<div class="prose-block"><h2>Associated Observing Night</h2>{night_link}</div>' if night_link else ''}
      </section>

      <nav class="nav-bar">
        <div>{prev_link}</div>
        <div>{next_link}</div>
      </nav>
    </main>

    <footer class="site-footer">
      <a href="/astro/transients">&larr; Back to Transients Gallery</a> &middot;
      <a href="/astro">Astro Hub</a> &middot;
      <a href="/contents">Home</a>
    </footer>
  </div>

  <script>
    (function(){{
      var trigger = document.getElementById('media-zoom-trigger');
      var modal = document.getElementById('zoom-modal');
      var closeBtn = document.getElementById('modal-close');
      var zoomImg = document.getElementById('zoom-img');

      if (!trigger || !modal) return;

      function openModal() {{
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
      }}
      function closeModal() {{
        modal.classList.remove('open');
        document.body.style.overflow = '';
      }}

      trigger.addEventListener('click', openModal);
      if (closeBtn) closeBtn.addEventListener('click', closeModal);
      modal.addEventListener('click', function(e) {{
        if (e.target === modal || e.target === zoomImg) {{
          closeModal();
        }}
      }});
      document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape' && modal.classList.contains('open')) {{
          closeModal();
        }}
      }});
    }})();
  </script>
</body>
</html>'''
