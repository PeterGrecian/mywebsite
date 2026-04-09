"""Shared camera page renderers for springcam and skycam."""


def render_camera_latest(camera_name, images, *, theme_css_js, gallery_path, fullres_path):
    """Render a camera latest-images page."""
    cards = ''
    for img in images:
        display_ts = img['timestamp']
        cards += f'''
                <div class="image-container">
                    <a href="{fullres_path}?key={img['key']}">
                        <img src="{img['url']}" alt="{camera_name} {display_ts}" loading="lazy">
                    </a>
                    <div class="timestamp">{display_ts}</div>
                </div>'''

    return f'''{theme_css_js}
            <title>{camera_name}</title>
            <style>
                body {{ font-family: var(--font); text-align: center; margin: 1rem; background: var(--bg); color: var(--text); }}
                h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
                .gallery-link {{ display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1.5rem; background: var(--card-bg); color: var(--accent); text-decoration: none; border-radius: 8px; border: 1px solid var(--divider); transition: opacity 0.2s; }}
                .gallery-link:hover {{ opacity: 0.8; }}
                .gallery {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; max-width: 1024px; margin: 0 auto; }}
                .image-container {{ flex: 1; min-width: 280px; max-width: 340px; }}
                .image-container img {{ width: 100%; height: auto; border-radius: 8px; }}
                .timestamp {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem; }}
                @media (max-width: 1024px) {{
                    .gallery {{ flex-direction: column; }}
                    .image-container {{ min-width: 100%; max-width: 100%; }}
                }}
            </style>
            <div style="text-align: center; margin-bottom: 1rem;">
                <a href="contents" style="color: var(--accent); text-decoration: none;">Home</a>
            </div>
            <h1>{camera_name}</h1>
            <a href="{gallery_path}" class="gallery-link">View Full Gallery</a>
            <div class="gallery">
            {cards}</div>'''


def render_camera_gallery(camera_name, all_images, *, latest_path, thumb_key_fn, get_presigned_url):
    """Render a camera thumbnail gallery page."""
    thumbs = ''
    for img in all_images:
        thumb = thumb_key_fn(img['key'])
        thumb_url = get_presigned_url(thumb)
        full_url = get_presigned_url(img['key'])
        ts = img['timestamp'][:16] if img['timestamp'] else ''
        thumbs += f'''
            <div>
                <a href="{full_url}" target="_blank">
                    <img class="thumb" src="{thumb_url}" alt="{ts}" loading="lazy">
                </a>
                <div class="ts">{ts}</div>
            </div>'''

    return f'''
        <title>{camera_name} Gallery</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 1rem; }}
            h1 {{ text-align: center; margin-bottom: 1rem; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }}
            .gallery {{ display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }}
            .thumb {{ width: 150px; height: 112px; object-fit: cover; border-radius: 4px; cursor: pointer; }}
            .thumb:hover {{ opacity: 0.8; }}
            .ts {{ font-size: 0.7rem; color: #888; text-align: center; margin-top: 2px; }}
        </style>
        <h1>{camera_name} Gallery</h1>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{latest_path}">Latest</a>
        </div>
        <div class="gallery">
        {thumbs}</div>'''


def render_camera_fullres(camera_name, image_url, ts, *, latest_path, gallery_path):
    """Render a camera full-resolution image page."""
    return f'''
            <title>{camera_name} - Full Resolution</title>
            <style>
                body {{ background: #000; margin: 0; display: flex; flex-direction: column; align-items: center; }}
                img {{ max-width: 100%; height: auto; }}
                .nav {{ color: #aaa; padding: 0.5rem; font-family: Arial, sans-serif; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }}
            </style>
            <div class="nav"><a href="../../contents">Home</a> | <a href="{latest_path}">Latest</a> | <a href="{gallery_path}">Gallery</a></div>
            <div class="nav">{ts}</div>
            <img src="{image_url}" alt="{ts}">
            '''
