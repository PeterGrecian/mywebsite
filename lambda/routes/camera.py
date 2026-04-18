"""Shared camera page renderers for springcam and skycam."""


def render_camera_latest(camera_name, images, *, theme_css_js, gallery_path, fullres_path, videos_path=None):
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

    videos_link = f'<a href="{videos_path}" class="gallery-link">Timelapse Videos</a>' if videos_path else ''

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
            {videos_link}
            <div class="gallery">
            {cards}</div>'''


def render_camera_gallery(camera_name, all_images, *, latest_path, thumb_key_fn, get_presigned_url, fullres_path=None):
    """Render a camera thumbnail gallery page."""
    import boto3
    from concurrent.futures import ThreadPoolExecutor

    s3 = boto3.client("s3", region_name="eu-west-1")

    def _presign(key):
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': 'gardencam-berrylands-eu-west-1', 'Key': key},
            ExpiresIn=3600,
        )

    thumb_keys = [thumb_key_fn(img['key']) for img in all_images]
    with ThreadPoolExecutor(max_workers=20) as ex:
        thumb_urls = list(ex.map(_presign, thumb_keys))

    thumbs = ''
    for img, thumb_url in zip(all_images, thumb_urls):
        if fullres_path:
            full_url = f"{fullres_path}?key={img['key']}"
        else:
            full_url = _presign(img['key'])
        ts = img['timestamp'][:16] if img['timestamp'] else ''
        thumbs += f'''
            <div>
                <a href="{full_url}">
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


def render_camera_day_index(camera_name, days, *, gallery_path, latest_path, videos_path=None):
    """Render a day-based gallery index page."""
    day_links = ''
    for day in days:
        day_links += f'''
            <a href="{gallery_path}?day={day['date']}" class="day-link">{day['label']}</a>'''

    videos_nav = f' | <a href="{videos_path}">Videos</a>' if videos_path else ''

    return f'''
        <title>{camera_name} Gallery</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 2rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
            .nav a:hover {{ text-decoration: underline; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .day-list {{ max-width: 800px; margin: 0 auto; }}
            .day-link {{ display: block; padding: 1rem 1.5rem; margin-bottom: 0.75rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1.1rem; transition: background 0.3s; }}
            .day-link:hover {{ background: #3a3a3a; }}
        </style>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{latest_path}">Latest</a>{videos_nav}
        </div>
        <h1>{camera_name} Gallery</h1>
        <div class="day-list">{day_links}</div>'''


def render_camera_day_gallery(camera_name, day_str, images, *, page, total_pages, total_images,
                              thumb_key_fn, gallery_path, latest_path, fullres_path):
    """Render a paginated day gallery page with thumbnails."""
    import boto3

    s3 = boto3.client("s3", region_name="eu-west-1")

    def _presign(key):
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': 'gardencam-berrylands-eu-west-1', 'Key': key},
            ExpiresIn=3600,
        )

    from concurrent.futures import ThreadPoolExecutor
    thumb_keys = [thumb_key_fn(img['key']) for img in images]
    with ThreadPoolExecutor(max_workers=20) as ex:
        thumb_urls = list(ex.map(_presign, thumb_keys))

    thumbs = ''
    for img, thumb_url in zip(images, thumb_urls):
        ts = img['timestamp'][:16] if img.get('timestamp') else ''
        full_url = f"{fullres_path}?key={img['key']}"
        thumbs += f'''
            <div>
                <a href="{full_url}">
                    <img class="thumb" src="{thumb_url}" alt="{ts}" loading="lazy">
                </a>
                <div class="ts">{ts}</div>
            </div>'''

    # Pagination links
    pagination = '<div class="pagination">'
    if page > 1:
        pagination += f'<a href="{gallery_path}?day={day_str}&page={page - 1}">&larr; Prev</a> '
    pagination += f'<span class="page-info">Page {page} of {total_pages} ({total_images} images)</span>'
    if page < total_pages:
        pagination += f' <a href="{gallery_path}?day={day_str}&page={page + 1}">Next &rarr;</a>'
    pagination += '</div>'

    return f'''
        <title>{camera_name} - {day_str}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 1rem; }}
            h1 {{ text-align: center; margin-bottom: 1rem; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }}
            .gallery {{ display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }}
            .thumb {{ width: 150px; height: 112px; object-fit: cover; border-radius: 4px; cursor: pointer; }}
            .thumb:hover {{ opacity: 0.8; }}
            .ts {{ font-size: 0.7rem; color: #888; text-align: center; margin-top: 2px; }}
            .pagination {{ text-align: center; margin: 1.5rem 0; }}
            .pagination a {{ color: #4a9eff; text-decoration: none; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .pagination a:hover {{ background: #3a3a3a; }}
            .page-info {{ color: #888; margin: 0 1rem; }}
        </style>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{gallery_path}">All Days</a> |
            <a href="{latest_path}">Latest</a>
        </div>
        <h1>{day_str}</h1>
        {pagination}
        <div class="gallery">{thumbs}</div>
        {pagination}'''


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


def render_camera_videos(camera_name, recent_videos, *, latest_path, gallery_path):
    """Render a timelapse videos page for a camera (generic, flat list)."""
    cards = ''
    for v in recent_videos:
        cards += f'''
            <a href="{v['url']}" class="video-card">
                <div class="video-thumbnail">
                    <div class="play-icon"></div>
                </div>
                <div class="video-meta">
                    <h3>{v['label']}</h3>
                    <p>{v['size_mb']:.1f} MB</p>
                </div>
            </a>'''

    if not recent_videos:
        cards = '<p style="color:#888; text-align:center;">No timelapse videos yet.</p>'

    return f'''
        <title>{camera_name} - Timelapse Videos</title>
        {_VIDEO_PAGE_STYLE}
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{latest_path}">Latest</a> |
            <a href="{gallery_path}">Gallery</a>
        </div>
        <h1>{camera_name} — Timelapse Videos</h1>
        <div class="video-grid">{cards}</div>'''


def _skycam_video_cards(videos):
    """Render video cards for a list of skycam videos."""
    if not videos:
        return '<p style="color:#888; text-align:center;">No videos for this period.</p>'
    cards = ''
    for v in videos:
        extra_class = ' video-card-daily' if v.get('is_daily') else ''
        cards += f'''
            <a href="{v['url']}" class="video-card{extra_class}">
                <div class="video-thumbnail">
                    <div class="play-icon"></div>
                </div>
                <div class="video-meta">
                    <h3>{v['label']}</h3>
                    <p>{v['size_mb']:.1f} MB</p>
                </div>
            </a>'''
    return f'<div class="video-grid">{cards}</div>'


def _skycam_nav():
    return '''
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="../skycam">Latest</a> |
            <a href="gallery">Gallery</a> |
            <a href="videos">Videos</a>
        </div>'''


def render_skycam_videos_index(today_str, today_videos, months_list):
    """Landing page: today's videos + links to browse by month."""
    from datetime import datetime

    month_links = ''
    for m in months_list:
        try:
            dt = datetime.strptime(m + '-01', '%Y-%m-%d')
            label = dt.strftime('%B %Y')
        except ValueError:
            label = m
        month_links += f'<a href="videos?month={m}" class="month-link">{label}</a>'

    if not month_links:
        month_links = '<p style="color:#888;">No archived months yet.</p>'

    return f'''
        <title>Sky Camera - Hourly Timelapses</title>
        {_VIDEO_PAGE_STYLE}
        {_skycam_nav()}
        <h1>Sky Camera — Hourly Timelapses</h1>
        <p style="color:#888; text-align:center; margin-bottom:1.5rem;">One video per daylight hour, ~360 frames at 24fps (~15s each)</p>
        <div class="content">
            <h2 class="section-heading">Today — {today_str}</h2>
            {_skycam_video_cards(today_videos)}
            <h2 class="section-heading" style="margin-top:2.5rem;">Browse by Month</h2>
            <div class="month-list">{month_links}</div>
        </div>'''


def render_skycam_videos_month(month_str, days_list):
    """Month view: list of days with video counts."""
    from datetime import datetime

    try:
        dt = datetime.strptime(month_str + '-01', '%Y-%m-%d')
        month_label = dt.strftime('%B %Y')
    except ValueError:
        month_label = month_str

    day_links = ''
    for day_str, count in days_list:
        try:
            dt = datetime.strptime(day_str, '%Y-%m-%d')
            label = dt.strftime('%A %d %B')
        except ValueError:
            label = day_str
        day_links += f'<a href="videos?day={day_str}" class="day-link">{label}<span class="count">{count} video{"s" if count != 1 else ""}</span></a>'

    if not day_links:
        day_links = '<p style="color:#888; text-align:center;">No videos recorded this month.</p>'

    return f'''
        <title>Sky Camera - {month_label}</title>
        {_VIDEO_PAGE_STYLE}
        {_skycam_nav()}
        <h1>{month_label}</h1>
        <div class="content">
            <div class="day-list">{day_links}</div>
        </div>'''


def render_skycam_videos_day(day_str, videos):
    """Day view: all hourly videos for a specific day."""
    from datetime import datetime

    try:
        dt = datetime.strptime(day_str, '%Y-%m-%d')
        day_label = dt.strftime('%A %d %B %Y')
    except ValueError:
        day_label = day_str

    return f'''
        <title>Sky Camera - {day_label}</title>
        {_VIDEO_PAGE_STYLE}
        {_skycam_nav()}
        <h1>{day_label}</h1>
        <p style="color:#888; text-align:center; margin-bottom:1.5rem;">{len(videos)} video{"s" if len(videos) != 1 else ""}</p>
        <div class="content">
            {_skycam_video_cards(videos)}
        </div>'''


_VIDEO_PAGE_STYLE = '''
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
            .nav { text-align: center; margin-bottom: 2rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 1rem; }
            .nav a:hover { text-decoration: underline; }
            h1 { text-align: center; margin-bottom: 0.5rem; }
            .content { max-width: 1400px; margin: 0 auto; }
            .section-heading { color: #4a9eff; margin: 2rem 0 1rem 0; padding-left: 0.5rem; font-size: 1.2rem; }
            .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
            .video-card { background: #2a2a2a; border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; display: block; transition: transform 0.2s; }
            .video-card:hover { transform: translateY(-4px); }
            .video-thumbnail { height: 100px; background: linear-gradient(135deg, #1e2a1e 0%, #1a1a1a 100%); display: flex; align-items: center; justify-content: center; }
            .play-icon { width: 40px; height: 40px; background: rgba(74,158,255,0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
            .play-icon::after { content: ''; width: 0; height: 0; border-style: solid; border-width: 8px 0 8px 14px; border-color: transparent transparent transparent #fff; margin-left: 2px; }
            .video-meta { padding: 0.5rem 0.75rem; }
            .video-meta h3 { margin: 0 0 0.25rem 0; color: #4a9eff; font-size: 0.85rem; }
            .video-meta p { margin: 0; color: #888; font-size: 0.75rem; }
            .month-list { display: flex; flex-wrap: wrap; gap: 0.75rem; }
            .month-link { display: block; padding: 0.75rem 1.5rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1rem; transition: background 0.3s; }
            .month-link:hover { background: #3a3a3a; }
            .day-list { display: flex; flex-direction: column; gap: 0.5rem; }
            .day-link { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.5rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1rem; transition: background 0.3s; }
            .day-link:hover { background: #3a3a3a; }
            .day-link .count { color: #888; font-size: 0.85rem; }
            .video-card-daily { grid-column: 1 / -1; max-width: 400px; border: 1px solid #4a9eff; }
            .video-card-daily .video-meta h3 { font-size: 1rem; }
        </style>'''
