"""Shared camera page renderers for springcam and skycam."""


def render_camera_latest(camera_name, images, *, theme_css_js, gallery_path, fullres_path, videos_path=None, starcam_path=None, advanced_videos_path=None):
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
    advanced_link = f'<a href="{advanced_videos_path}" class="gallery-link">⚙ Advanced player</a>' if advanced_videos_path else ''
    starcam_link = f'<a href="{starcam_path}" class="gallery-link">Starcam</a>' if starcam_path else ''

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
            {advanced_link}
            {starcam_link}
            <div class="gallery">
            {cards}</div>'''


_GALLERY_STYLE = '''
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
            .nav { text-align: center; margin-bottom: 1rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }
            .nav a:hover { text-decoration: underline; }
            .breadcrumb { text-align: center; margin-bottom: 1.5rem; font-size: 0.9rem; color: #888; }
            .breadcrumb a { color: #4a9eff; text-decoration: none; }
            .breadcrumb a:hover { text-decoration: underline; }
            .zoom-out { display: block; text-align: center; margin-bottom: 1.5rem; }
            .zoom-out a { display: inline-block; padding: 0.5rem 1.5rem; background: #2a2a2a; color: #4a9eff; text-decoration: none; border-radius: 8px; font-size: 1rem; transition: background 0.3s; }
            .zoom-out a:hover { background: #3a3a3a; }
            h1 { text-align: center; margin-bottom: 0.5rem; }
            .subtitle { text-align: center; color: #888; margin-bottom: 1.5rem; font-size: 0.9rem; }
            .gallery { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
            .thumb { width: 150px; height: 112px; object-fit: cover; border-radius: 4px; cursor: pointer; }
            .thumb:hover { opacity: 0.8; }
            .ts { font-size: 0.7rem; color: #888; text-align: center; margin-top: 2px; }
            .item-list { max-width: 800px; margin: 0 auto; }
            .item-link { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.5rem; margin-bottom: 0.5rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1rem; transition: background 0.3s; }
            .item-link:hover { background: #3a3a3a; }
            .item-link .count { color: #888; font-size: 0.85rem; }
            .day-section { margin-bottom: 2rem; }
            .day-heading { color: #4a9eff; margin: 1.5rem 0 0.75rem; font-size: 1.1rem; padding-left: 0.5rem; }
            .pagination { text-align: center; margin: 1.5rem 0; }
            .pagination a { color: #4a9eff; text-decoration: none; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }
            .pagination a:hover { background: #3a3a3a; }
            .page-info { color: #888; margin: 0 1rem; }
        </style>'''


def _gallery_nav(camera_name, latest_path, videos_path=None):
    """Standard nav bar for gallery pages."""
    videos_link = f' | <a href="{videos_path}">Videos</a>' if videos_path else ''
    return f'''
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{latest_path}">Latest</a> |
            <a href="gallery">Gallery</a>{videos_link}
        </div>'''


def _presign_thumbs(images, thumb_key_fn):
    """Presign thumbnail URLs for a list of images. Falls back to full image if thumb missing."""
    import boto3
    from concurrent.futures import ThreadPoolExecutor

    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = 'gardencam-berrylands-eu-west-1'

    def _presign(img_key):
        thumb_key = thumb_key_fn(img_key)
        # Check if thumbnail exists; fall back to full image
        try:
            s3.head_object(Bucket=bucket, Key=thumb_key)
            key = thumb_key
        except Exception:
            key = img_key
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600,
        )

    keys = [img['key'] for img in images]
    with ThreadPoolExecutor(max_workers=20) as ex:
        return list(ex.map(_presign, keys))


def _render_thumb_grid(images, thumb_urls, fullres_path):
    """Render a grid of thumbnail images with timestamps."""
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
    return thumbs


def _render_exposure_chart(exposure_data):
    """Render a canvas chart of exposure time (log scale) and brightness over a day."""
    if not exposure_data:
        return ''
    import json as _json
    chart_json = _json.dumps(exposure_data)
    return f'''
        <div style="max-width: 900px; margin: 0 auto 1.5rem;">
            <canvas id="expchart" style="width: 100%; border-radius: 8px; background: #2a2a2a;"></canvas>
        </div>
        <script>
        window.addEventListener('DOMContentLoaded', function() {{
        (function() {{
            var data = {chart_json};
            if (data.length < 2) return;
            var canvas = document.getElementById('expchart');
            var w = canvas.parentElement.offsetWidth;
            var h = Math.round(w / 4);
            canvas.width = w * (window.devicePixelRatio || 1);
            canvas.height = h * (window.devicePixelRatio || 1);
            canvas.style.height = h + 'px';
            var ctx = canvas.getContext('2d');
            ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

            var pad = {{top: 20, right: 55, bottom: 30, left: 65}};
            var cw = w - pad.left - pad.right;
            var ch = h - pad.top - pad.bottom;

            // Parse timestamps to hours-since-midnight (local time)
            function toLocalHour(ts) {{
                var t = new Date(ts);
                return t.getHours() + t.getMinutes() / 60;
            }}
            var pts = data.map(function(d) {{
                return {{x: toLocalHour(d.timestamp), exp: d.exposure_s, bright: d.avg_brightness}};
            }}).filter(function(d) {{ return d.exp !== null && d.exp > 0; }});

            var brightPts = data.map(function(d) {{
                return {{x: toLocalHour(d.timestamp), bright: d.avg_brightness}};
            }});

            var xMin = 0, xMax = 24;

            // Log10 exposure range
            var expMin = Math.log10(0.001);  // 1ms floor
            var expMax = pts.length > 0 ? Math.log10(Math.max.apply(null, pts.map(function(d) {{ return d.exp; }}))) : 1;
            expMax = Math.max(expMax, Math.log10(10));  // at least up to 10s

            function xPos(hh) {{ return pad.left + cw * (hh - xMin) / (xMax - xMin); }}
            function yPosExp(e) {{
                var le = Math.log10(Math.max(e, 0.0001));
                return pad.top + ch - ch * (le - expMin) / (expMax - expMin);
            }}
            function yPosBright(b) {{ return pad.top + ch - ch * b / 255; }}

            // Axes box
            ctx.strokeStyle = '#555';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(pad.left, pad.top);
            ctx.lineTo(pad.left, pad.top + ch);
            ctx.lineTo(pad.left + cw, pad.top + ch);
            ctx.lineTo(pad.left + cw, pad.top);
            ctx.stroke();

            // Left Y axis: log exposure ticks
            var expTicks = [0.001, 0.01, 0.1, 1, 5, 10, 30, 60];
            ctx.font = '10px sans-serif';
            ctx.fillStyle = '#4a9eff';
            ctx.textAlign = 'right';
            expTicks.forEach(function(v) {{
                var lv = Math.log10(v);
                if (lv < expMin || lv > expMax) return;
                var y = yPosExp(v);
                var label = v < 1 ? v.toString() + 's' : v + 's';
                ctx.fillText(label, pad.left - 5, y + 4);
                ctx.strokeStyle = '#333';
                ctx.beginPath();
                ctx.moveTo(pad.left, y);
                ctx.lineTo(pad.left + cw, y);
                ctx.stroke();
            }});

            // Right Y axis: brightness (0-255)
            ctx.fillStyle = '#FF9500';
            ctx.textAlign = 'left';
            [0, 64, 128, 192, 255].forEach(function(v) {{
                var y = yPosBright(v);
                ctx.fillText(v, pad.left + cw + 5, y + 4);
            }});

            // X axis: hourly labels
            ctx.fillStyle = '#888';
            ctx.textAlign = 'center';
            for (var h = 0; h <= 24; h += 2) {{
                var x = xPos(h);
                ctx.fillText(String(h).padStart(2,'0') + ':00', x, pad.top + ch + 18);
                if (h > 0 && h < 24) {{
                    ctx.strokeStyle = '#2a2a2a';
                    ctx.beginPath();
                    ctx.moveTo(x, pad.top);
                    ctx.lineTo(x, pad.top + ch);
                    ctx.stroke();
                }}
            }}

            // Plot brightness (orange, right axis)
            if (brightPts.length >= 2) {{
                ctx.strokeStyle = '#FF9500';
                ctx.lineWidth = 2;
                ctx.beginPath();
                brightPts.forEach(function(d, i) {{
                    var x = xPos(d.x), y = yPosBright(d.bright);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }});
                ctx.stroke();
                ctx.fillStyle = '#FF9500';
                brightPts.forEach(function(d) {{
                    ctx.beginPath(); ctx.arc(xPos(d.x), yPosBright(d.bright), 3, 0, Math.PI*2); ctx.fill();
                }});
            }}

            // Plot exposure (blue, left log axis)
            if (pts.length >= 2) {{
                ctx.strokeStyle = '#4a9eff';
                ctx.lineWidth = 2;
                ctx.beginPath();
                pts.forEach(function(d, i) {{
                    var x = xPos(d.x), y = yPosExp(d.exp);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }});
                ctx.stroke();
                ctx.fillStyle = '#4a9eff';
                pts.forEach(function(d) {{
                    ctx.beginPath(); ctx.arc(xPos(d.x), yPosExp(d.exp), 3, 0, Math.PI*2); ctx.fill();
                }});
            }}

            // Legend
            ctx.font = '11px sans-serif';
            var lx = pad.left + 8, ly = pad.top + 13;
            ctx.fillStyle = '#4a9eff'; ctx.fillRect(lx, ly - 4, 12, 3);
            ctx.textAlign = 'left'; ctx.fillText('Exposure (log)', lx + 16, ly);
            ctx.fillStyle = '#FF9500'; ctx.fillRect(lx + 130, ly - 4, 12, 3);
            ctx.fillText('Avg brightness', lx + 146, ly);
        }})();
        }});
        </script>'''


def render_gallery_day(camera_name, day_str, images, *, page, total_pages, total_images,
                       thumb_key_fn, gallery_path, latest_path, fullres_path, week_iso,
                       videos_path=None, exposure_data=None):
    """Day view: today's thumbnails with 'This week' zoom-out link at top.
    exposure_data: optional list of dicts with 'timestamp', 'exposure_s', 'avg_brightness'.
    """
    import json as _json
    from datetime import datetime

    thumb_urls = _presign_thumbs(images, thumb_key_fn)
    thumbs = _render_thumb_grid(images, thumb_urls, fullres_path)

    try:
        dt = datetime.strptime(day_str, '%Y-%m-%d')
        day_label = dt.strftime('%A %d %B %Y')
    except ValueError:
        day_label = day_str

    # Pagination
    pagination = ''
    if total_pages > 1:
        pagination = '<div class="pagination">'
        if page > 1:
            pagination += f'<a href="{gallery_path}?day={day_str}&page={page - 1}">&larr; Prev</a> '
        pagination += f'<span class="page-info">Page {page} of {total_pages} ({total_images} images)</span>'
        if page < total_pages:
            pagination += f' <a href="{gallery_path}?day={day_str}&page={page + 1}">Next &rarr;</a>'
        pagination += '</div>'

    chart_html = _render_exposure_chart(exposure_data)

    return f'''
        <title>{camera_name} - {day_label}</title>
        {_GALLERY_STYLE}
        {_gallery_nav(camera_name, latest_path, videos_path)}
        <div class="zoom-out"><a href="{gallery_path}?week={week_iso}">This week &rarr;</a></div>
        <h1>{day_label}</h1>
        <div class="subtitle">{total_images} image{"s" if total_images != 1 else ""}</div>
        {chart_html}
        {pagination}
        <div class="gallery">{thumbs}</div>
        {pagination}'''


def render_gallery_week(camera_name, week_iso, days_with_counts, *,
                        gallery_path, latest_path, month_str, videos_path=None):
    """Week view: list of days this week, with zoom-out to month."""
    from datetime import datetime

    day_links = ''
    for day_str, count in days_with_counts:
        try:
            dt = datetime.strptime(day_str, '%Y-%m-%d')
            label = dt.strftime('%A %d %B')
        except ValueError:
            label = day_str
        day_links += f'''
            <a href="{gallery_path}?day={day_str}" class="item-link">
                {label}
                <span class="count">{count} image{"s" if count != 1 else ""}</span>
            </a>'''

    if not day_links:
        day_links = '<p style="color:#888; text-align:center;">No images this week.</p>'

    # Parse week for display
    try:
        from datetime import date
        iso_year, iso_week = int(week_iso[:4]), int(week_iso.split('W')[1])
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        sunday = date.fromisocalendar(iso_year, iso_week, 7)
        week_label = f"Week of {monday.strftime('%d %B')} — {sunday.strftime('%d %B %Y')}"
    except (ValueError, IndexError):
        week_label = week_iso

    return f'''
        <title>{camera_name} - {week_label}</title>
        {_GALLERY_STYLE}
        {_gallery_nav(camera_name, latest_path, videos_path)}
        <div class="zoom-out"><a href="{gallery_path}?month={month_str}">{_month_label(month_str)} &rarr;</a></div>
        <h1>{week_label}</h1>
        <div class="item-list">{day_links}</div>'''


def render_gallery_month(camera_name, month_str, weeks_with_days, *,
                         gallery_path, latest_path, year_str, videos_path=None):
    """Month view: weeks in this month, each listing its days."""
    from datetime import datetime

    content = ''
    for week_iso, days in weeks_with_days:
        try:
            from datetime import date
            iso_year, iso_week = int(week_iso[:4]), int(week_iso.split('W')[1])
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            sunday = date.fromisocalendar(iso_year, iso_week, 7)
            week_label = f"{monday.strftime('%d %b')} — {sunday.strftime('%d %b')}"
        except (ValueError, IndexError):
            week_label = week_iso

        day_links = ''
        for day_str, count in days:
            try:
                dt = datetime.strptime(day_str, '%Y-%m-%d')
                label = dt.strftime('%A %d')
            except ValueError:
                label = day_str
            day_links += f'''
                <a href="{gallery_path}?day={day_str}" class="item-link">
                    {label}
                    <span class="count">{count}</span>
                </a>'''

        content += f'''
            <div class="day-section">
                <h2 class="day-heading"><a href="{gallery_path}?week={week_iso}" style="color:#4a9eff; text-decoration:none;">{week_label}</a></h2>
                <div class="item-list">{day_links}</div>
            </div>'''

    if not content:
        content = '<p style="color:#888; text-align:center;">No images this month.</p>'

    return f'''
        <title>{camera_name} - {_month_label(month_str)}</title>
        {_GALLERY_STYLE}
        {_gallery_nav(camera_name, latest_path, videos_path)}
        <div class="zoom-out"><a href="{gallery_path}?year={year_str}">{year_str} &rarr;</a></div>
        <h1>{_month_label(month_str)}</h1>
        <div class="content" style="max-width:800px; margin:0 auto;">{content}</div>'''


def render_gallery_year(camera_name, year_str, months_with_counts, *,
                        gallery_path, latest_path, videos_path=None):
    """Year view: list of months with image counts."""
    month_links = ''
    for month_str, count in months_with_counts:
        month_links += f'''
            <a href="{gallery_path}?month={month_str}" class="item-link">
                {_month_label(month_str)}
                <span class="count">{count} image{"s" if count != 1 else ""}</span>
            </a>'''

    if not month_links:
        month_links = '<p style="color:#888; text-align:center;">No images this year.</p>'

    return f'''
        <title>{camera_name} - {year_str}</title>
        {_GALLERY_STYLE}
        {_gallery_nav(camera_name, latest_path, videos_path)}
        <h1>{year_str}</h1>
        <div class="item-list">{month_links}</div>'''


def _month_label(month_str):
    """Convert '2026-04' to 'April 2026'."""
    from datetime import datetime
    try:
        dt = datetime.strptime(month_str + '-01', '%Y-%m-%d')
        return dt.strftime('%B %Y')
    except ValueError:
        return month_str


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


def _video_cards(videos, play_path='play'):
    """Render video cards for a list of videos."""
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


def _video_nav(camera_name, latest_path, gallery_path, videos_path):
    """Standard nav bar for video pages."""
    return f'''
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="{latest_path}">Latest</a> |
            <a href="{gallery_path}">Gallery</a> |
            <a href="{videos_path}">Videos</a>
        </div>'''


def render_videos_day(camera_name, day_str, videos, *, latest_path, gallery_path, videos_path, week_iso, exposure_data=None):
    """Day view: today's videos with 'This week' zoom-out link."""
    from datetime import datetime

    try:
        dt = datetime.strptime(day_str, '%Y-%m-%d')
        day_label = dt.strftime('%A %d %B %Y')
    except ValueError:
        day_label = day_str

    daily = [v for v in videos if v.get('is_daily')]
    hourly = [v for v in videos if not v.get('is_daily')]
    has_daily = len(daily) > 0
    cast_link = f' <a href="play" class="cast-link">Cast timelapse</a>' if has_daily else ''
    chart_html = _render_exposure_chart(exposure_data)

    return f'''
        <title>{camera_name} Videos - {day_label}</title>
        {_VIDEO_PAGE_STYLE}
        {_video_nav(camera_name, latest_path, gallery_path, videos_path)}
        <div class="zoom-out"><a href="{videos_path}?week={week_iso}">This week &rarr;</a></div>
        <h1>{day_label}{cast_link}</h1>
        <div class="content">
            {_video_cards(daily)}
        </div>
        {chart_html}
        <p style="color:#888; text-align:center; margin-bottom:1.5rem;">{len(hourly)} hourly video{"s" if len(hourly) != 1 else ""}</p>
        <div class="content">
            {_video_cards(hourly)}
        </div>'''


def render_videos_week(camera_name, week_iso, days_with_counts, *,
                       latest_path, gallery_path, videos_path, month_str):
    """Week view: list of days this week with video counts."""
    from datetime import datetime

    day_links = ''
    for day_str, count in days_with_counts:
        try:
            dt = datetime.strptime(day_str, '%Y-%m-%d')
            label = dt.strftime('%A %d %B')
        except ValueError:
            label = day_str
        day_links += f'''
            <a href="{videos_path}?day={day_str}" class="item-link">
                {label}
                <span class="count">{count} video{"s" if count != 1 else ""}</span>
            </a>'''

    if not day_links:
        day_links = '<p style="color:#888; text-align:center;">No videos this week.</p>'

    try:
        from datetime import date
        iso_year, iso_week = int(week_iso[:4]), int(week_iso.split('W')[1])
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        sunday = date.fromisocalendar(iso_year, iso_week, 7)
        week_label = f"Week of {monday.strftime('%d %B')} — {sunday.strftime('%d %B %Y')}"
    except (ValueError, IndexError):
        week_label = week_iso

    return f'''
        <title>{camera_name} Videos - {week_label}</title>
        {_VIDEO_PAGE_STYLE}
        {_video_nav(camera_name, latest_path, gallery_path, videos_path)}
        <div class="zoom-out"><a href="{videos_path}?month={month_str}">{_month_label(month_str)} &rarr;</a></div>
        <h1>{week_label}</h1>
        <div class="item-list">{day_links}</div>'''


def render_videos_month(camera_name, month_str, days_list, *,
                        latest_path, gallery_path, videos_path, year_str):
    """Month view: list of days with video counts."""
    from datetime import datetime

    day_links = ''
    for day_str, count in days_list:
        try:
            dt = datetime.strptime(day_str, '%Y-%m-%d')
            label = dt.strftime('%A %d %B')
        except ValueError:
            label = day_str
        day_links += f'''
            <a href="{videos_path}?day={day_str}" class="item-link">
                {label}
                <span class="count">{count} video{"s" if count != 1 else ""}</span>
            </a>'''

    if not day_links:
        day_links = '<p style="color:#888; text-align:center;">No videos this month.</p>'

    return f'''
        <title>{camera_name} Videos - {_month_label(month_str)}</title>
        {_VIDEO_PAGE_STYLE}
        {_video_nav(camera_name, latest_path, gallery_path, videos_path)}
        <div class="zoom-out"><a href="{videos_path}?year={year_str}">{year_str} &rarr;</a></div>
        <h1>{_month_label(month_str)}</h1>
        <div class="content">
            <div class="item-list">{day_links}</div>
        </div>'''


def render_videos_year(camera_name, year_str, months_with_counts, *,
                       latest_path, gallery_path, videos_path):
    """Year view: list of months with video counts."""
    month_links = ''
    for month_str, count in months_with_counts:
        month_links += f'''
            <a href="{videos_path}?month={month_str}" class="item-link">
                {_month_label(month_str)}
                <span class="count">{count} video{"s" if count != 1 else ""}</span>
            </a>'''

    if not month_links:
        month_links = '<p style="color:#888; text-align:center;">No videos this year.</p>'

    return f'''
        <title>{camera_name} Videos - {year_str}</title>
        {_VIDEO_PAGE_STYLE}
        {_video_nav(camera_name, latest_path, gallery_path, videos_path)}
        <h1>{year_str}</h1>
        <div class="item-list">{month_links}</div>'''


_VIDEO_PAGE_STYLE = '''
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
            .nav { text-align: center; margin-bottom: 1rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 1rem; }
            .nav a:hover { text-decoration: underline; }
            .zoom-out { display: block; text-align: center; margin-bottom: 1.5rem; }
            .zoom-out a { display: inline-block; padding: 0.5rem 1.5rem; background: #2a2a2a; color: #4a9eff; text-decoration: none; border-radius: 8px; font-size: 1rem; transition: background 0.3s; }
            .zoom-out a:hover { background: #3a3a3a; }
            h1 { text-align: center; margin-bottom: 0.5rem; }
            .content { max-width: 1400px; margin: 0 auto; }
            .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
            .video-card { background: #2a2a2a; border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; display: block; transition: transform 0.2s; }
            .video-card:hover { transform: translateY(-4px); }
            .video-thumbnail { height: 100px; background: linear-gradient(135deg, #1e2a1e 0%, #1a1a1a 100%); display: flex; align-items: center; justify-content: center; }
            .play-icon { width: 40px; height: 40px; background: rgba(74,158,255,0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
            .play-icon::after { content: ''; width: 0; height: 0; border-style: solid; border-width: 8px 0 8px 14px; border-color: transparent transparent transparent #fff; margin-left: 2px; }
            .video-meta { padding: 0.5rem 0.75rem; }
            .video-meta h3 { margin: 0 0 0.25rem 0; color: #4a9eff; font-size: 0.85rem; }
            .video-meta p { margin: 0; color: #888; font-size: 0.75rem; }
            .item-list { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.5rem; }
            .item-link { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.5rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1rem; transition: background 0.3s; }
            .item-link:hover { background: #3a3a3a; }
            .item-link .count { color: #888; font-size: 0.85rem; }
            .video-card-daily { grid-column: 1 / -1; max-width: 400px; border: 1px solid #4a9eff; }
            .video-card-daily .video-meta h3 { font-size: 1rem; }
            .cast-link { font-size: 0.85rem; font-weight: normal; color: #4a9eff; text-decoration: none; margin-left: 1rem; }
            .cast-link:hover { text-decoration: underline; }
        </style>'''


VERDICT_GLYPH = {
    "clear":   ("☀",  "#34C759", "Clear"),
    "cloudy":  ("☁",  "#8E8E93", "Cloudy"),
    "rain":    ("🌧",  "#007AFF", "Rain"),
    "moon":    ("🌕",  "#FF9500", "Moon / twilight"),
    "no-data": ("·",   "#8E8E93", "No data"),
}


# Precomputed via astropy (sun-moon elongation extrema), 2026-2027.
# Regenerate with `astro/bin/regen-moon-phases` if extending the range.
_NEW_MOONS = {"2026-01-18", "2026-02-17", "2026-03-19", "2026-04-17",
              "2026-05-16", "2026-06-15", "2026-07-14", "2026-08-12",
              "2026-09-11", "2026-10-10", "2026-11-09", "2026-12-09",
              "2027-01-07", "2027-02-06", "2027-03-08", "2027-04-06",
              "2027-05-06", "2027-06-04", "2027-07-04", "2027-08-02",
              "2027-08-31", "2027-09-30", "2027-10-29", "2027-11-28",
              "2027-12-27"}
_FULL_MOONS = {"2026-01-03", "2026-02-01", "2026-03-03", "2026-04-02",
               "2026-05-01", "2026-05-31", "2026-06-30", "2026-07-29",
               "2026-08-28", "2026-09-26", "2026-10-26", "2026-11-24",
               "2026-12-24", "2027-01-22", "2027-02-20", "2027-03-22",
               "2027-04-20", "2027-05-20", "2027-06-19", "2027-07-18",
               "2027-08-17", "2027-09-15", "2027-10-15", "2027-11-14",
               "2027-12-13"}


def _moon_phase_marker(year: int, month: int, day: int) -> tuple[str, str] | None:
    iso = f"{year:04d}-{month:02d}-{day:02d}"
    if iso in _NEW_MOONS:
        return ("●", "#8E8E93")
    if iso in _FULL_MOONS:
        return ("○", "#FFFFFF")
    return None


def render_starcam_nights_index(nights):
    """Calendar overview at /starcam/nights.

    nights: list of dicts {night, verdict, hours_ok, hours_total, pole_spread_px}
            sorted newest-first.
    """
    from datetime import date as _date, timedelta as _td

    by_iso = {n["night"]: n for n in nights}
    today = _date.today()
    # Anchor: Monday of the current week.
    monday_this_week = today - _td(days=today.weekday())
    # Earliest week: Monday of the week containing the oldest night (or
    # this week if no data yet).
    oldest_iso = min(by_iso) if by_iso else today.isoformat()
    oldest = _date.fromisoformat(oldest_iso)
    monday_oldest = oldest - _td(days=oldest.weekday())
    n_weeks = ((monday_this_week - monday_oldest).days // 7) + 1

    rows = []
    last_month = None
    for w in range(n_weeks):
        week_start = monday_this_week - _td(days=7 * w)
        # Month divider when the row's *Sunday* (week_start + 6) is in
        # a different month from the previous row's Sunday.
        week_end = week_start + _td(days=6)
        month_label = week_end.strftime("%B %Y")
        if month_label != last_month:
            rows.append(
                f'<div style="grid-column:1 / -1;color:#8E8E93;font-size:0.8rem;'
                f'margin:0.6rem 0 0.2rem;">{month_label}</div>')
            last_month = month_label

        for i in range(7):
            d = week_start + _td(days=i)
            moon = _moon_phase_marker(d.year, d.month, d.day)
            moon_html = (f'<span style="position:absolute;top:3px;right:5px;'
                         f'color:{moon[1]};font-size:0.85rem;line-height:1;">'
                         f'{moon[0]}</span>') if moon else ''
            day_label = f'{d.day}'
            if d > today:
                # Future day — placeholder.
                rows.append(
                    f'<div style="position:relative;aspect-ratio:1;'
                    f'background:#050505;border-radius:8px;padding:6px;'
                    f'color:#1a1a1a;font-size:0.75rem;">{day_label}{moon_html}</div>')
                continue
            n = by_iso.get(d.isoformat())
            if n is None:
                rows.append(
                    f'<div style="position:relative;aspect-ratio:1;'
                    f'background:#0a0a0a;border-radius:8px;padding:6px;'
                    f'color:#3a3a3a;font-size:0.75rem;">{day_label}{moon_html}</div>')
                continue
            glyph, colour, _ = VERDICT_GLYPH.get(
                n["verdict"], VERDICT_GLYPH["no-data"])
            rows.append(
                f'<a href="/starcam/night/{n["night"]}" style="position:relative;'
                f'display:flex;flex-direction:column;aspect-ratio:1;'
                f'background:#161616;border-radius:8px;padding:6px;'
                f'text-decoration:none;color:#E0E0E0;border:1px solid {colour};">'
                f'<span style="font-size:0.75rem;color:#8E8E93;">{day_label}</span>'
                f'<span style="flex:1;display:flex;align-items:center;'
                f'justify-content:center;font-size:1.4rem;color:{colour};">'
                f'{glyph}</span>{moon_html}</a>')

    months_html = [
        '<div style="display:grid;grid-template-columns:repeat(7,1fr);'
        'gap:6px;max-width:560px;">'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Mon</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Tue</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Wed</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Thu</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Fri</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Sat</div>'
        '<div style="font-size:0.7rem;color:#8E8E93;text-align:center;">Sun</div>'
        + "".join(rows) +
        '</div>'
    ]

    legend = " · ".join(
        f'<span style="color:{c};">{g}</span> {label}'
        for v, (g, c, label) in VERDICT_GLYPH.items())
    legend += (' · <span style="color:#FFFFFF;">○</span> full moon'
               ' · <span style="color:#8E8E93;">●</span> new moon')

    return f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Star Camera — Nights</title>
<style>
  body {{ background: #000; color: #E0E0E0;
    font-family: -apple-system, 'SF Pro Display', 'Inter', 'Roboto', sans-serif;
    margin: 0; padding: 1rem; max-width: 1100px; margin: 0 auto; }}
  a {{ color: #007AFF; text-decoration: none; }}
  .nav {{ font-size: 0.85rem; margin-bottom: 0.6rem; }}
  .legend {{ color: #8E8E93; font-size: 0.85rem; margin: 0.4rem 0 1rem; }}
</style>
</head><body>
<div class="nav"><a href="/starcam">← Star Camera</a> · <a href="/contents">Home</a></div>
<h1 style="margin:0.6rem 0;font-size:1.4rem;">Nights</h1>
<div class="legend">{legend}</div>
{"".join(months_html) or "<p style='color:#8E8E93;'>No nights published yet.</p>"}
</body></html>'''


def render_starcam_night_results(night_str, summary, urls):
    """Public per-night results page for /starcam/night/<YYYY-MM-DD>.

    summary: parsed summary.json (includes verdict, aggregate, hours[]).
    urls:    dict of presigned URLs keyed by basename
             (brightness.png, all-night-derot.jpg, sum_HH.jpg, ...).
    """
    verdict = summary.get("verdict", "no-data")
    glyph, colour, label = VERDICT_GLYPH.get(verdict, VERDICT_GLYPH["no-data"])
    agg = summary.get("aggregate", {}) or {}
    hours = sorted(summary.get("hours", []) or [],
                   key=lambda h: (int(h["hh"]) + 24) % 36)

    brightness_img = ""
    if urls.get("brightness.png"):
        brightness_img = (
            f'<img src="{urls["brightness.png"]}" '
            f'alt="brightness vs time" style="width:100%;max-width:960px;">')

    derot_img = ""
    if urls.get("all-night-derot.jpg"):
        derot_img = (
            f'<h2>All-night derotation</h2>'
            f'<img src="{urls["all-night-derot.jpg"]}" '
            f'alt="all-night derot" style="width:100%;max-width:960px;'
            f'background:#000;">')

    hour_cards = []
    for h in hours:
        hh = h["hh"]
        thumb_url = urls.get(f"sum_{hh}.jpg")
        thumb = (f'<img src="{thumb_url}" alt="sum_{hh}" '
                 f'style="width:100%;border-radius:8px;background:#000;">'
                 if thumb_url else '<div style="height:120px;'
                 'background:#161616;border-radius:8px;"></div>')
        mean = h.get("mean_brightness")
        mean_str = f"{mean:.2f}" if mean is not None else "—"
        status = h.get("status", "")
        status_colour = ("#34C759" if status == "ok"
                         else "#FF9500" if status == "skipped-bright"
                         else "#8E8E93")
        hour_cards.append(
            f'<div style="background:#161616;border-radius:12px;padding:10px;">'
            f'{thumb}'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-top:6px;">'
            f'<span style="font-weight:600;">{hh}:00</span>'
            f'<span style="color:#8E8E93;font-size:0.85rem;">'
            f'<span style="color:{status_colour};">●</span> {mean_str}</span>'
            f'</div></div>')

    wall = summary.get("wall_seconds") or 0
    wall_str = f"{wall // 60}m {wall % 60}s" if wall else "—"
    spread = agg.get("pole_spread_px")
    spread_str = f"{spread:.0f} px" if spread is not None else "—"

    return f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Star Camera — {night_str}</title>
<style>
  :root {{
    --bg: #000; --card-bg: #161616; --text: #E0E0E0;
    --muted: #8E8E93; --accent: #007AFF; --divider: #2C2C2E;
    --font: -apple-system, 'SF Pro Display', 'Inter', 'Roboto', sans-serif;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font);
         margin: 0; padding: 1rem; max-width: 1100px; margin: 0 auto; }}
  a {{ color: var(--accent); text-decoration: none; }}
  h1 {{ margin: 0.6rem 0; font-size: 1.4rem; }}
  h2 {{ margin: 1.4rem 0 0.6rem; font-size: 1.1rem; color: var(--muted);
        font-weight: 500; }}
  .verdict {{ display: inline-flex; align-items: center; gap: 0.4rem;
              padding: 0.25rem 0.7rem; background: var(--card-bg);
              border-radius: 999px; border: 1px solid {colour};
              color: {colour}; font-size: 0.9rem; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 1.2rem; color: var(--muted);
            font-size: 0.85rem; margin: 0.6rem 0 1.2rem; }}
  .hour-grid {{ display: grid; grid-template-columns: repeat(auto-fill,
                 minmax(140px, 1fr)); gap: 10px; }}
  .nav {{ font-size: 0.85rem; margin-bottom: 0.6rem; }}
</style>
</head><body>
<div class="nav"><a href="/starcam">← Star Camera</a> · <a href="/contents">Home</a></div>
<h1>Star Camera — {night_str}</h1>
<div class="verdict">{glyph} {label}</div>
<div class="stats">
  <span>Hours OK: <b style="color:var(--text);">{agg.get('hours_ok', 0)}/{agg.get('hours_total', 0)}</b></span>
  <span>Skipped (bright): <b style="color:var(--text);">{agg.get('hours_skipped_bright', 0)}</b></span>
  <span>Pole spread: <b style="color:var(--text);">{spread_str}</b></span>
  <span>Wall time: <b style="color:var(--text);">{wall_str}</b></span>
</div>
<h2>Brightness vs time</h2>
{brightness_img}
{derot_img}
<h2>Per-hour stacks</h2>
<div class="hour-grid">{''.join(hour_cards)}</div>
</body></html>'''


def render_skycam_player(video_url, title, hours=None):
    """Render a cast-enabled video player with clock overlay and loop."""
    import json
    hours_json = json.dumps(hours or [])

    return f'''
        <title>Sky Camera — {title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #000; color: #fff; }}
            .nav {{ text-align: center; padding: 0.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
            .player-wrap {{ position: relative; max-width: 1280px; margin: 0 auto; }}
            video {{ width: 100%; display: block; background: #000; }}
            .clock {{
                text-align: center; padding: 0.4rem 0;
                font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
                font-size: 2rem; font-weight: 600; letter-spacing: 0.05em;
                color: #fff;
            }}
            .controls {{ text-align: center; padding: 0.75rem; }}
            .cast-btn {{
                display: inline-block; padding: 0.5rem 1.5rem;
                background: #4a9eff; color: #fff; border: none; border-radius: 8px;
                font-size: 0.9rem; cursor: pointer; transition: opacity 0.2s;
            }}
            .cast-btn:hover {{ opacity: 0.8; }}
            .cast-btn:disabled {{ opacity: 0.4; cursor: default; }}
            .cast-status {{ color: #888; margin-top: 0.3rem; font-size: 0.8rem; }}
            google-cast-launcher {{
                display: inline-block; width: 28px; height: 28px;
                vertical-align: middle; margin-left: 0.75rem; cursor: pointer;
                --connected-color: #4a9eff; --disconnected-color: #888;
            }}
        </style>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="videos">Videos</a>
            <google-cast-launcher></google-cast-launcher>
        </div>
        <div class="player-wrap">
            <video id="player" controls autoplay loop playsinline>
                <source src="{video_url}" type="video/mp4">
            </video>
        </div>
        <div class="clock" id="clock"></div>
        <div class="controls">
            <button class="cast-btn" id="castBtn" onclick="castVideo()" disabled>Cast to TV</button>
            <div class="cast-status" id="castStatus"></div>
        </div>
        <script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
        <script>
            const VIDEO_URL = "{video_url}";
            const VIDEO_TITLE = "{title}";
            const HOURS = {hours_json};
            let castSession = null;

            // Clock overlay: map video position to real time
            const player = document.getElementById('player');
            const clockEl = document.getElementById('clock');

            function updateClock() {{
                if (!player.duration || HOURS.length === 0) return;
                const frac = player.currentTime / player.duration;
                const segIdx = Math.min(Math.floor(frac * HOURS.length), HOURS.length - 1);
                const segFrac = (frac * HOURS.length) - segIdx;
                const hour = HOURS[segIdx];
                const mins = Math.floor(segFrac * 60);
                clockEl.textContent = String(hour).padStart(2, '0') + ':' + String(mins).padStart(2, '0');
            }}
            player.addEventListener('timeupdate', updateClock);
            player.addEventListener('loadedmetadata', updateClock);

            // Cast SDK
            window['__onGCastApiAvailable'] = function(isAvailable) {{
                if (isAvailable) {{
                    const ctx = cast.framework.CastContext.getInstance();
                    ctx.setOptions({{
                        receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
                        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
                    }});
                    ctx.addEventListener(
                        cast.framework.CastContextEventType.SESSION_STATE_CHANGED,
                        function(e) {{
                            if (e.sessionState === cast.framework.SessionState.SESSION_STARTED ||
                                e.sessionState === cast.framework.SessionState.SESSION_RESUMED) {{
                                castSession = ctx.getCurrentSession();
                                document.getElementById('castBtn').disabled = false;
                                document.getElementById('castStatus').textContent = 'Connected to ' + castSession.getCastDevice().friendlyName;
                            }} else {{
                                castSession = null;
                                document.getElementById('castBtn').disabled = true;
                                document.getElementById('castStatus').textContent = '';
                            }}
                        }}
                    );
                }}
            }};

            // Loop via one-item Queue + REPEAT_ALL — the only loop method
            // that worked on the test Chromecast. Trade-off: the Default
            // Media Receiver shows an "up next in N seconds…" overlay near
            // the end of each loop, with the filename. Annoying on short
            // clips, fine on day-long videos. See mywebsite/TODO.md.
            function castVideo() {{
                if (!castSession) return;
                const mediaInfo = new chrome.cast.media.MediaInfo(VIDEO_URL, 'video/mp4');
                mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
                mediaInfo.metadata.title = 'Sky Camera — ' + VIDEO_TITLE;
                const queueItem = new chrome.cast.media.QueueItem(mediaInfo);
                const request = new chrome.cast.media.LoadRequest(mediaInfo);
                request.queueData = new chrome.cast.media.QueueData();
                request.queueData.items = [queueItem];
                request.queueData.repeatMode = chrome.cast.media.RepeatMode.ALL;
                castSession.loadMedia(request).then(
                    function() {{ document.getElementById('castStatus').textContent = 'Playing on TV (looping)'; }},
                    function(e) {{ document.getElementById('castStatus').textContent = 'Cast failed: ' + e; }}
                );
            }}
        </script>'''


def render_clouds_movie(days):
    """Render the "Clouds - The Movie" playlist page.

    days: list of dicts
        [{"date": "2026-05-08",
          "hours": [{"hh":"06", "url":"<presigned>", "size_mb":4.4}, ...]},
         ...]
        oldest first. Each day has 1..24 hourlies; the page builds a
        playlist by flattening (selected days) × (selected hour range).

    Speed buttons: 60 / 50 / 30 / 25 fps. The encoded source is 60fps so
    these map to playbackRate 1.0, 0.833, 0.5, 0.417 respectively.

    Cast: a sliding window of CAST_QUEUE_SIZE items. As the cast playhead
    nears the end of the loaded queue, the page calls queueInsertItems()
    to append more — so playback continues forever without the receiver
    LOAD-message size limit ever biting.
    """
    import json
    days_json = json.dumps(days)

    return f'''<!DOCTYPE html>
<html><head>
<title>Clouds - The Movie</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body {{ font-family: -apple-system, 'SF Pro Display', 'Inter', 'Roboto', sans-serif;
            margin: 0; padding: 0; background: #000; color: #E0E0E0; }}
    .nav {{ text-align: center; padding: 0.5rem; }}
    .nav a {{ color: #007AFF; text-decoration: none; margin: 0 1rem; }}
    .player-wrap {{ position: relative; max-width: 1280px; margin: 0 auto; }}
    video {{ width: 100%; display: block; background: #000; }}
    .now-playing {{ text-align: center; padding: 0.4rem 0; color: #E0E0E0;
                    font-size: 1.1rem; font-weight: 500; }}
    .controls {{ text-align: center; padding: 0.5rem; }}
    .controls button {{
        background: #161616; color: #E0E0E0; border: 1px solid #2C2C2E;
        border-radius: 12px; padding: 0.5rem 1rem; margin: 0 0.25rem;
        font-size: 0.9rem; cursor: pointer;
    }}
    .controls button:hover {{ background: #1f1f1f; }}
    .controls button.active {{ background: #007AFF; color: #fff; border-color: #007AFF; }}
    .controls .group {{ display: inline-block; margin: 0 1rem; }}
    .controls .label {{ color: #8E8E93; font-size: 0.85rem; margin-right: 0.5rem; }}
    .controls input[type=number] {{
        width: 3.5em; background: #161616; color: #E0E0E0;
        border: 1px solid #2C2C2E; border-radius: 6px;
        padding: 0.15rem 0.3rem;
    }}
    .cast-status {{ color: #8E8E93; margin-top: 0.3rem; font-size: 0.8rem; text-align: center; }}
    google-cast-launcher {{
        display: inline-block; width: 28px; height: 28px;
        vertical-align: middle; margin-left: 0.75rem; cursor: pointer;
        --connected-color: #007AFF; --disconnected-color: #8E8E93;
    }}
    .day-list {{ max-width: 1100px; margin: 1rem auto; padding: 0 1rem; }}
    .day-list h3 {{ color: #8E8E93; font-weight: 500; margin: 1rem 0 0.5rem; }}
    .bulk-bar {{ margin: 0.25rem 0 0.75rem; }}
    .day-grid {{ display: grid; grid-template-columns: repeat(4, 1fr);
                 gap: 0.4rem; }}
    @media (max-width: 900px) {{ .day-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 500px) {{ .day-grid {{ grid-template-columns: 1fr; }} }}
    .day-row {{ display: flex; align-items: center; padding: 0.5rem 0.75rem;
                border-radius: 12px; background: #161616;
                cursor: pointer; transition: background 0.15s; }}
    .day-row:hover {{ background: #1f1f1f; }}
    .day-row.playing {{ background: #003a6b; }}
    .day-row.disabled .day-label {{ color: #555; text-decoration: line-through; }}
    .day-row input[type=checkbox] {{
        margin-right: 0.75rem; width: 18px; height: 18px; accent-color: #007AFF;
        cursor: pointer;
    }}
    .day-label {{ flex: 1; color: #E0E0E0; }}
    .day-meta {{ color: #8E8E93; font-size: 0.85rem; }}
</style>
<script>
// Define the Cast SDK callback BEFORE the framework script loads, so
// that when the SDK initialises, our setup runs and the
// <google-cast-launcher> custom element gets registered properly.
window['__onGCastApiAvailable'] = function(isAvailable) {{
    if (!isAvailable) return;
    const ctx = cast.framework.CastContext.getInstance();
    ctx.setOptions({{
        receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
    }});
    ctx.addEventListener(
        cast.framework.CastContextEventType.SESSION_STATE_CHANGED,
        function(e) {{
            if (e.sessionState === cast.framework.SessionState.SESSION_STARTED ||
                e.sessionState === cast.framework.SessionState.SESSION_RESUMED) {{
                window.__castSession = ctx.getCurrentSession();
                const btn = document.getElementById('castBtn');
                if (btn) btn.disabled = false;
                const st = document.getElementById('castStatus');
                if (st) st.textContent =
                    'Connected to ' + window.__castSession.getCastDevice().friendlyName;
            }} else {{
                window.__castSession = null;
                window.__castQueue = [];
                const btn = document.getElementById('castBtn');
                if (btn) btn.disabled = true;
                const st = document.getElementById('castStatus');
                if (st) st.textContent = '';
            }}
        }}
    );
}};
</script>
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
</head><body>
<div class="nav">
    <a href="/skycam/contents">Skycam</a> |
    <a href="/contents">Home</a>
    <google-cast-launcher></google-cast-launcher>
</div>
<div class="player-wrap">
    <video id="player" controls autoplay playsinline></video>
</div>
<div class="now-playing" id="np">Loading…</div>
<div class="controls">
    <div class="group">
        <span class="label">Speed:</span>
        <button data-speed="1.0">60fps</button>
        <button data-speed="0.833">50fps</button>
        <button data-speed="0.5">30fps</button>
        <button data-speed="0.417">25fps</button>
    </div>
    <div class="group">
        <span class="label">Hours:</span>
        <input id="hourFrom" type="number" min="0" max="23" value="8">
        –
        <input id="hourTo" type="number" min="0" max="23" value="20">
    </div>
    <div class="group">
        <button id="prevBtn">← Prev</button>
        <button id="nextBtn">Next →</button>
    </div>
    <div class="group">
        <button id="castBtn" disabled>Cast to TV</button>
    </div>
</div>
<div class="cast-status" id="castStatus"></div>
<div class="day-list">
    <h3>Days (oldest → newest). Click row to play that day. Uncheck to skip.</h3>
    <div class="bulk-bar">
        <button id="selAll">All</button>
        <button id="selNone">None</button>
        <button id="selInvert">Invert</button>
    </div>
    <div id="rows" class="day-grid"></div>
</div>
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
<script>
const DAYS = {days_json};
const CAST_QUEUE_SIZE = 12;     // initial items pushed to receiver
const CAST_REFILL_AHEAD = 3;    // append more when this many items remain

// ---- State ----
const params = new URLSearchParams(location.search);
const offSet = new Set(
    (params.get('off') || localStorage.getItem('cloudsOff') || '')
        .split(',').filter(Boolean));
let speed = parseFloat(params.get('speed') || localStorage.getItem('cloudsSpeed') || '1.0');
let hourFrom = parseInt(params.get('from') || localStorage.getItem('cloudsHourFrom') || '8');
let hourTo   = parseInt(params.get('to')   || localStorage.getItem('cloudsHourTo')   || '20');
let currentIdx = 0;             // index into the flat (day,hour) playlist
let castQueue  = [];            // mirror of items currently on the cast receiver
let castNextItemId = 1;         // monotonic for QueueItem.itemId

const player  = document.getElementById('player');
const np      = document.getElementById('np');
const rowsEl  = document.getElementById('rows');
const fromEl  = document.getElementById('hourFrom');
const toEl    = document.getElementById('hourTo');

fromEl.value = hourFrom;
toEl.value   = hourTo;

// ---- Playlist builders ----

function dayOff(date) {{
    return offSet.has(date.replace(/-/g, ''));
}}

function hoursInRange(day) {{
    return day.hours.filter(h => {{
        const n = parseInt(h.hh, 10);
        return n >= hourFrom && n <= hourTo;
    }});
}}

// Flatten to a list of {{date, hh, url, size_mb}} entries in order.
function playlist() {{
    const out = [];
    for (const d of DAYS) {{
        if (dayOff(d.date)) continue;
        for (const h of hoursInRange(d)) {{
            out.push({{date: d.date, hh: h.hh, url: h.url, size_mb: h.size_mb}});
        }}
    }}
    return out;
}}

function persistState() {{
    const off = Array.from(offSet).join(',');
    localStorage.setItem('cloudsOff', off);
    localStorage.setItem('cloudsSpeed', String(speed));
    localStorage.setItem('cloudsHourFrom', String(hourFrom));
    localStorage.setItem('cloudsHourTo', String(hourTo));
    const np = new URLSearchParams();
    if (off) np.set('off', off);
    if (speed !== 1.0) np.set('speed', String(speed));
    if (hourFrom !== 8) np.set('from', String(hourFrom));
    if (hourTo !== 20) np.set('to', String(hourTo));
    const qs = np.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
}}

// ---- Browser playback ----

function setSpeed(s) {{
    speed = s;
    player.playbackRate = s;
    document.querySelectorAll('.controls button[data-speed]').forEach(b => {{
        b.classList.toggle('active', parseFloat(b.dataset.speed) === s);
    }});
    if (window.__castSession) {{
        const ms = window.__castSession.getMediaSession();
        if (ms) {{
            const legal = [0.5, 1.0, 1.5, 2.0];
            const target = legal.reduce((p, c) =>
                Math.abs(c - speed) < Math.abs(p - speed) ? c : p);
            const req = new chrome.cast.media.SetPlaybackRateRequest(target);
            ms.setPlaybackRate(req, () => {{}}, e => console.warn('cast setPlaybackRate failed', e));
        }}
    }}
    persistState();
}}

function loadByIndex(idx) {{
    const list = playlist();
    if (list.length === 0) {{ np.textContent = 'Nothing selected'; return; }}
    currentIdx = ((idx % list.length) + list.length) % list.length;
    const item = list[currentIdx];
    player.src = item.url;
    player.playbackRate = speed;
    player.play().catch(() => {{}});
    np.textContent = `${{item.date}} hour ${{item.hh}}  (${{currentIdx + 1}} of ${{list.length}})`;
    document.querySelectorAll('.day-row').forEach(r => {{
        r.classList.toggle('playing', r.dataset.date === item.date);
    }});
}}

function next() {{ loadByIndex(currentIdx + 1); }}
function prev() {{ loadByIndex(currentIdx - 1); }}

player.addEventListener('ended', next);

document.querySelectorAll('.controls button[data-speed]').forEach(b => {{
    b.addEventListener('click', () => setSpeed(parseFloat(b.dataset.speed)));
}});
document.getElementById('prevBtn').addEventListener('click', prev);
document.getElementById('nextBtn').addEventListener('click', next);

fromEl.addEventListener('change', () => {{
    hourFrom = parseInt(fromEl.value); persistState(); loadByIndex(0);
}});
toEl.addEventListener('change', () => {{
    hourTo = parseInt(toEl.value); persistState(); loadByIndex(0);
}});

// ---- Day rows ----

function refreshRowsFromOffset() {{
    document.querySelectorAll('.day-row').forEach(r => {{
        const flat = r.dataset.date.replace(/-/g, '');
        const off = offSet.has(flat);
        r.classList.toggle('disabled', off);
        const cb = r.querySelector('input');
        if (cb) cb.checked = !off;
    }});
}}

DAYS.forEach((d) => {{
    const row = document.createElement('div');
    row.className = 'day-row';
    row.dataset.date = d.date;
    const dateFlat = d.date.replace(/-/g, '');
    if (offSet.has(dateFlat)) row.classList.add('disabled');
    row.innerHTML = `
        <input type="checkbox" ${{offSet.has(dateFlat) ? '' : 'checked'}}>
        <span class="day-label">${{d.date}}</span>
        <span class="day-meta">${{d.hours.length}}h</span>
    `;
    const cb = row.querySelector('input');
    cb.addEventListener('click', e => {{
        e.stopPropagation();
        if (cb.checked) {{ offSet.delete(dateFlat); row.classList.remove('disabled'); }}
        else            {{ offSet.add(dateFlat);    row.classList.add('disabled'); }}
        persistState();
    }});
    row.addEventListener('click', () => {{
        if (offSet.has(dateFlat)) {{
            offSet.delete(dateFlat); cb.checked = true;
            row.classList.remove('disabled'); persistState();
        }}
        const list = playlist();
        const idx = list.findIndex(x => x.date === d.date);
        if (idx >= 0) loadByIndex(idx);
    }});
    rowsEl.appendChild(row);
}});

document.getElementById('selAll').addEventListener('click', () => {{
    offSet.clear(); refreshRowsFromOffset(); persistState();
}});
document.getElementById('selNone').addEventListener('click', () => {{
    DAYS.forEach(d => offSet.add(d.date.replace(/-/g, '')));
    refreshRowsFromOffset(); persistState();
}});
document.getElementById('selInvert').addEventListener('click', () => {{
    DAYS.forEach(d => {{
        const f = d.date.replace(/-/g, '');
        if (offSet.has(f)) offSet.delete(f); else offSet.add(f);
    }});
    refreshRowsFromOffset(); persistState();
}});

setSpeed(speed);
loadByIndex(0);

// ---- Cast ----
// Init code lives in the <head> so the SDK script can find the callback
// before the <google-cast-launcher> element is parsed. The session is
// kept on window.__castSession by that init.

function makeQueueItem(entry) {{
    const mi = new chrome.cast.media.MediaInfo(entry.url, 'video/mp4');
    mi.metadata = new chrome.cast.media.GenericMediaMetadata();
    mi.metadata.title = `${{entry.date}} h${{entry.hh}}`;
    const qi = new chrome.cast.media.QueueItem(mi);
    qi.itemId = castNextItemId++;
    return qi;
}}

document.getElementById('castBtn').addEventListener('click', function() {{
    if (!window.__castSession) return;
    const list = playlist();
    if (list.length === 0) {{
        document.getElementById('castStatus').textContent = 'Nothing selected';
        return;
    }}
    castNextItemId = 1;
    castQueue = [];
    // Initial window of CAST_QUEUE_SIZE items starting at currentIdx
    for (let i = 0; i < Math.min(CAST_QUEUE_SIZE, list.length); i++) {{
        castQueue.push(list[(currentIdx + i) % list.length]);
    }}
    const items = castQueue.map(makeQueueItem);
    const request = new chrome.cast.media.LoadRequest(items[0].media);
    request.queueData = new chrome.cast.media.QueueData();
    request.queueData.items = items;
    request.queueData.startIndex = 0;
    request.queueData.repeatMode = chrome.cast.media.RepeatMode.OFF;
    window.__castSession.loadMedia(request).then(
        function() {{
            // Apply nearest-legal speed
            const legal = [0.5, 1.0, 1.5, 2.0];
            const target = legal.reduce((p, c) =>
                Math.abs(c - speed) < Math.abs(p - speed) ? c : p);
            const ms = window.__castSession.getMediaSession();
            if (ms) {{
                const req = new chrome.cast.media.SetPlaybackRateRequest(target);
                ms.setPlaybackRate(req, () => {{}}, e => console.warn('rate failed', e));
                ms.addUpdateListener(onCastUpdate);
            }}
            document.getElementById('castStatus').textContent =
                `Casting from ${{castQueue[0].date}} h${{castQueue[0].hh}} (${{items.length}} loaded; auto-extends), speed ${{target}}× (req ${{speed}}×)`;
        }},
        function(e) {{ document.getElementById('castStatus').textContent = 'Cast failed: ' + JSON.stringify(e); }}
    );
}});

// Auto-extend the cast queue: when the receiver's "items remaining" drops
// below CAST_REFILL_AHEAD, append more from the playlist (looping).
function onCastUpdate(isAlive) {{
    if (!isAlive || !window.__castSession) return;
    const ms = window.__castSession.getMediaSession();
    if (!ms || !ms.items) return;
    const remaining = ms.items.length - ms.items.findIndex(it => it.itemId === ms.currentItemId);
    if (remaining > CAST_REFILL_AHEAD) return;

    // Append next batch from playlist (loop forever)
    const list = playlist();
    if (list.length === 0) return;
    const lastEntry = castQueue[castQueue.length - 1];
    let lastIdxInPlaylist = list.findIndex(e => e.date === lastEntry.date && e.hh === lastEntry.hh);
    if (lastIdxInPlaylist < 0) lastIdxInPlaylist = -1;
    const toAppend = [];
    for (let i = 1; i <= CAST_QUEUE_SIZE; i++) {{
        toAppend.push(list[(lastIdxInPlaylist + i) % list.length]);
    }}
    castQueue = castQueue.concat(toAppend);
    const newItems = toAppend.map(makeQueueItem);
    const req = new chrome.cast.media.QueueInsertItemsRequest(newItems);
    ms.queueInsertItems(req, () => {{}}, e => console.warn('queue extend failed', e));
}}
</script></body></html>'''



# ---------------------------------------------------------------------------
# Starcam renderers
# ---------------------------------------------------------------------------

def render_starcam_index(nights):
    """Render starcam landing: list of nights with stacked image counts.
    nights: list of (evening_date_str, count) e.g. [('2026-04-19', 3), ...]
    """
    items = ''
    for evening_date, count in nights:
        from datetime import datetime, timedelta
        ev = datetime.strptime(evening_date, '%Y-%m-%d')
        morning = ev + timedelta(days=1)
        label = f"{ev.strftime('%A')} / {morning.strftime('%A')} {ev.day}/{morning.day} {ev.strftime('%B %Y')}"
        items += f'''
            <a href="starcam/night?date={evening_date}" class="item-link">
                <span>{label}</span>
                <span class="count">{count} stacked</span>
            </a>'''

    return f'''{_GALLERY_STYLE}
        <title>Starcam</title>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href=".">Sky Camera</a>
        </div>
        <h1>Starcam</h1>
        <p class="subtitle">Stacked long-exposure night images</p>
        <div class="item-list">
        {items}
        </div>'''


def render_starcam_night(evening_date, images, brightness_data=None):
    """Render a single night's stacked images with darkest-100 chart.
    evening_date: str like '2026-04-19'
    images: list of dicts with 'url', 'key', 'timestamp', 'stack_count', 'darkest_100_avg'
    brightness_data: list of dicts with 'time', 'value' (hourly avg brightness from DynamoDB)
    """
    import json as _json
    from datetime import datetime, timedelta
    ev = datetime.strptime(evening_date, '%Y-%m-%d')
    morning = ev + timedelta(days=1)
    label = f"{ev.strftime('%A')} / {morning.strftime('%A')} {ev.day}/{morning.day} {ev.strftime('%B %Y')}"

    # Build chart data with delta from midnight for x positioning
    chart_data = []
    for img in images:
        d100 = img.get('darkest_100_avg', '')
        if d100:
            chart_data.append({'time': img['timestamp'], 'value': int(d100), 'delta': img.get('delta', 0)})
    chart_json = _json.dumps(chart_data)
    brightness_json = _json.dumps(brightness_data or [])

    cards = ''
    for img in images:
        stack_info = f" ({img.get('stack_count', '?')} frames)" if img.get('stack_count') else ''
        cards += f'''
            <div style="margin-bottom: 1.5rem;">
                <a href="../fullres?key={img['key']}">
                    <img src="{img['url']}" alt="Stacked {img['timestamp']}"
                         style="width: 100%; max-width: 800px; border-radius: 8px;">
                </a>
                <div class="ts">{img['timestamp']}{stack_info}</div>
            </div>'''

    return f'''{_GALLERY_STYLE}
        <title>Starcam — {label}</title>
        <div class="nav">
            <a href="../../contents">Home</a> |
            <a href="..">Sky Camera</a> |
            <a href=".">Starcam</a>
        </div>
        <h1>Starcam</h1>
        <p class="subtitle">{label}</p>
        <div style="text-align: center; max-width: 800px; margin: 0 auto 1.5rem;">
            <canvas id="d100chart" style="width: 100%; border-radius: 8px; background: #2a2a2a;"></canvas>
        </div>
        <div style="text-align: center;">
        {cards}
        </div>
        <script>
        (function() {{
            var d100 = {chart_json};
            var bright = {brightness_json};
            if (d100.length < 1 && bright.length < 1) return;
            var canvas = document.getElementById('d100chart');
            var w = canvas.parentElement.offsetWidth;
            var h = Math.round(w / 3);
            canvas.width = w * (window.devicePixelRatio || 1);
            canvas.height = h * (window.devicePixelRatio || 1);
            canvas.style.height = h + 'px';
            var ctx = canvas.getContext('2d');
            ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

            var pad = {{top: 20, right: 55, bottom: 30, left: 55}};
            var cw = w - pad.left - pad.right;
            var ch = h - pad.top - pad.bottom;

            // Find x range from all deltas
            var allDeltas = [];
            d100.forEach(function(d) {{ allDeltas.push(d.delta); }});
            bright.forEach(function(d) {{ allDeltas.push(d.delta); }});
            if (allDeltas.length < 1) return;
            var xMin = Math.min.apply(null, allDeltas);
            var xMax = Math.max.apply(null, allDeltas);
            if (xMin === xMax) {{ xMin -= 1; xMax += 1; }}

            function xPos(delta) {{
                return pad.left + cw * (delta - xMin) / (xMax - xMin);
            }}

            // Convert delta back to time label
            function deltaLabel(d) {{
                var h = d < 0 ? d + 24 : d;
                var hh = Math.floor(h);
                var mm = Math.round((h - hh) * 60);
                return (hh < 10 ? '0' : '') + hh + ':' + (mm < 10 ? '0' : '') + mm;
            }}

            // Left Y axis: darkest 100 (uint16)
            var d100Max = d100.length > 0 ? Math.max.apply(null, d100.map(function(d) {{ return d.value; }})) : 100;
            d100Max = Math.max(d100Max, 100);

            // Right Y axis: brightness (0-255)
            var brightMax = 255;

            // Axes
            ctx.strokeStyle = '#555';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(pad.left, pad.top);
            ctx.lineTo(pad.left, pad.top + ch);
            ctx.lineTo(pad.left + cw, pad.top + ch);
            ctx.lineTo(pad.left + cw, pad.top);
            ctx.stroke();

            // Left Y gridlines + labels (darkest 100)
            ctx.fillStyle = '#4a9eff';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'right';
            var yTicks = 4;
            for (var i = 0; i <= yTicks; i++) {{
                var val = Math.round(d100Max * i / yTicks);
                var y = pad.top + ch - (ch * i / yTicks);
                ctx.fillText(val.toLocaleString(), pad.left - 5, y + 4);
                if (i > 0) {{
                    ctx.strokeStyle = '#333';
                    ctx.beginPath();
                    ctx.moveTo(pad.left, y);
                    ctx.lineTo(pad.left + cw, y);
                    ctx.stroke();
                }}
            }}

            // Right Y labels (brightness)
            ctx.fillStyle = '#FF9500';
            ctx.textAlign = 'left';
            for (var i = 0; i <= yTicks; i++) {{
                var val = Math.round(brightMax * i / yTicks);
                var y = pad.top + ch - (ch * i / yTicks);
                ctx.fillText(val, pad.left + cw + 5, y + 4);
            }}

            // 32768 reference line
            if (d100Max >= 32768 && d100.length > 0) {{
                var refY = pad.top + ch - (ch * 32768 / d100Max);
                ctx.strokeStyle = '#4a9eff';
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(pad.left, refY);
                ctx.lineTo(pad.left + cw, refY);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.fillStyle = '#4a9eff';
                ctx.textAlign = 'left';
                ctx.fillText('target', pad.left + 3, refY - 4);
            }}

            // X labels — hourly ticks
            ctx.fillStyle = '#888';
            ctx.textAlign = 'center';
            var firstHour = Math.ceil(xMin);
            var lastHour = Math.floor(xMax);
            for (var d = firstHour; d <= lastHour; d++) {{
                ctx.fillText(deltaLabel(d), xPos(d), pad.top + ch + 18);
                // Midnight marker
                if (d === 0) {{
                    ctx.strokeStyle = '#555';
                    ctx.setLineDash([2, 2]);
                    ctx.beginPath();
                    ctx.moveTo(xPos(0), pad.top);
                    ctx.lineTo(xPos(0), pad.top + ch);
                    ctx.stroke();
                    ctx.setLineDash([]);
                }}
            }}

            // Plot brightness line (orange, right axis)
            if (bright.length >= 2) {{
                ctx.strokeStyle = '#FF9500';
                ctx.lineWidth = 2;
                ctx.beginPath();
                for (var i = 0; i < bright.length; i++) {{
                    var x = xPos(bright[i].delta);
                    var y = pad.top + ch - (ch * bright[i].value / brightMax);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
                ctx.stroke();
                ctx.fillStyle = '#FF9500';
                for (var i = 0; i < bright.length; i++) {{
                    var x = xPos(bright[i].delta);
                    var y = pad.top + ch - (ch * bright[i].value / brightMax);
                    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
                }}
            }}

            // Plot darkest 100 line (blue, left axis)
            if (d100.length >= 2) {{
                ctx.strokeStyle = '#4a9eff';
                ctx.lineWidth = 2;
                ctx.beginPath();
                for (var i = 0; i < d100.length; i++) {{
                    var x = xPos(d100[i].delta);
                    var y = pad.top + ch - (ch * d100[i].value / d100Max);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
                ctx.stroke();
                ctx.fillStyle = '#4a9eff';
                for (var i = 0; i < d100.length; i++) {{
                    var x = xPos(d100[i].delta);
                    var y = pad.top + ch - (ch * d100[i].value / d100Max);
                    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
                }}
            }}

            // Legend
            ctx.font = '11px sans-serif';
            var lx = pad.left + 5;
            var ly = pad.top + 12;
            ctx.fillStyle = '#4a9eff';
            ctx.fillRect(lx, ly - 4, 12, 3);
            ctx.textAlign = 'left';
            ctx.fillText('Darkest 100 avg', lx + 16, ly);
            ctx.fillStyle = '#FF9500';
            ctx.fillRect(lx + 140, ly - 4, 12, 3);
            ctx.fillText('Avg brightness', lx + 156, ly);
        }})();
        </script>'''
