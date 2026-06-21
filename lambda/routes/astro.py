"""Astro hub page — lists the project's astronomy cameras."""


CAMERAS = [
    {
        "path": "/starcam",
        "title": "Star Camera",
        "desc": "Zenith-pointing OV5647 — nightly stacks, plate-solved frames, derotation experiments.",
        "status": "live",
    },
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
    # Hero: the sliding-window colour video; mono sibling below for the
    # science-leaning view. Both are window-stack-sweep outputs sharing
    # the same time burn-in and autodetected window.
    # Poster = the mid-night frame of the colour sweep (thumb.jpg), so
    # the player preview is a frame FROM the clip rather than the
    # unrelated star-trail max-stack. Fall back to max.jpg for older
    # nights that predate thumb.jpg.
    poster = urls.get("thumb.jpg") or urls.get("max.jpg", "")
    for key, cap in (
        ("sweep-colour.mp4",
         "colour sweep — 10 min stack sliding 1 min per frame, 60 fps; "
         "story of the night in 5 seconds"),
        ("sweep-mono.mp4",
         "monochrome sweep — same window, greyscale (science view)"),
        ("sweep-diff.mp4",
         "difference sweep — max(frame) − window mean; the sky floor, "
         "hot pixels, and cloud-glow cancel, leaving only trails and "
         "transients"),
    ):
        url = urls.get(key)
        if url:
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
                                 combined_brightness_url=None):
    """Calendar of nights for a camera, newest first.

    nights_with_meta: list of {"night": "YYYY-MM-DD", "thumb_url": ...|None,
                               "summary": dict|None}
    combined_brightness_url: presigned URL of the multi-night overlay
        plot (or None — section is hidden if absent).
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
    {cards_html}
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
