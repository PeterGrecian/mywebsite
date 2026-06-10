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
        "desc": "Pi 4 + Camera Module v2 (IMX219). Nightly max/min/sum stacks with hot/cold pixel masking.",
        "status": "soon",
    },
    {
        "path": "/astro/eclipticam",
        "title": "Ecliptic Camera",
        "desc": "Two-camera Pi (OV5647 v1 + IMX708 Wide) — day and night astro along the ecliptic.",
        "status": "soon",
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


def render_astro_stub(*, theme_css_js, title):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 600px; margin: 4rem auto; text-align: center; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.5rem; }}
    p {{ color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; }}
    a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <p>Coming soon.</p>
    <p><a href="/astro">&larr; Astro</a> &middot; <a href="/contents">Home</a></p>
  </div>
</body>
</html>'''
