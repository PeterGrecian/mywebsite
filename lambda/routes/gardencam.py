"""Gardencam page renderers extracted from mywebsite.py."""

import json


def render_gardencam_stats(windows, summary):
    """Render the gardencam statistics page with brightness charts.

    Args:
        windows: list of dicts with 'label', 'data' (list of dicts with
                 'timestamp_str', 'avg_brightness', 'mode')
        summary: dict with 'total_images', 'day_count', 'night_count',
                 'stacking_count', 'avg_brightness'
    """
    html = f'''
        <title>Garden Camera Statistics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .chart-container {{ max-width: 1400px; margin: 0 auto 2rem auto; background: #2a2a2a; padding: 1.5rem; border-radius: 8px; }}
            .chart-title {{ font-size: 1.1rem; margin-bottom: 1rem; color: #aaa; text-align: center; }}
            .chart-subtitle {{ font-size: 0.9rem; color: #666; text-align: center; margin-top: -0.5rem; margin-bottom: 1rem; }}
            canvas {{ max-height: 300px; }}
            .stats-summary {{ max-width: 1400px; margin: 0 auto 2rem auto; padding: 1rem; background: #2a2a2a; border-radius: 8px; }}
            .stats-summary h2 {{ margin-top: 0; color: #aaa; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .stat-box {{ background: #1a1a1a; padding: 1rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .legend {{ text-align: center; margin-bottom: 1rem; }}
            .legend-item {{ display: inline-block; margin: 0 1rem; }}
            .legend-color {{ display: inline-block; width: 20px; height: 20px; border-radius: 4px; vertical-align: middle; margin-right: 0.5rem; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="gallery">Gallery</a>
            <a href="videos">Videos</a>
            <a href="s3-stats">Storage</a>
        </div>
        <h1>Garden Camera Statistics</h1>

        <div class="stats-summary">
            <h2>Summary (Last 8 Days)</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{summary['total_images']}</div>
                    <div class="stat-label">Total Images</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{summary['day_count']}</div>
                    <div class="stat-label">Day Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{summary['night_count']}</div>
                    <div class="stat-label">Night Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{summary['stacking_count']}</div>
                    <div class="stat-label">Stacking Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{summary['avg_brightness']:.1f}</div>
                    <div class="stat-label">Avg Brightness</div>
                </div>
            </div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <span class="legend-color" style="background: #f59e0b;"></span>
                <span>Day Mode</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #3b82f6;"></span>
                <span>Night Mode</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #8b5cf6;"></span>
                <span>Stacking Mode</span>
            </div>
        </div>
        '''

    # Create a chart canvas for each window
    for i, window in enumerate(windows):
        if not window['data']:
            continue

        chart_id = f'chart_{i}'
        data_count = len(window['data'])

        html += f'''
        <div class="chart-container">
            <div class="chart-title">{window['label']}</div>
            <div class="chart-subtitle">{data_count} images</div>
            <canvas id="{chart_id}"></canvas>
        </div>
            '''

    # Add JavaScript to create all charts
    html += '''
        <script>
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    ticks: { color: '#888', maxTicksLimit: 12 },
                    grid: { color: '#333' }
                },
                y: {
                    min: 0,
                    max: 255,
                    ticks: { color: '#888' },
                    grid: { color: '#333' },
                    title: {
                        display: true,
                        text: 'Uncorrected Brightness',
                        color: '#aaa'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            return 'Brightness: ' + context.parsed.y.toFixed(1);
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 3,
                    hoverRadius: 6
                },
                line: {
                    borderWidth: 2
                }
            }
        };
        '''

    # Generate chart creation code for each window
    for i, window in enumerate(windows):
        if not window['data']:
            continue

        day_data = []
        night_data = []
        stacking_data = []
        labels = []

        for d in window['data']:
            labels.append(d['timestamp_str'])
            if d['mode'] == 'day':
                day_data.append(d['avg_brightness'])
                night_data.append(None)
                stacking_data.append(None)
            elif d['mode'] == 'stacking':
                day_data.append(None)
                night_data.append(None)
                stacking_data.append(d['avg_brightness'])
            else:
                day_data.append(None)
                night_data.append(d['avg_brightness'])
                stacking_data.append(None)

        chart_id = f'chart_{i}'

        html += f'''
        new Chart(document.getElementById('{chart_id}'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{
                        label: 'Day',
                        data: {json.dumps(day_data)},
                        borderColor: '#f59e0b',
                        backgroundColor: '#f59e0b',
                        spanGaps: false
                    }},
                    {{
                        label: 'Night',
                        data: {json.dumps(night_data)},
                        borderColor: '#3b82f6',
                        backgroundColor: '#3b82f6',
                        spanGaps: false
                    }},
                    {{
                        label: 'Stacking',
                        data: {json.dumps(stacking_data)},
                        borderColor: '#8b5cf6',
                        backgroundColor: '#8b5cf6',
                        spanGaps: false
                    }}
                ]
            }},
            options: chartOptions
        }});
            '''

    html += '''
        </script>
        '''
    return html


def render_gardencam_fullres(timestamp, image_url, stats_display):
    """Render the gardencam full resolution image page."""
    return f'''
            <title>Full Resolution - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ margin-bottom: 1rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                .nav a:hover {{ text-decoration: underline; }}
                h2 {{ margin-bottom: 1rem; color: #aaa; }}
                img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a> | <a href="../gardencam">Latest</a> | <a href="gallery">Gallery</a>
            </div>
            <h2>{timestamp} UTC{stats_display}</h2>
            <img src="{image_url}" alt="Full resolution image">
            '''


def render_gardencam_display(timestamp, image_url, image_key, stats_display):
    """Render the gardencam display-width image page."""
    return f'''
            <title>Display Width - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ margin-bottom: 1rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                .nav a:hover {{ text-decoration: underline; }}
                h2 {{ margin-bottom: 1rem; color: #aaa; }}
                .image-container {{ max-width: 1920px; margin: 0 auto; }}
                img {{ width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a> | <a href="../gardencam">Latest</a> | <a href="gallery">Gallery</a> | <a href="fullres?key={image_key}">Full Res</a>
            </div>
            <h2>{timestamp} UTC{stats_display}</h2>
            <div class="image-container">
                <a href="fullres?key={image_key}">
                    <img src="{image_url}" alt="Display width image">
                </a>
            </div>
            '''


def render_s3_stats(summary_data, sorted_weeks, chart_weeks, chart_counts, chart_sizes):
    """Render the S3 storage statistics page."""
    total_files = summary_data['total_files']
    total_size_gb = summary_data['total_size_gb']
    total_monthly = summary_data['total_monthly']
    yearly_total = summary_data['yearly_total']
    storage_cost = summary_data['storage_cost']
    put_cost = summary_data['put_cost']
    get_cost = summary_data['get_cost']
    generated_at = summary_data['generated_at']

    # Build weekly table rows
    weekly_rows = ''
    for week, data in sorted_weeks:
        size_gb = data.get('size_gb', 0)
        size_bytes = data.get('size', 0)
        size_mb = size_bytes / 1048576 if size_bytes else size_gb * 1024
        weekly_cost = data.get('weekly_cost_usd', 0)
        size_display = f"{size_mb:.1f} MB" if size_gb < 1 else f"{size_gb:.2f} GB"
        weekly_rows += f'''
                    <tr>
                        <td>{week}</td>
                        <td>{data['count']:,}</td>
                        <td>{size_display}</td>
                        <td>${weekly_cost:.4f}</td>
                    </tr>
                '''

    return f'''
        <title>S3 Storage Statistics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .chart-container {{ max-width: 1400px; margin: 0 auto 3rem auto; background: #2a2a2a; padding: 1.5rem; border-radius: 8px; }}
            .chart-title {{ font-size: 1.2rem; margin-bottom: 1rem; color: #aaa; text-align: center; }}
            canvas {{ max-height: 400px; }}
            .stats-summary {{ max-width: 1400px; margin: 0 auto 2rem auto; padding: 1rem; background: #2a2a2a; border-radius: 8px; }}
            .stats-summary h2 {{ margin-top: 0; color: #aaa; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .stat-box {{ background: #1a1a1a; padding: 1rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .weekly-table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            .weekly-table th, .weekly-table td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #3a3a3a; }}
            .weekly-table th {{ color: #aaa; background: #1a1a1a; }}
            .weekly-table td {{ font-family: monospace; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="gallery">Gallery</a>
            <a href="videos">Videos</a>
            <a href="stats">Capture Stats</a>
        </div>
        <h1>S3 Storage Statistics</h1>

        <div class="stats-summary">
            <h2>Total Storage</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{total_files:,}</div>
                    <div class="stat-label">Total Files</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_size_gb:.2f} GB</div>
                    <div class="stat-label">Total Size</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${total_monthly:.3f}</div>
                    <div class="stat-label">Monthly Total</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${yearly_total:.2f}</div>
                    <div class="stat-label">Yearly Total</div>
                </div>
            </div>
            <div style="margin-top: 1rem; color: #666; font-size: 0.85rem;">
                Breakdown: Storage ${storage_cost:.4f} + PUT requests ${put_cost:.4f} + GET requests ${get_cost:.4f}
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Files per Week</div>
            <canvas id="countChart"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">Storage Size per Week (GB)</div>
            <canvas id="sizeChart"></canvas>
        </div>

        <div class="stats-summary">
            <h2>Weekly Breakdown</h2>
            <table class="weekly-table">
                <thead>
                    <tr>
                        <th>Week</th>
                        <th>Files</th>
                        <th>Size</th>
                        <th>Weekly Cost</th>
                    </tr>
                </thead>
                <tbody>
        {weekly_rows}
                </tbody>
            </table>
            <p style="color: #666; font-size: 0.85rem; margin-top: 1rem;">Last updated: {generated_at}</p>
        </div>

        <script>
        const chartWeeks = {json.dumps(chart_weeks)};
        const chartCounts = {json.dumps(chart_counts)};
        const chartSizes = {json.dumps(chart_sizes)};

        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: true,
            scales: {{
                x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }},
                y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }}
            }},
            plugins: {{ legend: {{ labels: {{ color: '#aaa' }} }} }}
        }};

        new Chart(document.getElementById('countChart'), {{
            type: 'bar',
            data: {{
                labels: chartWeeks,
                datasets: [{{
                    label: 'Files',
                    data: chartCounts,
                    backgroundColor: '#4a9eff'
                }}]
            }},
            options: chartOptions
        }});

        new Chart(document.getElementById('sizeChart'), {{
            type: 'bar',
            data: {{
                labels: chartWeeks,
                datasets: [{{
                    label: 'Size (GB)',
                    data: chartSizes,
                    backgroundColor: '#10b981'
                }}]
            }},
            options: chartOptions
        }});
        </script>
            '''


def render_s3_stats_error(cache_error):
    """Render the S3 stats error page when cache is unavailable."""
    return f'''
            <title>S3 Storage Statistics</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                .error {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
                .error h1 {{ color: #ef4444; }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
            </div>
            <div class="error">
                <h1>Cache Not Available</h1>
                <p>The storage summary cache has not been generated yet.</p>
                <p style="color: #888;">Error: {cache_error}</p>
                <p style="color: #666; font-size: 0.9rem;">The cache is updated hourly by a scheduled Lambda function.</p>
            </div>
            '''


def render_gallery_week_index(weeks):
    """Render the gallery week index page."""
    week_links = ''
    for week_name in weeks:
        week_links += f'''
                <a href="gallery?week={week_name}" class="week-link">
                    {week_name}
                </a>
                '''

    return f'''
            <title>Garden Camera Gallery - Weekly Index</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ text-align: center; margin-bottom: 2rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                .nav a:hover {{ text-decoration: underline; }}
                h1 {{ text-align: center; margin-bottom: 2rem; }}
                .week-list {{ max-width: 800px; margin: 0 auto; }}
                .week-link {{ display: block; padding: 1rem 1.5rem; margin-bottom: 0.75rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1.1rem; transition: background 0.3s; }}
                .week-link:hover {{ background: #3a3a3a; }}
                .week-count {{ float: right; color: #888; font-size: 0.9rem; }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
                <a href="videos">Videos</a>
                <a href="stats">Statistics</a>
            </div>
            <h1>Garden Camera Gallery - By Week</h1>
            <div class="week-list">
            {week_links}</div>'''


def render_gallery_days(week_param, days):
    """Render the gallery days-in-week page."""
    day_links = ''
    for day_name, day_images in days:
        day_links += f'''
                    <a href="gallery?week={week_param}&day={day_name}" class="day-link">
                        {day_name}
                    </a>
                    '''

    return f'''
                <title>{week_param} - Days</title>
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
                    <a href="../../contents">Home</a>
                    <a href="gallery">All Weeks</a>
                    <a href="../gardencam">Latest</a>
                </div>
                <h1>{week_param}</h1>
                <div class="day-list">
                {day_links}</div>'''


def render_gallery_images_header(day_param, week_param, prev_link, next_link):
    """Render the gallery images page header (CSS + nav). Thumbnails appended by caller."""
    return f'''
                <title>{day_param} - Gallery</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                    .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                    .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                    .nav a:hover {{ background: #3a3a3a; }}
                    h1 {{ text-align: center; margin-bottom: 2rem; }}
                    .thumbnails {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; max-width: 1400px; margin: 0 auto; }}
                    .thumb-container {{ position: relative; }}
                    .thumb-container a {{ display: block; }}
                    .thumb-container img {{ width: 100%; height: 150px; object-fit: cover; border-radius: 6px; transition: transform 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
                    .thumb-container img:hover {{ transform: scale(1.05); }}
                    .thumb-time {{ text-align: center; font-size: 0.85rem; color: #888; margin-top: 0.3rem; }}

                    @media (max-width: 768px) {{
                        .thumbnails {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; }}
                        .thumb-container img {{ height: 120px; }}
                    }}
                </style>
                    <div class="nav">
                        <a href="../../contents">Home</a>
                        {prev_link}
                        <a href="gallery?week={week_param}">Week Index</a>
                        <a href="gallery">All Weeks</a>
                        <a href="../gardencam">Latest</a>
                        {next_link}
                    </div>
                    <h1>{day_param}</h1>
                '''


def build_cloudcam_poc_banner():
    """Presign and return HTML for the cloudcam timelapse POC banner.
    Lists the most recent day's hourly + day-concat rerender MP4s under
    skycam/rerender/ (looking back up to 7 days to survive day rollover
    before that day's rerender has run)."""
    import boto3
    from datetime import datetime, timezone, timedelta
    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = "gardencam-berrylands-eu-west-1"
    contents = []
    d = datetime.now(timezone.utc)
    for back in range(7):
        try_d = d - timedelta(days=back)
        prefix = f"skycam/rerender/{try_d.strftime('%Y/%m/%d')}/"
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        except Exception:
            return ""
        contents = resp.get("Contents", [])
        if contents:
            d = try_d
            break
    if not contents:
        return ""
    day_key = None
    hourly = []
    for obj in contents:
        k = obj["Key"]
        if not k.endswith("_rerender.mp4"):
            continue
        name = k.rsplit("/", 1)[-1]
        # day concat: sky_YYYYMMDD_rerender.mp4 (no hour segment)
        stem = name[:-len("_rerender.mp4")]
        parts = stem.split("_")
        if len(parts) == 2:
            day_key = k
        elif len(parts) == 3:
            hourly.append((parts[2], k))
    hourly.sort()

    from urllib.parse import quote
    def player_url(k):
        return f"/skycam/player?key={quote(k, safe='')}"

    parts_html = []
    if day_key:
        parts_html.append(
            f'<a href="{player_url(day_key)}" class="gallery-link" '
            f'style="background: var(--accent); color: white;">▶ Whole day</a>')
    for hh, k in hourly:
        parts_html.append(
            f'<a href="{player_url(k)}" class="gallery-link" '
            f'style="padding: 0.4rem 0.8rem; font-size: 0.9rem;">{hh}:00</a>')
    if not parts_html:
        return ""
    return (
        '<div style="background: var(--card-bg); border: 1px solid var(--divider); '
        'border-radius: 12px; padding: 1rem; margin-bottom: 1rem; max-width: 900px; '
        'margin-left: auto; margin-right: auto;">'
        '<div style="color: var(--text-secondary); font-size: 0.9rem; '
        'margin-bottom: 0.5rem;">Cloudcam timelapse POC '
        f'({d.strftime("%Y-%m-%d")} UTC)</div>'
        '<div style="display: flex; flex-wrap: wrap; gap: 0.4rem; '
        'justify-content: center;">' + "".join(parts_html) + '</div></div>'
    )


def render_skycam_player(key, in_sec=None, out_sec=None):
    """Render a self-contained custom video player for a skycam/* S3 key.
    Validates and presigns the key (1h URL); the page itself is permanent
    and shareable via /skycam/player?key=...&in=...&out=...
    """
    import boto3
    from urllib.parse import quote
    if not key.startswith("skycam/") or ".." in key:
        return None
    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = "gardencam-berrylands-eu-west-1"
    try:
        video_url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
    except Exception:
        return None

    title = key.rsplit("/", 1)[-1]
    in_attr  = f"{in_sec:.3f}"  if in_sec  is not None else "null"
    out_attr = f"{out_sec:.3f}" if out_sec is not None else "null"
    share_key = quote(key, safe="")

    return f'''<!doctype html>
<html lang="en"><head>
{_THEME_CSS_JS}
<title>Sky Camera — {title}</title>
<style>
  body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
  .top {{ display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem; }}
  .top a {{ color: var(--accent); text-decoration: none; }}
  .filename {{ color: var(--text-secondary); font-size: 0.9rem; }}
  video {{ width: 100%; max-width: 1200px; display: block; margin: 0 auto; background: #000; border-radius: 8px; }}
  .controls {{ max-width: 1200px; margin: 0.75rem auto; display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; justify-content: center; }}
  button, .btn {{ font: inherit; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; padding: 0.4rem 0.8rem; cursor: pointer; }}
  button:hover {{ opacity: 0.8; }}
  button.active {{ background: var(--accent); color: white; }}
  .scrub {{ max-width: 1200px; margin: 0.5rem auto; position: relative; height: 40px; }}
  .bar {{ position: absolute; top: 16px; left: 0; right: 0; height: 8px; background: var(--divider); border-radius: 4px; cursor: pointer; }}
  .play-region {{ position: absolute; top: 16px; height: 8px; background: var(--accent); opacity: 0.4; border-radius: 4px; }}
  .head {{ position: absolute; top: 12px; width: 4px; height: 16px; background: var(--text); border-radius: 2px; transform: translateX(-2px); pointer-events: none; }}
  .marker {{ position: absolute; top: 8px; width: 2px; height: 24px; background: var(--accent); pointer-events: none; }}
  .marker::after {{ content: attr(data-label); position: absolute; top: -16px; left: -8px; font-size: 0.7rem; color: var(--accent); }}
  .time {{ font-variant-numeric: tabular-nums; color: var(--text-secondary); font-size: 0.9rem; min-width: 9rem; text-align: center; }}
  .help {{ max-width: 1200px; margin: 0.5rem auto; color: var(--text-secondary); font-size: 0.8rem; text-align: center; }}
</style>
</head><body>
  <div class="top">
    <a href="/skycam">← Sky Camera</a>
    <span class="filename">{title}</span>
  </div>
  <video id="v" src="{video_url}" preload="auto" playsinline></video>
  <div class="scrub">
    <div class="bar" id="bar"></div>
    <div class="play-region" id="region"></div>
    <div class="marker" id="markIn"  data-label="in"></div>
    <div class="marker" id="markOut" data-label="out"></div>
    <div class="head" id="head"></div>
  </div>
  <div class="controls">
    <button id="rev">◀ Reverse</button>
    <button id="play">▶ Play</button>
    <button id="fwd">▶ Forward</button>
    <span class="time" id="time">0.000 / 0.000</span>
    <button data-speed="0.25">¼×</button>
    <button data-speed="0.5">½×</button>
    <button data-speed="1" class="active">1×</button>
    <button data-speed="2">2×</button>
    <button data-speed="4">4×</button>
    <button id="setIn">[ in</button>
    <button id="setOut">out ]</button>
    <button id="clearMarks">clear</button>
    <button id="loop" class="active">loop: ping-pong</button>
    <button id="share">share</button>
  </div>
  <div class="help">space play/pause · ←/→ frame step · ,/. speed · [ / ] markers · L loop mode · R reverse</div>
<script>
(function() {{
  const v = document.getElementById("v");
  const head = document.getElementById("head");
  const bar  = document.getElementById("bar");
  const region = document.getElementById("region");
  const mIn = document.getElementById("markIn");
  const mOut = document.getElementById("markOut");
  const timeEl = document.getElementById("time");
  const FPS = 24;
  let dir = 1;       // +1 fwd, -1 reverse
  let speed = 1.0;
  let inPt  = {in_attr};
  let outPt = {out_attr};
  let loopMode = "pingpong";  // "pingpong" | "loop" | "once"
  let rafId = null;
  let lastTs = null;

  function dur() {{ return v.duration || 0; }}
  function lo() {{ return inPt  != null ? inPt  : 0; }}
  function hi() {{ return outPt != null ? outPt : dur(); }}

  function fmt(t) {{ if (!isFinite(t)) return "—"; return t.toFixed(3) + "s"; }}
  function repaint() {{
    const D = dur(); if (!D) return;
    head.style.left = (v.currentTime / D * 100) + "%";
    region.style.left  = (lo() / D * 100) + "%";
    region.style.width = ((hi() - lo()) / D * 100) + "%";
    mIn.style.display  = inPt  != null ? "block" : "none";
    mOut.style.display = outPt != null ? "block" : "none";
    if (inPt  != null) mIn.style.left  = (inPt  / D * 100) + "%";
    if (outPt != null) mOut.style.left = (outPt / D * 100) + "%";
    timeEl.textContent = fmt(v.currentTime) + " / " + fmt(D);
  }}

  function step(ts) {{
    if (lastTs == null) lastTs = ts;
    const dt = (ts - lastTs) / 1000;
    lastTs = ts;
    let t = v.currentTime + dir * speed * dt;
    if (t >= hi()) {{
      if (loopMode === "pingpong") {{ t = hi(); dir = -1; }}
      else if (loopMode === "loop") {{ t = lo(); }}
      else {{ t = hi(); cancelAnimationFrame(rafId); rafId = null; lastTs = null; v.pause(); repaint(); return; }}
    }} else if (t <= lo()) {{
      if (loopMode === "pingpong") {{ t = lo(); dir = 1; }}
      else if (loopMode === "loop") {{ t = hi(); }}
      else {{ t = lo(); cancelAnimationFrame(rafId); rafId = null; lastTs = null; v.pause(); repaint(); return; }}
    }}
    v.currentTime = t;
    repaint();
    rafId = requestAnimationFrame(step);
  }}

  function play() {{
    if (rafId != null) return;
    if (dir > 0 && v.currentTime >= hi() - 0.001) v.currentTime = lo();
    if (dir < 0 && v.currentTime <= lo() + 0.001) v.currentTime = hi();
    lastTs = null;
    rafId = requestAnimationFrame(step);
  }}
  function pause() {{
    if (rafId != null) {{ cancelAnimationFrame(rafId); rafId = null; lastTs = null; }}
  }}
  function toggle() {{ rafId == null ? play() : pause(); }}

  document.getElementById("play").onclick = toggle;
  document.getElementById("rev").onclick  = () => {{ dir = -1; play(); }};
  document.getElementById("fwd").onclick  = () => {{ dir =  1; play(); }};
  document.querySelectorAll("[data-speed]").forEach(b => {{
    b.onclick = () => {{
      speed = parseFloat(b.dataset.speed);
      document.querySelectorAll("[data-speed]").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
    }};
  }});
  document.getElementById("setIn").onclick  = () => {{ inPt  = v.currentTime; if (outPt != null && inPt > outPt) outPt = null; repaint(); }};
  document.getElementById("setOut").onclick = () => {{ outPt = v.currentTime; if (inPt  != null && outPt < inPt) inPt = null;  repaint(); }};
  document.getElementById("clearMarks").onclick = () => {{ inPt = outPt = null; repaint(); }};
  document.getElementById("loop").onclick = () => {{
    loopMode = loopMode === "pingpong" ? "loop" : loopMode === "loop" ? "once" : "pingpong";
    document.getElementById("loop").textContent = "loop: " + loopMode;
  }};
  document.getElementById("share").onclick = () => {{
    const u = new URL(location.href);
    if (inPt  != null) u.searchParams.set("in",  inPt.toFixed(3));  else u.searchParams.delete("in");
    if (outPt != null) u.searchParams.set("out", outPt.toFixed(3)); else u.searchParams.delete("out");
    history.replaceState(null, "", u);
    navigator.clipboard?.writeText(u.toString());
    document.getElementById("share").textContent = "copied";
    setTimeout(() => document.getElementById("share").textContent = "share", 1200);
  }};

  bar.onclick = e => {{
    const r = bar.getBoundingClientRect();
    v.currentTime = (e.clientX - r.left) / r.width * dur();
    repaint();
  }};

  document.addEventListener("keydown", e => {{
    if (e.target.tagName === "INPUT") return;
    if (e.code === "Space") {{ e.preventDefault(); toggle(); }}
    else if (e.code === "ArrowLeft")  {{ pause(); v.currentTime = Math.max(lo(), v.currentTime - 1/FPS); repaint(); }}
    else if (e.code === "ArrowRight") {{ pause(); v.currentTime = Math.min(hi(), v.currentTime + 1/FPS); repaint(); }}
    else if (e.key === ",") {{ const speeds=[0.25,0.5,1,2,4]; const i=speeds.indexOf(speed); if (i>0) {{ speed = speeds[i-1]; document.querySelectorAll("[data-speed]").forEach(b=>b.classList.toggle("active", parseFloat(b.dataset.speed)===speed)); }} }}
    else if (e.key === ".") {{ const speeds=[0.25,0.5,1,2,4]; const i=speeds.indexOf(speed); if (i>=0 && i<speeds.length-1) {{ speed = speeds[i+1]; document.querySelectorAll("[data-speed]").forEach(b=>b.classList.toggle("active", parseFloat(b.dataset.speed)===speed)); }} }}
    else if (e.key === "[") document.getElementById("setIn").click();
    else if (e.key === "]") document.getElementById("setOut").click();
    else if (e.key === "l" || e.key === "L") document.getElementById("loop").click();
    else if (e.key === "r" || e.key === "R") {{ dir = -dir; play(); }}
  }});

  v.addEventListener("loadedmetadata", () => {{
    if (inPt  != null) inPt  = Math.max(0, Math.min(dur(), inPt));
    if (outPt != null) outPt = Math.max(0, Math.min(dur(), outPt));
    if (inPt != null) v.currentTime = inPt;
    repaint();
  }});
  v.addEventListener("timeupdate", repaint);
}})();
</script>
</body></html>'''


def render_gardencam_main(images, image_cards, poc_banner_html=""):
    """Render the main gardencam page with latest images."""
    return f'''\
{_THEME_CSS_JS}
            <title>Sky Camera</title>
            <style>
                body {{ font-family: var(--font); text-align: center; margin: 1rem; background: var(--bg); color: var(--text); }}
                h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
                .gallery-link {{ display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1.5rem; background: var(--card-bg); color: var(--accent); text-decoration: none; border-radius: 8px; border: 1px solid var(--divider); transition: opacity 0.2s; }}
                .gallery-link:hover {{ opacity: 0.8; }}
                .gallery {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; max-width: 1024px; margin: 0 auto; }}
                .image-container {{ flex: 1; min-width: 280px; max-width: 340px; }}
                .image-container a {{ display: block; cursor: pointer; }}
                .image-container img {{ width: 100%; height: auto; border-radius: 8px; transition: opacity 0.2s; }}
                .image-container img:hover {{ opacity: 0.85; }}
                .timestamp {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem; }}
                .label {{ color: var(--text-secondary); font-weight: bold; margin-bottom: 0.5rem; font-size: 1rem; }}

                /* Mobile/Tablet - stack vertically */
                @media (max-width: 1024px) {{
                    body {{ margin: 0.5rem; }}
                    h1 {{ font-size: 1.5rem; margin-bottom: 0.75rem; }}
                    .gallery {{ flex-direction: column; gap: 1rem; }}
                    .image-container {{ min-width: 100%; max-width: 100%; }}
                    .label {{ font-size: 1rem; }}
                    .timestamp {{ font-size: 0.85rem; }}
                }}
            </style>
            <div style="text-align: center; margin-bottom: 1rem;">
                <a href="contents" style="color: var(--accent); text-decoration: none;">Home</a>
            </div>
            {poc_banner_html}
            <h1>Sky Camera</h1>
            <a href="gardencam/gallery" class="gallery-link">View Full Gallery</a>
            <a href="gardencam/stats" class="gallery-link" style="margin-left: 0.5rem;">Capture Stats</a>
            <a href="gardencam/s3-stats" class="gallery-link" style="margin-left: 0.5rem;">Storage Stats</a>
            <button id="captureBtn" class="gallery-link" style="margin-left: 0.5rem; cursor: pointer;">📷 Capture Now</button>
            <div id="captureStatus" style="margin-top: 0.5rem; font-size: 0.9rem;"></div>
            <script>
            document.getElementById('captureBtn').addEventListener('click', function() {{
                const btn = this;
                const status = document.getElementById('captureStatus');
                btn.disabled = true;
                btn.textContent = '📷 Capturing...';
                status.textContent = 'Sending capture command...';
                status.style.color = '#4a9eff';

                fetch('gardencam/capture', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        status.textContent = data.message || 'Capture command sent! Image will appear in ~30 seconds.';
                        status.style.color = '#10b981';
                        setTimeout(() => {{
                            btn.disabled = false;
                            btn.textContent = '📷 Capture Now';
                        }}, 3000);
                    }})
                    .catch(error => {{
                        status.textContent = 'Error: ' + error.message;
                        status.style.color = '#ef4444';
                        btn.disabled = false;
                        btn.textContent = '📷 Capture Now';
                    }});
            }});

            // Page load performance tracking
            window.addEventListener('load', function() {{
                // Wait a bit for images to fully load
                setTimeout(function() {{
                    const perfData = window.performance.timing;
                    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
                    const domReadyTime = perfData.domContentLoadedEventEnd - perfData.navigationStart;
                    const serverResponseTime = perfData.responseEnd - perfData.requestStart;

                    // Send timing data to server
                    fetch('gardencam/timing', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            pageLoadTime: pageLoadTime,
                            domReadyTime: domReadyTime,
                            serverResponseTime: serverResponseTime,
                            timestamp: new Date().toISOString(),
                            userAgent: navigator.userAgent
                        }})
                    }}).catch(err => console.log('Timing log failed:', err));
                }}, 500);
            }});
            </script>
            <div class="gallery">
            {image_cards}</div>'''


def render_gardencam_main_card(label, img_key, img_url, timestamp, time_delta, resolution_display, stats_display):
    """Render a single image card for the gardencam main page."""
    return f'''
                <div class="image-container">
                    <div class="label">{label}</div>
                    <a href="gardencam/display?key={img_key}">
                        <img src="{img_url}" alt="{label} capture">
                    </a>
                    <p class="timestamp">{time_delta}{timestamp}{resolution_display}{stats_display}</p>
                </div>
                '''


_THEME_CSS_JS = ''


def _init_theme(theme_css_js):
    """Set the theme CSS/JS for gardencam renderers that need it."""
    global _THEME_CSS_JS
    _THEME_CSS_JS = theme_css_js
