"""Manim animations page — videos rendered locally and uploaded to S3."""

S3_BASE = "https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/manim"

# Each entry: scene class name (= S3 mp4 filename stem), title, description.
# Add a new entry after running ./render-and-upload.sh in ~/manim.
SCENES = [
    {
        "class": "PlanetsAndStarsIntro",
        "title": "Planets and Stars — Intro",
        "desc": "Telling planets from stars at a glance. The first rule: planets don't twinkle.",
    },
]


def render_manim_page(*, theme_css_js):
    cards = ""
    for s in SCENES:
        url = f"{S3_BASE}/{s['class']}.mp4"
        cards += f'''<div class="scene-card">
  <div class="scene-title">{s["title"]}</div>
  <p class="scene-desc">{s["desc"]}</p>
  <video controls preload="metadata" playsinline>
    <source src="{url}" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</div>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manim — Animations</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 800px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1.5rem 0 0.3rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .intro {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.85rem; line-height: 1.6; color: var(--text-secondary); }}
    .intro a {{ color: var(--accent); text-decoration: none; }}
    .scene-card {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }}
    .scene-title {{ font-size: 1.05rem; font-weight: 600; color: var(--text); }}
    .scene-desc {{ font-size: 0.85rem; color: var(--text-secondary); margin: 0.4rem 0 0.7rem; line-height: 1.5; }}
    video {{ width: 100%; height: auto; border-radius: 8px; background: #000; display: block; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Manim Animations</h1>
    <div class="subtitle">a short guide to identifying the planets and stars</div>
    <div class="intro">
      Animations built with <a href="https://www.manim.community/" target="_blank">ManimCE</a>,
      the community fork of Grant Sanderson's animation engine for 3Blue1Brown.
      Source code: <a href="https://github.com/PeterGrecian/manim" target="_blank">github.com/PeterGrecian/manim</a>.
    </div>
{cards}
    <div class="footer">
      <a href="/contents">Home</a>
    </div>
  </div>
</body>
</html>'''
