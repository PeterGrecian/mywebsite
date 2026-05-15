"""Shared camera page renderers for springcam and skycam."""


def render_camera_latest(camera_name, images, *, theme_css_js, gallery_path, fullres_path, videos_path=None, starcam_path=None):
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

            function castVideo() {{
                if (!castSession) return;
                const mediaInfo = new chrome.cast.media.MediaInfo(VIDEO_URL, 'video/mp4');
                mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
                mediaInfo.metadata.title = 'Sky Camera — ' + VIDEO_TITLE;
                // Queue of one item with REPEAT_ALL so the cast receiver loops.
                // (LoadRequest's `loop` flag isn't honoured by the Default Media
                // Receiver; the queue path is the reliable one.)
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
