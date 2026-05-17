"""Stereo photography — gallery and WebXR viewer."""

import json
import boto3

S3_BUCKET = "petergrecian.co.uk"
S3_PREFIX = "stereo"
S3_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/"
S3_VIDEO_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/video/"

# Beauty renders live on Cloudflare R2 with custom domain (free egress).
R2_VIDEO_BASE = "https://stereo.petergrecian.co.uk/"

# Human-readable labels for shot dir slugs. Falls back to slug if missing.
PLACE_LABELS = {
    "barbican": "Barbican",
    "from-waterloo-bridge-bus-20260424-full": "From Waterloo Bridge (bus)",
    "kingston-1348": "Kingston by Bus (13:48)",
    "kingston-1356": "Kingston by Bus (13:56)",
    "may1-1123": "May 1 — 11:23 set",
    "may1-1223": "May 1 — 12:23 set",
    "nine-elms-20260424": "Nine Elms",
    "vauxhall": "Vauxhall",
}


# Beauty renders — finished pieces served from R2.
# url is full https URL (R2 custom domain).
# Structured pipeline metadata (source_fps, output_fps, source_mbps, output_mbps,
# mci, baseline_s) is shown by the video viewers' info panel. baseline_s is in
# seconds; the viewer also derives the equivalent in source frames as
# round(baseline_s × source_fps).
BEAUTY_RENDERS = [
    {
        "slug": "clouds-train-2-b4-1k-nomci-skymask",
        "url": R2_VIDEO_BASE + "clouds-train-2-b4-1k-nomci-skymask.mp4",
        "title": "Clouds from train — 4s baseline + sky mask",
        "subtitle": "1:28 · 1K stereo · 30 fps native · 4.0s baseline · HSV-intersection sky mask",
        "notes": "Same 4s-baseline render as the adjacent variant, with a post-process sky mask: HSV-threshold per eye, intersect (parallax-aware so foreground clutter fails), feather, composite over a pale-blue sampled from the first frame's brightest agreed-sky pixels. Non-sky regions dissolve into uniform pale-blue, leaving the cloud composition unfought. Smaller file (10 MiB vs 15 MiB) because uniform fill compresses better.",
        "source_fps": 30, "output_fps": 30,
        "source_mbps": 20, "output_mbps": 0.9,
        "mci": False, "baseline_s": 4.0,
    },
    {
        "slug": "clouds-train-2-b3-1k-nomci",
        "url": R2_VIDEO_BASE + "clouds-train-2-b3-1k-nomci.mp4",
        "title": "Clouds from train — 3s baseline (no MCI)",
        "subtitle": "1:29 · 1K stereo · 30 fps native · 3.0s baseline · single-stage Cloud Run",
        "notes": "92s source rendered in one ffmpeg pass on Cloud Run (8 vCPU, 4 GiB, ~5 min wall). No motion-compensated interpolation — source 30 fps passes through unchanged. Single-stage pipeline (inline-v5-nomci.sh) skips the split-and-join because there's no slow stage to parallelise without MCI.",
        "source_fps": 30, "output_fps": 30,
        "source_mbps": 20, "output_mbps": 1.4,
        "mci": False, "baseline_s": 3.0,
    },
    {
        "slug": "clouds-train-2-b4-1k-nomci",
        "url": R2_VIDEO_BASE + "clouds-train-2-b4-1k-nomci.mp4",
        "title": "Clouds from train — 4s baseline (no MCI)",
        "subtitle": "1:28 · 1K stereo · 30 fps native · 4.0s baseline · single-stage Cloud Run",
        "notes": "92s source rendered in one ffmpeg pass on Cloud Run (8 vCPU, 4 GiB). 4s baseline sits between the 3s and 5s variants for direct comparison of how baseline affects perceived cloud depth.",
        "source_fps": 30, "output_fps": 30,
        "source_mbps": 20, "output_mbps": 1.4,
        "mci": False, "baseline_s": 4.0,
    },
    {
        "slug": "clouds-train-2-b10-1k",
        "url": R2_VIDEO_BASE + "clouds-train-2-b10-1k.mp4",
        "title": "Clouds from train — 10s baseline",
        "subtitle": "1:22 · 1K stereo · 30→60 fps mci · 10.0s baseline · 3-part join",
        "notes": "92s source rendered via the three-stage long-baseline pipeline: 3×31s prep-mci parts in parallel with seam-frame borrowing, mono concat, then 10s stereo offset. Wide baseline emphasises the depth of cloud layers.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 1.7,
        "mci": True, "baseline_s": 10.0,
    },
    {
        "slug": "clouds-train-2-b5-1k",
        "url": R2_VIDEO_BASE + "clouds-train-2-b5-1k.mp4",
        "title": "Clouds from train — 5s baseline",
        "subtitle": "1:27 · 1K stereo · 30→60 fps mci · 5.0s baseline · 3-part join",
        "notes": "Same 92s source as the 10s render, with a 5s baseline for comparison. Three-stage pipeline with bridge-frame-clean joins between parts.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 1.6,
        "mci": True, "baseline_s": 5.0,
    },
    {
        "slug": "clouds-train-2-test-0p5k-v3",
        "url": R2_VIDEO_BASE + "clouds-train-2-test-0p5k-v3.mp4",
        "title": "Clouds from train — 9s seam test (0.5K)",
        "subtitle": "0:07 · 0.5K stereo · 30→60 fps mci · 2.0s baseline · 3-part join",
        "notes": "Validation of the three-stage long-baseline pipeline. 9s source split into 3×3s parts, each prep-mci'd in parallel with seam-frame borrowing (option-2 fix from gardencam) so the two interior joins are bridge-frame-clean. Concat + symmetric head/tail trim for time-aligned stereo. End-to-end ~20 min, mostly VM allocation; ffmpeg work ~70s total.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 0.6,
        "mci": True, "baseline_s": 2.0,
    },
    {
        "slug": "kingston-bus-1k",
        "url": R2_VIDEO_BASE + "kingston-bus-1k.mp4",
        "title": "Kingston by Bus",
        "subtitle": "1K stereo · 30→60 fps mci · 1-frame baseline",
        "notes": "Landscape pan from the top deck through Kingston. 1-frame baseline (0.0167s) appropriate for the close-foreground bus context. inline-v4 single-pass pipeline on e2-standard-2, eye_order right-early baked in.",
        "source_fps": 60, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 5.0,
        "mci": True, "baseline_s": 0.0167,
    },
    {
        "slug": "clouds-train-2-1k",
        "url": R2_VIDEO_BASE + "clouds-train-2-1k.mp4",
        "title": "Clouds from train — 92s split-and-join test",
        "subtitle": "1:32 · 1K stereo · 30→60 fps mci · 2.0s baseline",
        "notes": "1080p Top Shot source rendered as three parallel 30s parts on e2-standard-2 (2 vCPU, 8 GiB) with a fourth concat job polling GCS until all parts present. Total wall 29 min vs ~110 min sequential = 3.8× speedup. First run with STEREO_EYE_ORDER=right-early baked into the encode (no post-swap needed).",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 5.0,
        "mci": True, "baseline_s": 2.0,
    },
    {
        "slug": "clouds-train-1-1k",
        "url": R2_VIDEO_BASE + "clouds-train-1-1k.mp4",
        "title": "Clouds from train — 4K source at 1K",
        "subtitle": "0:46 · 1K stereo · 30→60 fps mci · 2.0s baseline",
        "notes": "4K source downscaled in prep stage to 1K (1280×720) per eye before mci. CRF 28 single-pass on e2-standard-2 (2 vCPU, 8 GiB). Peak RAM 5.97 GiB, wall 48 min. Eyes swapped post-encode for right-to-left camera motion.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 43, "output_mbps": 3.7,
        "mci": True, "baseline_s": 2.0,
    },
    {
        "slug": "clouds-train-3-1k",
        "url": R2_VIDEO_BASE + "clouds-train-3-1k.mp4",
        "title": "Clouds from train — 1K test",
        "subtitle": "0:18 · 1K stereo · 30→60 fps mci · 2.0s baseline",
        "notes": "First clouds-from-train experiment. 1080p Top Shot source downscaled to 1K (1280×720) per eye, mci interpolation, CRF 28. Eyes swapped post-encode for right-to-left camera motion.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 5.0,
        "mci": True, "baseline_s": 2.0,
    },
    {
        "slug": "waterloo-60",
        "url": R2_VIDEO_BASE + "waterloo-60.mp4",
        "title": "Arrival at Waterloo",
        "subtitle": "4:18 · 1080p stereo · 30→60 fps mci",
        "notes": "Bus-train journey from Surbiton ending at Waterloo. Software-encoded HEVC two-pass slow preset, 8 segments rendered in parallel on GCP Batch, served from Cloudflare R2.",
        "source_fps": 30, "output_fps": 60,
        "source_mbps": 20, "output_mbps": 5.0,
        "mci": True, "baseline_s": 0.0333,
    },
]


def _beauty_info_html(video_url):
    """Build a small info block describing the render pipeline for a beauty video.
    Returns empty string if the URL isn't a known beauty render."""
    b = next((b for b in BEAUTY_RENDERS if b["url"] == video_url), None)
    if not b:
        return ""
    src_fps = b.get("source_fps")
    out_fps = b.get("output_fps")
    src_mbps = b.get("source_mbps")
    out_mbps = b.get("output_mbps")
    mci = b.get("mci")
    base_s = b.get("baseline_s")
    if src_fps is None:
        return ""
    base_frames = round(base_s * src_fps) if base_s is not None else None
    pipeline = f"{src_fps} fps @ {src_mbps} Mbps → {out_fps} fps @ {out_mbps} Mbps"
    mci_str = "MCI" if mci else "no MCI"
    base_str = (f"baseline {base_s:g}s = {base_frames} src frame"
                + ("s" if base_frames != 1 else "")) if base_s is not None else ""
    return (
        '<div class="render-info">'
        f'<span>{pipeline}</span>'
        f'<span>{mci_str}</span>'
        f'<span>{base_str}</span>'
        '</div>'
    )


# Manually curated video list — add entries here after uploading to S3
# visible=False marks videos known to fail in the WebXR viewer (under investigation)
STEREO_VIDEOS = [
    {"file": "may1-105049-mb4.mp4", "label": "Railway 25s — motion blur 4×", "note": "2K · dormouse · optical-flow blur", "visible": False},
    {"file": "may1-105132-mb4.mp4", "label": "Railway 64s — motion blur 4×", "note": "2K · ferret · optical-flow blur", "visible": True},
    {"file": "may1-lift-mb4.mp4", "label": "LIFT TEST — motion blur 4×", "note": "Barbican view, rotated 90°, optical-flow blur", "visible": False},
    {"file": "may1-105249-2k.mp4", "label": "Arrival at Waterloo (4 min)", "note": "2K · 3840×1080 · 1-frame baseline · NO blur", "visible": True},
    {"file": "may1-105132-2k.mp4", "label": "Railway 64s — May 2026", "note": "2K · 3840×1080 · squirrel · NO blur", "visible": False},
    {"file": "may1-105049-2k.mp4", "label": "Railway 25s — May 2026", "note": "2K · 3840×1080 · magpie · NO blur", "visible": True},
]


def _list_shots():
    """List all shot metadata from S3, sorted by inliers descending."""
    s3 = boto3.client("s3", region_name="eu-west-1")
    paginator = s3.get_paginator("list_objects_v2")
    shots = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX + "/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                try:
                    resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    meta = json.loads(resp["Body"].read())
                    shots.append(meta)
                except Exception:
                    pass
    shots.sort(key=lambda x: x.get("inliers", 0), reverse=True)
    return shots


_GALLERY_CSS = '''
    body { font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }
    .container { max-width: 600px; margin: 0 auto; }
    h1 { font-size: 1.4rem; margin: 1rem 0 0.3rem; text-align: center; }
    h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
    .subtitle { text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }
    .shot-card {
      display: block; text-decoration: none;
      background: var(--card-bg); border-radius: 12px;
      padding: 1rem 1.2rem; margin-bottom: 0.75rem;
      border: 1px solid var(--divider);
    }
    .shot-card:hover { opacity: 0.8; }
    .shot-title { font-size: 1.05rem; font-weight: 600; color: var(--accent); margin-bottom: 0.3rem; }
    .shot-meta { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); }
    .empty { text-align: center; color: var(--text-secondary); margin-top: 2rem; }
    .footer { text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }
    .footer a { color: var(--accent); text-decoration: none; }
'''


def _place_label(slug: str) -> str:
    return PLACE_LABELS.get(slug, slug)


def render_index_page(*, theme_css_js):
    """Top-level index: links to beauty renders, per-place stills, per-visibility video pages."""
    shots = _list_shots()
    places = sorted({s.get("slug", "") for s in shots})

    place_links = "".join(
        f'<a class="shot-card" href="/stereo?place={slug}">'
        f'<div class="shot-title">{_place_label(slug)}</div></a>'
        for slug in places
    ) or '<p class="empty">No stereo images yet.</p>'

    has_visible   = any(v.get("visible", True)     for v in STEREO_VIDEOS)
    has_invisible = any(not v.get("visible", True) for v in STEREO_VIDEOS)

    video_links = ""
    if has_visible:
        video_links += '<a class="shot-card" href="/stereo?videos=visible">' \
                       '<div class="shot-title">Visible</div></a>'
    if has_invisible:
        video_links += '<a class="shot-card" href="/stereo?videos=invisible">' \
                       '<div class="shot-title">Invisible (under investigation)</div></a>'

    beauty_section = ""
    if BEAUTY_RENDERS:
        beauty_section = '<h2>Beauty renders</h2>' + \
            '<a class="shot-card" href="/stereo?beauty=1">' \
            '<div class="shot-title">All beauty renders</div></a>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stereo Photography</title>
  {theme_css_js}
  <style>{_GALLERY_CSS}</style>
</head>
<body>
  <div class="container">
    <h1>Stereo Photography</h1>
    <div class="subtitle">Quest 2 VR</div>
    {beauty_section}
    <h2>Stills by location</h2>
    {place_links}
    <h2>Videos</h2>
    {video_links}
    <div class="footer"><a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def render_beauty_page(*, theme_css_js):
    """List of beauty renders — finished pieces served from R2."""
    def beauty_card(b):
        # Each card has Sphere VR + Flat VR buttons that pass the full URL
        # as the video param (the viewer functions detect http:// and route).
        url_param = b["url"]
        return f'''
    <div class="shot-card">
      <div class="shot-title">{b["title"]}</div>
      <div class="shot-meta" style="margin-bottom:0.5rem;">
        <span class="quality">{b.get("subtitle", "")}</span>
      </div>
      <div style="font-size:0.85rem;color:var(--text-secondary);margin:0.4rem 0 0.6rem;">{b.get("notes", "")}</div>
      <div style="display:flex;gap:8px;">
        <a href="/stereo?svideo={url_param}" style="flex:1;text-align:center;background:var(--accent);color:#fff;border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Sphere VR</a>
        <a href="/stereo?video={url_param}" style="flex:1;text-align:center;background:var(--card-bg);color:var(--accent);border:1px solid var(--divider);border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Flat VR</a>
        <a href="{url_param}" style="flex:1;text-align:center;background:var(--card-bg);color:var(--text-secondary);border:1px solid var(--divider);border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Direct link</a>
      </div>
    </div>'''

    cards = "".join(beauty_card(b) for b in BEAUTY_RENDERS) \
            or '<p class="empty">No beauty renders yet.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Beauty renders</title>
  {theme_css_js}
  <style>{_GALLERY_CSS}</style>
</head>
<body>
  <div class="container">
    <h1>Beauty renders</h1>
    <div class="subtitle">Finished pieces — served from Cloudflare R2</div>
    {cards}
    <div class="footer"><a href="/stereo">&#8592; Stereo Photography</a></div>
  </div>
</body>
</html>'''


def render_place_page(*, theme_css_js, place):
    """Stills for one location."""
    shots = [s for s in _list_shots() if s.get("slug") == place]

    def shot_card(s):
        slug = s.get("slug", "")
        pair_id = s.get("pair_id", "")
        title = s.get("title", slug)
        inliers = s.get("inliers", "?")
        ts = s.get("timestamp", "")
        time_str = ts[11:16] if ts else ""
        date_str = ts[:10] if ts else ""
        img_param = f"{slug}/{slug}.{pair_id}"
        return (f'<a href="/stereo?img={img_param}" class="shot-card">'
                f'<div class="shot-title">{title}</div>'
                f'<div class="shot-meta">'
                f'<span class="quality">{inliers} inliers</span>'
                f'<span class="timestamp">{date_str} {time_str}</span>'
                f'</div></a>')

    cards = "".join(shot_card(s) for s in shots) \
            or '<p class="empty">No shots in this location.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_place_label(place)}</title>
  {theme_css_js}
  <style>{_GALLERY_CSS}</style>
</head>
<body>
  <div class="container">
    <h1>{_place_label(place)}</h1>
    <div class="subtitle">{len(shots)} stereo pair{'s' if len(shots) != 1 else ''}</div>
    {cards}
    <div class="footer"><a href="/stereo">&#8592; Stereo Photography</a></div>
  </div>
</body>
</html>'''


def render_videos_page(*, theme_css_js, visibility):
    """Videos filtered by visibility ('visible' or 'invisible')."""
    want_visible = (visibility == "visible")
    videos = [v for v in STEREO_VIDEOS if v.get("visible", True) == want_visible]

    def video_card(v):
        return f'''
    <div class="shot-card">
      <div class="shot-title">{v["label"]}</div>
      <div class="shot-meta" style="margin-bottom:0.5rem;">
        <span class="quality">{v["note"]}</span>
        <span class="timestamp">SBS MP4</span>
      </div>
      <div style="display:flex;gap:8px;">
        <a href="/stereo?svideo={v["file"]}" style="flex:1;text-align:center;background:var(--accent);color:#fff;border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Sphere VR</a>
        <a href="/stereo?video={v["file"]}" style="flex:1;text-align:center;background:var(--card-bg);color:var(--accent);border:1px solid var(--divider);border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Flat VR</a>
      </div>
    </div>'''

    cards = "".join(video_card(v) for v in videos) \
            or '<p class="empty">No videos in this section.</p>'

    title = "Visible videos" if want_visible else "Invisible videos"
    sub   = "Tap to open in WebXR VR viewer" if want_visible \
            else "Known not to display correctly — under investigation"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  {theme_css_js}
  <style>{_GALLERY_CSS}</style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="subtitle">{sub}</div>
    {cards}
    <div class="footer"><a href="/stereo">&#8592; Stereo Photography</a></div>
  </div>
</body>
</html>'''


# Back-compat shim: the existing import in mywebsite.py still references this name.
def render_gallery_page(*, theme_css_js):
    return render_index_page(theme_css_js=theme_css_js)


def get_neighbours(img_param):
    """Return {prev, next, current} for an img_param, in gallery sort order."""
    try:
        shots = _list_shots()
        params = [f"{s.get('slug','')}/{s.get('slug','')}.{s.get('pair_id','')}" for s in shots]
        if img_param in params:
            i = params.index(img_param)
            return {
                "prev": params[i - 1] if i > 0 else "",
                "next": params[i + 1] if i < len(params) - 1 else "",
                "current": img_param,
            }
    except Exception:
        pass
    return {"prev": "", "next": "", "current": img_param}


def render_viewer_page(*, theme_css_js, img_param):
    """img_param is e.g. 'barbican/barbican.12'"""
    jps_url = S3_BASE + img_param + ".jps"

    # Fetch eye_order from metadata so viewer defaults to correct orientation
    eye_order = "A"
    try:
        s3 = boto3.client("s3", region_name="eu-west-1")
        resp = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{img_param}.json")
        meta = json.loads(resp["Body"].read())
        eye_order = meta.get("eye_order", "A")
    except Exception:
        pass

    swapped_js = "true" if eye_order == "B" else "false"

    # Find previous and next shots in gallery order (same sort as gallery_page)
    prev_param = next_param = ""
    try:
        shots = _list_shots()
        params = [f"{s.get('slug','')}/{s.get('slug','')}.{s.get('pair_id','')}" for s in shots]
        if img_param in params:
            i = params.index(img_param)
            if i > 0:
                prev_param = params[i - 1]
            if i < len(params) - 1:
                next_param = params[i + 1]
    except Exception:
        pass

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stereo Viewer</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font); }}
    #ui {{
      padding: 20px; display: flex; flex-direction: column;
      align-items: center; gap: 16px;
    }}
    h1 {{ font-size: 1.2rem; color: var(--text); }}
    #preview {{ width: 100%; max-width: 600px; border-radius: 12px; display: none; }}
    #controls {{ display: none; flex-direction: column; gap: 12px; width: 100%; max-width: 600px; }}
    .control-row {{
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); border-radius: 12px; padding: 12px 16px;
    }}
    .control-row label {{ color: var(--text-secondary); font-size: 0.9rem; }}
    .control-row input[type=range] {{ width: 55%; accent-color: var(--accent); }}
    .control-row span {{ color: var(--text); font-size: 0.9rem; min-width: 40px; text-align: right; }}
    .btn-row {{ display: flex; gap: 12px; width: 100%; max-width: 600px; }}
    button {{
      background: var(--accent); color: #fff; border: none;
      border-radius: 12px; padding: 14px 0; font-size: 1rem;
      cursor: pointer; flex: 1;
    }}
    button:disabled {{ background: var(--divider); color: var(--text-secondary); cursor: default; }}
    button.secondary {{ background: var(--card-bg); color: var(--accent); border: 1px solid var(--divider); }}
    #status {{ color: var(--text-secondary); font-size: 0.85rem; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 1rem 0; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="ui">
    <h1>Stereo Viewer</h1>
    <img id="preview" alt="Preview">
    <div id="controls">
      <div class="control-row">
        <label>Convergence</label>
        <input type="range" id="convergence" min="-30" max="30" value="0" step="0.1">
        <span id="convergence-val">0.0°</span>
      </div>
      <div class="control-row">
        <label>Eye separation</label>
        <input type="range" id="separation" min="0.3" max="1.0" value="0.5" step="0.01">
        <span id="separation-val">0.50</span>
      </div>
    </div>
    <div class="btn-row">
      <button id="vr-btn" disabled>Enter VR</button>
      <button id="swap-btn" class="secondary" disabled>Order {eye_order}</button>
    </div>
    <div class="btn-row">
      <button id="prev-btn" class="secondary" {('disabled' if not prev_param else '')}>&#8592; Prev</button>
      <button id="next-btn" class="secondary" {('disabled' if not next_param else '')}>Next &#8594;</button>
    </div>
    <div id="status">Loading...</div>
    <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  </div>
  <canvas id="xr-canvas"></canvas>
  <script>
    const JPS_URL = '{jps_url}';

    const preview = document.getElementById('preview');
    const controls = document.getElementById('controls');
    const vrBtn = document.getElementById('vr-btn');
    const swapBtn = document.getElementById('swap-btn');
    const status = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    const convergenceSlider = document.getElementById('convergence');
    const separationSlider = document.getElementById('separation');
    const convergenceVal = document.getElementById('convergence-val');
    const separationVal = document.getElementById('separation-val');

    let swapped = {swapped_js};
    let zoom = 0.83;  // start 20% more zoomed in (uScale<1 = narrower FOV)
    let eyeShiftX = 0;  // normalized: per-eye X offset within its half (signed)
    let eyeShiftY = 0;  // normalized: per-eye Y offset (signed, mirrored between eyes)
    let xrSession = null;
    let gl = null;
    let prog = null;
    let tex = null;
    let toastTimer = null;
    function showToast(msg) {{
      status.textContent = msg;
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {{ status.textContent = ''; }}, 2000);
    }}
    function flipSwap() {{
      swapped = !swapped;
      swapBtn.textContent = swapped ? 'Order B' : 'Order A';
      showToast(swapped ? 'swapped' : 'not swapped');
    }}

    preview.crossOrigin = 'anonymous';
    preview.src = JPS_URL;
    preview.onload = () => {{
      preview.style.display = 'block';
      controls.style.display = 'flex';
      vrBtn.disabled = false;
      swapBtn.disabled = false;
      status.textContent = 'Ready';
    }};
    preview.onerror = () => {{ status.textContent = 'Failed to load image'; }};

    convergenceSlider.addEventListener('input', () => {{
      convergenceVal.textContent = parseFloat(convergenceSlider.value).toFixed(1) + '°';
    }});
    separationSlider.addEventListener('input', () => {{
      separationVal.textContent = parseFloat(separationSlider.value).toFixed(2);
    }});

    swapBtn.addEventListener('click', flipSwap);

    // Prev/next navigation — keeps the WebXR session alive by swapping the texture in-place.
    // Falls back to URL navigation when not in VR.
    let neighbours = {{ prev: '{prev_param}', next: '{next_param}', current: {json.dumps(img_param)} }};

    async function loadNeighbours(forParam) {{
      // Refresh prev/next pointers from a small JSON endpoint after switching image
      try {{
        const r = await fetch('/stereo-nav?img=' + encodeURIComponent(forParam));
        if (r.ok) neighbours = await r.json();
      }} catch(e) {{}}
    }}

    async function swapImage(target) {{
      if (!target) return;
      const newUrl = 'https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/' + target + '.jps';
      const newImg = new Image();
      newImg.crossOrigin = 'anonymous';
      newImg.src = newUrl;
      await new Promise((res, rej) => {{ newImg.onload = res; newImg.onerror = rej; }});

      // Update preview <img> for the 2D view
      preview.src = newUrl;

      // Reset per-image overrides
      eyeShiftX = 0;
      eyeShiftY = 0;

      // If in VR, swap the GL texture in-place
      if (xrSession && gl && tex) {{
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, newImg);
      }}
      // Update URL bar without navigating, so reloads restore current image
      history.replaceState(null, '', '/stereo?img=' + encodeURIComponent(target));
      neighbours.current = target;
      loadNeighbours(target);
    }}

    function go(target) {{ swapImage(target); }}

    document.getElementById('prev-btn').addEventListener('click', () => go(neighbours.prev));
    document.getElementById('next-btn').addEventListener('click', () => go(neighbours.next));
    document.addEventListener('keydown', e => {{
      if (e.key === 'ArrowLeft' || e.key === 'PageUp')   {{ e.preventDefault(); go(neighbours.prev); }}
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{ e.preventDefault(); go(neighbours.next); }}
    }});

    vrBtn.addEventListener('click', async () => {{
      if (xrSession) {{ await xrSession.end(); return; }}
      if (!navigator.xr) {{ status.textContent = 'WebXR not available'; return; }}
      const supported = await navigator.xr.isSessionSupported('immersive-vr');
      if (!supported) {{ status.textContent = 'Immersive VR not supported'; return; }}
      try {{
        xrSession = await navigator.xr.requestSession('immersive-vr', {{
          requiredFeatures: ['local']
        }});
        await startXR(xrSession);
      }} catch (e) {{
        status.textContent = 'VR error: ' + e.message;
      }}
    }});

    async function startXR(session) {{
      vrBtn.textContent = 'Exit VR';
      canvas.style.display = 'block';
      gl = canvas.getContext('webgl2', {{ xrCompatible: true }});
      await gl.makeXRCompatible();
      const refSpace = await session.requestReferenceSpace('local');
      const layer = new XRWebGLLayer(session, gl);
      session.updateRenderState({{ baseLayer: layer }});

      const img = preview;
      if (!img.complete) await new Promise(r => img.onload = r);

      tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

      const sphere = buildSphereRenderer(gl);

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};

      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);

        for (const src of session.inputSources) {{
          const gp = src.gamepad;
          if (!gp) continue;
          const id = src.handedness;
          if (!wasPressed[id]) wasPressed[id] = {{}};

          // A/X button (index 4) → swap eyes
          const aBtn = gp.buttons[4];
          if (aBtn?.pressed && !wasPressed[id][4]) {{
            flipSwap();
          }}
          wasPressed[id][4] = aBtn?.pressed;

          // Right trigger (button 0) → next image; Left trigger → prev
          const trig = gp.buttons[0];
          if (trig?.pressed && !wasPressed[id][0]) {{
            if (src.handedness === 'right') go(NEXT);
            else if (src.handedness === 'left') go(PREV);
          }}
          wasPressed[id][0] = trig?.pressed;

          // Right thumbstick X (axes[2]) → convergence; Y (axes[3]) → zoom
          if (src.handedness === 'right') {{
            const stickX = gp.axes[2] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              const val = Math.max(-30, Math.min(30,
                parseFloat(convergenceSlider.value) + stickX * 0.3));
              convergenceSlider.value = val;
              convergenceVal.textContent = val.toFixed(1) + '°';
            }}
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickY) > 0.15) {{
              zoom = Math.max(0.5, Math.min(3.0, zoom + stickY * 0.02));
            }}
          }}

          // Left thumbstick X/Y → pan (per-eye texture offset, opposite directions)
          if (src.handedness === 'left') {{
            const stickX = gp.axes[2] ?? 0;
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              eyeShiftX = Math.max(-0.25, Math.min(0.25, eyeShiftX + stickX * 0.003));
            }}
            if (Math.abs(stickY) > 0.15) {{
              eyeShiftY = Math.max(-0.25, Math.min(0.25, eyeShiftY + stickY * 0.003));
            }}
          }}
        }}

        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const yawDeg = parseFloat(convergenceSlider.value);
        const separation = parseFloat(separationSlider.value);
        for (const view of pose.views) {{
          const vp = layer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          const uOffset = eyeIsLeft ? 0.0 : 0.5;
          renderEyeSphere(gl, sphere, tex, uOffset, separation,
            view.projectionMatrix, view.transform.inverse.matrix, yawDeg, eyeIsLeft, zoom,
            img.naturalWidth, img.naturalHeight, eyeShiftX, eyeShiftY);
        }}
      }});
    }}

    // Build inside-out sphere mesh: stacks×slices quads, normals pointing inward.
    // Returns {{ prog, vao, indexCount, uProj, uView, uYaw, uOffsetX, uSeparation, uTex }}
    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS; // 0 (top) → π (bottom)
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(
            Math.sin(phi) * Math.cos(theta),  // x
            Math.cos(phi),                     // y
            Math.sin(phi) * Math.sin(theta)    // z
          );
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s * (SLICES + 1) + sl;
          const b = a + SLICES + 1;
          indices.push(a, b, a+1, b, b+1, a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; in vec2 aUV;
        uniform mat4 uProj, uView, uYawMat;
        out vec3 vDir;
        void main() {{
          // Pass world-space direction to fragment shader for angular mapping
          vDir = (uYawMat * vec4(aPos, 0.0)).xyz;
          vec4 worldPos = uYawMat * vec4(aPos * 100.0, 1.0);
          gl_Position = uProj * uView * worldPos;
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir;
        uniform sampler2D uTex;
        uniform float uOffsetX;    // 0.0=left eye half, 0.5=right eye half of SBS
        uniform float uHalfFovH;   // horizontal half-FOV of photo in radians
        uniform float uAspect;     // photo aspect ratio (width/height of one eye)
        uniform float uScale;      // zoom: >1 = wider FOV (zoom out)
        uniform float uShiftU;     // signed UV shift in x for this eye
        uniform float uShiftV;     // signed UV shift in y for this eye
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float azimuth   = atan(d.x, -d.z);
          float elevation = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float vFov = hFov / uAspect;
          float u01 = azimuth   / (2.0 * hFov) + 0.5 + uShiftU;
          float v01 = elevation / (2.0 * vFov) + 0.5 + uShiftV;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
            return;
          }}
          float u = uOffsetX + u01 * 0.5;
          fragColor = texture(uTex, vec2(u, 1.0 - v01));
        }}`;

      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const prog = gl.createProgram();
      gl.attachShader(prog, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(prog, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(prog, 'uProj'),
        uView:     gl.getUniformLocation(prog, 'uView'),
        uYawMat:   gl.getUniformLocation(prog, 'uYawMat'),
        uTex:      gl.getUniformLocation(prog, 'uTex'),
        uOffsetX:  gl.getUniformLocation(prog, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(prog, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(prog, 'uAspect'),
        uScale:    gl.getUniformLocation(prog, 'uScale'),
        uShiftU:   gl.getUniformLocation(prog, 'uShiftU'),
        uShiftV:   gl.getUniformLocation(prog, 'uShiftV'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, separation, projMat, viewMat, yawDeg, eyeIsLeft, zoom, imgW, imgH, shiftU, shiftV) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);

      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);

      // Toe-in convergence: rotate sphere by yawDeg per eye
      const dir = eyeIsLeft ? 1.0 : -1.0;
      const rad = yawDeg * Math.PI / 180.0 * dir;
      const c = Math.cos(rad), s = Math.sin(rad);
      const yaw = new Float32Array([
         c, 0, s, 0,
         0, 1, 0, 0,
        -s, 0, c, 0,
         0, 0, 0, 1
      ]);
      gl.uniformMatrix4fv(sphere.uYawMat, false, yaw);

      // Phone horizontal FOV ≈ 65°; each SBS eye is half the full width
      const halfFovH = (65.0 / 2.0) * Math.PI / 180.0;
      // Aspect ratio of one eye (half of SBS width : full height)
      const aspect = (imgW / 2) / imgH;

      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, halfFovH);
      gl.uniform1f(sphere.uAspect, aspect);
      gl.uniform1f(sphere.uScale, zoom);
      // Per-eye opposite shifts so eyes converge on the panned region
      gl.uniform1f(sphere.uShiftU, shiftU * (eyeIsLeft ? 1.0 : -1.0));
      gl.uniform1f(sphere.uShiftV, shiftV);

      // Disable depth test — sphere is the only object; back-face culling must be off
      // so the inside of the sphere is visible.
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''



def render_video_sphere_page(*, theme_css_js, video_file):
    """Player 3 — sphere renderer (same as stills player) with per-frame video texture."""
    # video_file may be a bare filename (legacy S3 entries) or a full https URL
    # (beauty renders on R2). Detect and route accordingly.
    if video_file.startswith(("http://", "https://")):
        video_url = video_file
        label = next((b["title"] for b in BEAUTY_RENDERS if b["url"] == video_file), video_file)
    else:
        video_url = S3_VIDEO_BASE + video_file
        label = next((v["label"] for v in STEREO_VIDEOS if v["file"] == video_file), video_file)

    info_html = _beauty_info_html(video_url)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{label}</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font); }}
    #ui {{ padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 16px; }}
    h1 {{ font-size: 1.2rem; color: var(--text); }}
    #preview {{ width: 100%; max-width: 600px; border-radius: 12px; }}
    #controls {{ display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 600px; }}
    .control-row {{
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); border-radius: 12px; padding: 12px 16px;
    }}
    .control-row label {{ color: var(--text-secondary); font-size: 0.9rem; }}
    .control-row input[type=range] {{ width: 55%; accent-color: var(--accent); }}
    .control-row span {{ color: var(--text); font-size: 0.9rem; min-width: 40px; text-align: right; }}
    .btn-row {{ display: flex; gap: 12px; width: 100%; max-width: 600px; }}
    button {{
      background: var(--accent); color: #fff; border: none;
      border-radius: 12px; padding: 14px 0; font-size: 1rem;
      cursor: pointer; flex: 1;
    }}
    button.secondary {{ background: var(--card-bg); color: var(--accent); border: 1px solid var(--divider); }}
    #status {{ color: var(--text-secondary); font-size: 0.85rem; min-height: 1.2em; }}
    .render-info {{
      display: flex; flex-wrap: wrap; gap: 4px 12px;
      justify-content: center; max-width: 600px;
      color: var(--text-secondary); font-size: 0.75rem;
      font-family: monospace;
    }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 1rem 0; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="ui">
    <h1>{label}</h1>
    {info_html}
    <video id="preview" src="{video_url}" controls playsinline loop crossorigin="anonymous"></video>
    <div id="controls">
      <div class="control-row">
        <label>Convergence</label>
        <input type="range" id="convergence" min="-30" max="30" value="0" step="0.1">
        <span id="convergence-val">0.0°</span>
      </div>
    </div>
    <div class="btn-row">
      <button id="vr-btn">Enter VR</button>
      <button id="swap-btn" class="secondary">Order A</button>
    </div>
    <div id="status"></div>
    <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  </div>
  <canvas id="xr-canvas"></canvas>
  <script>
    const vid = document.getElementById('preview');
    const vrBtn = document.getElementById('vr-btn');
    const swapBtn = document.getElementById('swap-btn');
    const status = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    const convergenceSlider = document.getElementById('convergence');
    const convergenceVal = document.getElementById('convergence-val');

    let swapped = false;
    let zoom = 0.83;  // start 20% more zoomed in (uScale<1 = narrower FOV = zoomed in)
    let xrSession = null, gl = null;
    let toastTimer = null;
    function showToast(msg) {{
      status.textContent = msg;
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {{ status.textContent = ''; }}, 2000);
    }}
    function flipSwap() {{
      swapped = !swapped;
      swapBtn.textContent = swapped ? 'Order B' : 'Order A';
      showToast(swapped ? 'swapped' : 'not swapped');
    }}

    convergenceSlider.addEventListener('input', () => {{
      convergenceVal.textContent = parseFloat(convergenceSlider.value).toFixed(1) + '°';
    }});
    swapBtn.addEventListener('click', flipSwap);

    vrBtn.addEventListener('click', async () => {{
      if (xrSession) {{ await xrSession.end(); return; }}
      if (!navigator.xr) {{ status.textContent = 'WebXR not available'; return; }}
      const supported = await navigator.xr.isSessionSupported('immersive-vr');
      if (!supported) {{ status.textContent = 'Immersive VR not supported'; return; }}
      try {{
        xrSession = await navigator.xr.requestSession('immersive-vr', {{ requiredFeatures: ['local'] }});
        await startXR(xrSession);
      }} catch (e) {{ status.textContent = 'VR error: ' + e.message; }}
    }});

    async function startXR(session) {{
      vrBtn.textContent = 'Exit VR';
      canvas.style.display = 'block';
      gl = canvas.getContext('webgl2', {{ xrCompatible: true }});
      await gl.makeXRCompatible();
      const refSpace = await session.requestReferenceSpace('local');
      const layer = new XRWebGLLayer(session, gl);
      session.updateRenderState({{ baseLayer: layer }});

      const sphere = buildSphereRenderer(gl);

      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, vid.videoWidth || 1024, vid.videoHeight || 288, 0, gl.RGB, gl.UNSIGNED_BYTE, null);

      vid.play();

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};

      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);

        if (vid.readyState >= vid.HAVE_CURRENT_DATA) {{
          gl.bindTexture(gl.TEXTURE_2D, tex);
          gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGB, gl.UNSIGNED_BYTE, vid);
        }}

        for (const src of session.inputSources) {{
          const gp = src.gamepad; if (!gp) continue;
          const id = src.handedness;
          if (!wasPressed[id]) wasPressed[id] = {{}};

          const aBtn = gp.buttons[4];
          if (aBtn?.pressed && !wasPressed[id][4]) {{
            flipSwap();
          }}
          wasPressed[id][4] = aBtn?.pressed;

          if (src.handedness === 'right') {{
            const trig = gp.buttons[0];
            if (trig?.pressed && !wasPressed[id][0]) vid.paused ? vid.play() : vid.pause();
            wasPressed[id][0] = trig?.pressed;

            const stickX = gp.axes[2] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              const val = Math.max(-30, Math.min(30, parseFloat(convergenceSlider.value) + stickX * 0.3));
              convergenceSlider.value = val;
              convergenceVal.textContent = val.toFixed(1) + '°';
            }}
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickY) > 0.15) zoom = Math.max(0.5, Math.min(3.0, zoom + stickY * 0.02));
          }}
          if (src.handedness === 'left') {{
            const trig = gp.buttons[0];
            if (trig?.pressed && !wasPressed[id][0]) session.end();
            wasPressed[id][0] = trig?.pressed;
          }}
        }}

        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const yawDeg = parseFloat(convergenceSlider.value);
        const vw = vid.videoWidth || 1024, vh = vid.videoHeight || 288;
        for (const view of pose.views) {{
          const vp = layer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          renderEyeSphere(gl, sphere, tex, eyeIsLeft ? 0.0 : 0.5, 1.0,
            view.projectionMatrix, view.transform.inverse.matrix, yawDeg, eyeIsLeft, zoom, vw, vh);
        }}
      }});
    }}

    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS;
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(Math.sin(phi)*Math.cos(theta), Math.cos(phi), Math.sin(phi)*Math.sin(theta));
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s*(SLICES+1)+sl, b = a+SLICES+1;
          indices.push(a, b, a+1, b, b+1, a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; uniform mat4 uProj, uView, uYawMat; out vec3 vDir;
        void main() {{
          vDir = (uYawMat * vec4(aPos, 0.0)).xyz;
          gl_Position = uProj * uView * uYawMat * vec4(aPos * 100.0, 1.0);
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir; uniform sampler2D uTex;
        uniform float uOffsetX, uHalfFovH, uAspect, uScale;
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float az = atan(d.x, -d.z);
          float el = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float vFov = hFov / uAspect;
          float u01 = az / (2.0 * hFov) + 0.5;
          float v01 = el / (2.0 * vFov) + 0.5;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0); return;
          }}
          fragColor = texture(uTex, vec2(uOffsetX + u01 * 0.5, 1.0 - v01));
        }}`;
      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const p = gl.createProgram();
      gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog: p, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(p, 'uProj'),
        uView:     gl.getUniformLocation(p, 'uView'),
        uYawMat:   gl.getUniformLocation(p, 'uYawMat'),
        uTex:      gl.getUniformLocation(p, 'uTex'),
        uOffsetX:  gl.getUniformLocation(p, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(p, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(p, 'uAspect'),
        uScale:    gl.getUniformLocation(p, 'uScale'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, separation, projMat, viewMat, yawDeg, eyeIsLeft, zoom, vidW, vidH) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);
      const dir = eyeIsLeft ? 1.0 : -1.0;
      const rad = yawDeg * Math.PI / 180.0 * dir;
      const c = Math.cos(rad), s = Math.sin(rad);
      gl.uniformMatrix4fv(sphere.uYawMat, false, new Float32Array([
        c,0,s,0, 0,1,0,0, -s,0,c,0, 0,0,0,1
      ]));
      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, (65.0 / 2.0) * Math.PI / 180.0);
      gl.uniform1f(sphere.uAspect, (vidW / 2) / vidH);
      gl.uniform1f(sphere.uScale, zoom);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''


def render_video_viewer_page(*, theme_css_js, video_file):
    """SBS video viewer — slate visible on load, fullscreen + WebXR options."""
    import random as _r
    # video_file may be a bare filename (legacy S3) or a full https URL (R2 beauty render)
    if video_file.startswith(("http://", "https://")):
        video_url = video_file
        label = next((b["title"] for b in BEAUTY_RENDERS if b["url"] == video_file), video_file)
    else:
        video_url = S3_VIDEO_BASE + video_file
        label = next((v["label"] for v in STEREO_VIDEOS if v["file"] == video_file), video_file)
    # Build pet — random per cold-start of the Lambda. Stable within a Lambda
    # container (free CloudFront cache hits), changes after deploy/cold-start.
    if not hasattr(render_video_viewer_page, "_pet"):
        pets = ["badger","otter","heron","fox","squirrel","wren","hare","stoat",
                "puffin","mole","newt","kestrel","owl","crow","robin","sparrow",
                "weasel","ferret","dormouse","raven","magpie","starling","linnet"]
        render_video_viewer_page._pet = _r.choice(pets)
    page_pet = render_video_viewer_page._pet
    info_html = _beauty_info_html(video_url)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{label}</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #000; color: var(--text); font-family: var(--font); display: flex; flex-direction: column; align-items: center; min-height: 100vh; }}
    #video-wrap {{ width: 100%; max-width: 900px; padding: 1rem; }}
    video {{ width: 100%; border-radius: 8px; display: block; }}
    .hint {{ text-align: center; color: #8E8E93; font-size: 0.85rem; margin: 0.75rem 1rem; line-height: 1.6; max-width: 600px; }}
    .hint strong {{ color: #E0E0E0; }}
    .btn-row {{ display: flex; gap: 10px; justify-content: center; margin: 0.75rem; flex-wrap: wrap; }}
    button {{
      background: #007AFF; color: #fff; border: none;
      border-radius: 12px; padding: 12px 24px; font-size: 0.95rem; cursor: pointer;
    }}
    button.secondary {{ background: #161616; color: #007AFF; border: 1px solid #2C2C2E; }}
    button:disabled {{ background: #2C2C2E; color: #8E8E93; cursor: default; }}
    .footer {{ text-align: center; color: #8E8E93; font-size: 0.75rem; margin: 1rem; }}
    .footer a {{ color: #007AFF; text-decoration: none; }}
    #status {{
      min-height: 1.5em;
      padding: 8px 16px;
      margin: 0.5rem auto;
      max-width: 600px;
      background: #161616;
      color: #FF9500;
      font-family: monospace;
      font-size: 0.85rem;
      border-radius: 8px;
      text-align: center;
      border: 1px solid #2C2C2E;
    }}
    .render-info {{
      display: flex; flex-wrap: wrap; gap: 4px 12px;
      justify-content: center; max-width: 600px;
      color: #8E8E93; font-size: 0.75rem;
      font-family: monospace;
      margin: 0.5rem 1rem;
    }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; }}
  </style>
</head>
<body>
  <div id="video-wrap">
    <!-- preload=auto loads enough to show the slate frame; no autoplay so slate stays visible -->
    <video id="vid" src="{video_url}" controls playsinline loop preload="auto"></video>
  </div>
  {info_html}
  <div class="hint">
    <strong>Quest: </strong>tap <strong>Play</strong> then <strong>Fullscreen</strong> — press <strong>O</strong> to push to background for stereo.<br>
    Or tap <strong>Enter VR</strong> for WebXR mode.
  </div>
  <div class="btn-row">
    <button id="fs-btn">Fullscreen</button>
    <button id="vr-btn">Enter VR</button>
    <button class="secondary" onclick="history.back()">&#8592; Back</button>
  </div>
  <div id="status"></div>
  <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  <canvas id="xr-canvas"></canvas>

  <!-- WebXR Layers polyfill (W3C reference sample loads this too) -->
  <script src="https://immersive-web.github.io/webxr-layers-polyfill/build/webxr-layers-polyfill.js"></script>
  <script>
    try {{ new WebXRLayersPolyfill(); }} catch(e) {{}}
    const vid = document.getElementById('vid');
    const vrBtn = document.getElementById('vr-btn');
    const statusEl = document.getElementById('status');
    let xrSession = null, xrVideo = null;

    // Match W3C reference: gate Enter VR until video has buffered enough.
    // The 25s clip has moov-at-end and high bitrate; entering VR before
    // canplaythrough means the compositor renders an empty texture (purple void).
    vrBtn.disabled = true;
    const origLabel = vrBtn.textContent;
    vrBtn.textContent = 'Loading video…';
    vid.addEventListener('canplaythrough', () => {{
      vrBtn.disabled = false;
      vrBtn.textContent = origLabel;
    }}, {{ once: true }});

    // Show the slate frame on load
    vid.addEventListener('loadedmetadata', () => {{ vid.currentTime = 0; }});
    vid.addEventListener('canplay', () => {{ if (vid.paused) vid.currentTime = 0; }});

    document.getElementById('fs-btn').addEventListener('click', () => {{
      vid.muted = false; vid.play();
      if (vid.webkitEnterFullscreen)       vid.webkitEnterFullscreen();
      else if (vid.requestFullscreen)      vid.requestFullscreen();
      else {{
        const el = document.getElementById('video-wrap');
        if (el.requestFullscreen)            el.requestFullscreen();
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
      }}
    }});

    function makeXrVideo() {{
      const v = document.createElement('video');
      v.crossOrigin = 'anonymous';
      v.preload = 'auto';
      v.loop = true;
      v.muted = true;
      v.playsInline = true;
      v.setAttribute('playsinline', '');
      v.setAttribute('webkit-playsinline', '');
      v.src = vid.src;
      return v;
    }}

    vrBtn.addEventListener('click', () => {{
      if (xrSession) {{ xrSession.end(); return; }}
      if (!navigator.xr) {{ statusEl.textContent = 'WebXR not available'; return; }}

      // Match W3C media-layer-sample order: kick session and play() inside
      // the same gesture, neither awaited.
      xrVideo = makeXrVideo();
      navigator.xr.requestSession('immersive-vr', {{ requiredFeatures: ['layers'] }})
        .then((session) => {{ xrSession = session; onSessionStarted(session); }})
        .catch((e) => {{ statusEl.textContent = 'Session failed: ' + e.message; }});
      xrVideo.play().catch(() => {{}});
    }});

    function onSessionStarted(session) {{
      vrBtn.textContent = 'Exit VR';
      session.addEventListener('end', onSessionEnded);
      const mediaFactory = new XRMediaBinding(session);

      // Wait for xrVideo to have decoded a frame before creating the layer —
      // otherwise the compositor renders an empty texture.
      const ready = xrVideo.readyState >= 2  // HAVE_CURRENT_DATA
        ? Promise.resolve()
        : new Promise((res) => xrVideo.addEventListener('loadeddata', res, {{ once: true }}));

      Promise.all([session.requestReferenceSpace('local'), ready]).then(([refSpace]) => {{
        let fovDeg = 90;
        const FOV_MIN = 60, FOV_MAX = 120;
        const eyeW = (xrVideo.videoWidth || 1280) / 2;
        const eyeH = xrVideo.videoHeight || 720;
        const aspect = eyeW / eyeH;
        const vAngleRad = (hDeg) => (hDeg / aspect) * Math.PI / 180 / 2;

        const layer = mediaFactory.createEquirectLayer(xrVideo, {{
          space: refSpace,
          centralHorizontalAngle: fovDeg * Math.PI / 180,
          upperVerticalAngle:  vAngleRad(fovDeg),
          lowerVerticalAngle: -vAngleRad(fovDeg),
          layout: 'stereo-left-right',
        }});
        session.updateRenderState({{ layers: [layer] }});

        // Single rAF loop drives the session and handles all controller input.
        // (Without a rAF loop, media layers don't display at all.)
        const wasPressed = {{}};
        function onXRFrame() {{
          session.requestAnimationFrame(onXRFrame);
          for (const src of session.inputSources) {{
            const gp = src.gamepad; if (!gp) continue;
            const id = src.handedness;
            if (!wasPressed[id]) wasPressed[id] = {{}};

            if (id === 'right') {{
              const stickY = gp.axes[3] ?? 0;
              if (Math.abs(stickY) > 0.15) {{
                fovDeg = Math.max(FOV_MIN, Math.min(FOV_MAX, fovDeg + stickY * 0.4));
                layer.centralHorizontalAngle = fovDeg * Math.PI / 180;
                layer.upperVerticalAngle =  vAngleRad(fovDeg);
                layer.lowerVerticalAngle = -vAngleRad(fovDeg);
              }}
              const trig = gp.buttons[0];
              if (trig?.pressed && !wasPressed[id][0]) {{
                xrVideo.paused ? xrVideo.play() : xrVideo.pause();
              }}
              wasPressed[id][0] = trig?.pressed;
            }}
            if (id === 'left') {{
              const trig = gp.buttons[0];
              if (trig?.pressed && !wasPressed[id][0]) session.end();
              wasPressed[id][0] = trig?.pressed;
            }}
          }}
        }}
        session.requestAnimationFrame(onXRFrame);
      }});
    }}

    function onSessionEnded() {{
      vrBtn.textContent = 'Enter VR';
      if (xrVideo) {{ xrVideo.pause(); xrVideo.src = ''; xrVideo = null; }}
      xrSession = null;
      statusEl.textContent = '';
    }}

    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS;
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(Math.sin(phi)*Math.cos(theta), Math.cos(phi), Math.sin(phi)*Math.sin(theta));
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s*(SLICES+1)+sl, b = a+SLICES+1;
          indices.push(a,b,a+1,b,b+1,a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; uniform mat4 uProj, uView; out vec3 vDir;
        void main() {{
          vDir = aPos;
          gl_Position = uProj * uView * vec4(aPos * 100.0, 1.0);
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir; uniform sampler2D uTex;
        uniform float uOffsetX, uHalfFovH, uAspect, uScale;
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float az = atan(d.x, -d.z);
          float el = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float u01 = az / (2.0 * hFov) + 0.5;
          float v01 = el / (2.0 * hFov * uAspect) + 0.5;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0); return;
          }}
          fragColor = texture(uTex, vec2(uOffsetX + u01 * 0.5, 1.0 - v01));
        }}`;
      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const p = gl.createProgram();
      gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog: p, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(p, 'uProj'),
        uView:     gl.getUniformLocation(p, 'uView'),
        uTex:      gl.getUniformLocation(p, 'uTex'),
        uOffsetX:  gl.getUniformLocation(p, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(p, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(p, 'uAspect'),
        uScale:    gl.getUniformLocation(p, 'uScale'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, projMat, viewMat, zoom, vidW, vidH) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);
      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, (65.0 / 2.0) * Math.PI / 180.0);
      gl.uniform1f(sphere.uAspect, (vidW / 2) / vidH);
      gl.uniform1f(sphere.uScale, zoom);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''
