"""Gardencam page renderers extracted from mywebsite.py."""

import json

try:
    from petname import pet_name
except Exception:
    def pet_name(h):
        return h or "unknown-build"

try:
    import build_info as _bi
    _MW_VERSION = getattr(_bi, "VERSION", "unknown")
    _MW_COMMIT = getattr(_bi, "COMMIT", "unknown")
    _MW_COMMIT_TIME = getattr(_bi, "COMMIT_TIME", "unknown")
    _MW_DEPLOY = getattr(_bi, "DEPLOY_COUNT", 0)
    _MW_DEPLOY_TIME = getattr(_bi, "DEPLOY_TIME", 0)
    _GC_VERSION = getattr(_bi, "GARDENCAM_VERSION", "unknown")
    _GC_COMMIT = getattr(_bi, "GARDENCAM_COMMIT", "unknown")
    _GC_COMMIT_TIME = getattr(_bi, "GARDENCAM_COMMIT_TIME", "unknown")
except Exception:
    _MW_VERSION = _MW_COMMIT = _MW_COMMIT_TIME = "unknown"
    _MW_DEPLOY = 0
    _MW_DEPLOY_TIME = 0
    _GC_VERSION = _GC_COMMIT = _GC_COMMIT_TIME = "unknown"


def _fmt_commit_time(iso):
    if not iso or iso == "unknown":
        return ""
    return iso.replace("T", " ")[:16]


def _build_tag(version, commit, commit_time, deploy=None):
    # Pet name seeded from commit+deploy, so it changes when either the
    # source moves OR a redeploy happens (commit and deploy are independent).
    seed = f"{commit}#{deploy}" if deploy else commit
    pn = pet_name(seed)
    when = _fmt_commit_time(commit_time)
    label = f"{commit}#{deploy}" if deploy else commit
    bits = [f"v{version}", pn, label]
    if when:
        bits.append(when)
    return " · ".join(bits)


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


def _list_rerender_days(max_days=30):
    """List days with hourly + day-concat MP4s, newest-first.
    Prefers skycam/rerender/YYYY/MM/DD/ (faststart re-encoded) when present;
    otherwise falls back to skycam/videos/YYYY/MM/DD/ (the live-encoded set)."""
    import boto3
    from datetime import datetime, timezone, timedelta
    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = "gardencam-berrylands-eu-west-1"
    out = []
    d = datetime.now(timezone.utc)
    for back in range(max_days):
        try_d = d - timedelta(days=back)
        ymd = try_d.strftime("%Y/%m/%d")
        ymd_compact = try_d.strftime("%Y%m%d")
        date_str = try_d.strftime("%Y-%m-%d")

        # Try rerender first.
        rerender_prefix = f"skycam/rerender/{ymd}/"
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=rerender_prefix)
        except Exception:
            resp = {}
        contents = resp.get("Contents", [])
        day_key = None
        hourly = []
        for obj in contents:
            k = obj["Key"]
            if not k.endswith("_rerender.mp4"):
                continue
            stem = k.rsplit("/", 1)[-1][:-len("_rerender.mp4")]
            parts = stem.split("_")
            if len(parts) == 2:
                day_key = k
            elif len(parts) == 3:
                hourly.append((parts[2], k))

        # Fall back to videos/.
        if not (day_key or hourly):
            videos_prefix = f"skycam/videos/{ymd}/"
            try:
                resp = s3.list_objects_v2(Bucket=bucket, Prefix=videos_prefix)
            except Exception:
                resp = {}
            for obj in resp.get("Contents", []):
                k = obj["Key"]
                if not k.endswith(".mp4"):
                    continue
                name = k.rsplit("/", 1)[-1]
                stem = name[:-len(".mp4")]
                parts = stem.split("_")
                # sky_YYYYMMDD_daily.mp4 / sky_YYYYMMDD_night.mp4 / sky_YYYYMMDD_HH.mp4
                if len(parts) == 3 and parts[1] == ymd_compact:
                    tag = parts[2]
                    if tag == "daily":
                        day_key = k
                    elif tag == "night":
                        hourly.append(("night", k))
                    elif tag.isdigit() and len(tag) == 2:
                        hourly.append((tag, k))

        hourly.sort()
        if day_key or hourly:
            out.append({"date": date_str,
                        "day_key": day_key, "hourly": hourly})
    return out


def build_cloudcam_links_block():
    """Two links from /skycam: Timelapse videos (the working hierarchical
    page) and vplayer (stub for the future custom player). No per-repo tags
    here — the top bar carries the single deploy pet name."""
    return (
        '<div style="background: var(--card-bg); border: 1px solid var(--divider); '
        'border-radius: 12px; padding: 1rem; margin-bottom: 1rem; max-width: 900px; '
        'margin-left: auto; margin-right: auto; display: flex; flex-wrap: wrap; '
        'gap: 0.5rem; justify-content: center;">'
        '<a href="/skycam/videos" class="gallery-link" '
        'style="background: var(--accent); color: white;">▶ Timelapse videos</a>'
        '<a href="/skycam/clouds" class="gallery-link">☁ Clouds: The Movie</a>'
        '<a href="/skycam/player-poc" class="gallery-link">⚙ vplayer (stub)</a>'
        '</div>'
    )


def build_skycam_top_bar():
    """The cache-fingerprint bar at the top of /skycam.

    The pet name is the human-friendly identifier for THIS Lambda deploy —
    its only job is letting the eye spot a stale CDN copy. The 'deployed Xm Ys
    ago' counter ticks live in the browser; if it freezes the page is frozen.
    Versions for individual components (gardencam, vplay, etc) live on the
    build-info page, not here."""
    pn = pet_name(f"{_MW_COMMIT}#{_MW_DEPLOY}")
    return (
        '<div style="display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; '
        'align-items: center; padding: 0.4rem 0.8rem; '
        'border-bottom: 1px solid var(--divider); '
        'font-size: 0.85rem; color: var(--text-secondary);">'
        '<a href="/contents" style="color: var(--accent);">Home</a>'
        f'<span>☁ <strong style="color: var(--text);">{pn}</strong></span>'
        f'<span id="deployed-ago" data-deployed="{_MW_DEPLOY_TIME}">'
        'deployed —</span>'
        '<a href="/skycam/build-info" style="color: var(--accent);">build info</a>'
        '</div>'
        '<script>(function(){'
        'var el=document.getElementById("deployed-ago");'
        'if(!el)return;'
        'var t=parseInt(el.dataset.deployed,10);'
        'if(!t){el.textContent="deployed (unknown)";return;}'
        'function fmt(s){'
        'var d=Math.floor(s/86400);s%=86400;'
        'var h=Math.floor(s/3600);s%=3600;'
        'var m=Math.floor(s/60);s%=60;'
        'if(d)return d+"d "+h+"h "+m+"m";'
        'if(h)return h+"h "+m+"m "+s+"s";'
        'if(m)return m+"m "+s+"s";'
        'return s+"s";'
        '}'
        'function tick(){'
        'var now=Math.floor(Date.now()/1000);'
        'el.textContent="deployed "+fmt(now-t)+" ago";'
        '}'
        'tick();setInterval(tick,1000);'
        '})();</script>'
    )


def render_build_info_page():
    """Stub build-info page — lists the components that make up the skycam
    homepage. Currently just shows what mywebsite's deploy can see; will grow
    when vplay is hosted and gardencam emits its own build manifest."""
    rows = [
        ("mywebsite", _MW_VERSION, _MW_COMMIT, _MW_COMMIT_TIME,
         f"#{_MW_DEPLOY}"),
        ("gardencam", _GC_VERSION, _GC_COMMIT, _GC_COMMIT_TIME, ""),
        ("vplay", "(stub)", "", "", ""),
    ]
    body = ""
    for name, ver, commit, ctime, deploy in rows:
        when = _fmt_commit_time(ctime)
        body += (
            f'<tr><td>{name}</td><td>{ver}</td><td>{commit}</td>'
            f'<td>{when}</td><td>{deploy}</td></tr>')
    return f'''<!doctype html><html><head><meta charset="utf-8">
<title>Skycam Build Info</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system,'SF Pro Display','Inter',sans-serif;
    background:#000; color:#E0E0E0; margin:0; padding:1rem; }}
  a {{ color:#007AFF; text-decoration:none; }}
  table {{ border-collapse:collapse; margin:1rem auto; max-width:900px;
    width:100%; }}
  th, td {{ padding:0.5rem 0.75rem; text-align:left;
    border-bottom:1px solid #2C2C2E; }}
  th {{ color:#8E8E93; font-weight:500; font-size:0.85rem; }}
  td {{ font-family: ui-monospace, 'SF Mono', monospace; font-size:0.9rem; }}
  h1 {{ text-align:center; font-weight:500; }}
  .nav {{ text-align:center; }}
  .stub {{ color:#8E8E93; font-style:italic; text-align:center; }}
</style></head><body>
<div class="nav"><a href="/skycam">← Skycam</a></div>
<h1>Build info</h1>
<p class="stub">Stub — components of the skycam homepage. Will fill out as
gardencam / vplay grow their own build manifests.</p>
<table>
<tr><th>Component</th><th>Version</th><th>Commit</th><th>Commit time</th><th>Deploy</th></tr>
{body}
</table>
</body></html>'''


# Backward-compat alias for the existing /skycam handler.
build_cloudcam_poc_banner = build_cloudcam_links_block


def _list_video_tree():
    """Scan skycam/videos/ and skycam/rerender/ and return a nested tree:
        { 'YYYY': { 'MM': { 'DD': {'day_key': k|None, 'hourly': [(hh,k)...]} } } }
    Prefers rerender/ entries when both exist for the same day."""
    import boto3
    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = "gardencam-berrylands-eu-west-1"
    paginator = s3.get_paginator("list_objects_v2")

    def collect(prefix, suffix):
        days = {}
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if not k.endswith(suffix):
                    continue
                rel = k[len(prefix):]
                parts = rel.split("/")
                if len(parts) != 4:
                    continue
                yyyy, mm, dd, fname = parts
                stem = fname[:-len(suffix)]
                seg = stem.split("_")
                day = days.setdefault((yyyy, mm, dd),
                                      {"day_key": None, "hourly": []})
                # rerender names: sky_YYYYMMDD[_HH]_rerender
                # videos names:   sky_YYYYMMDD_HH | sky_YYYYMMDD_daily | _night
                if suffix == "_rerender.mp4":
                    if len(seg) == 2:
                        day["day_key"] = k
                    elif len(seg) == 3:
                        day["hourly"].append((seg[2], k))
                else:
                    if len(seg) == 3:
                        tag = seg[2]
                        if tag == "daily":
                            day["day_key"] = k
                        elif tag == "night":
                            day["hourly"].append(("night", k))
                        elif tag.isdigit() and len(tag) == 2:
                            day["hourly"].append((tag, k))
        return days

    rerender = collect("skycam/rerender/", "_rerender.mp4")
    videos = collect("skycam/videos/", ".mp4")

    merged = {}
    for ymd, d in videos.items():
        merged[ymd] = d
    for ymd, d in rerender.items():
        merged[ymd] = d  # rerender wins outright

    tree = {}
    for (y, m, dd), d in merged.items():
        d["hourly"].sort()
        tree.setdefault(y, {}).setdefault(m, {})[dd] = d
    return tree


_MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def render_timelapse_index():
    """Year → month → day drilldown of skycam timelapse videos.
    Sticky native-video player at top; presigned 1h URLs."""
    import boto3
    from datetime import datetime, timezone
    s3 = boto3.client("s3", region_name="eu-west-1")
    bucket = "gardencam-berrylands-eu-west-1"
    tree = _list_video_tree()

    def presign(k):
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": k}, ExpiresIn=3600)

    today = datetime.now(timezone.utc)
    today_ymd = (today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"))

    def render_day(y, m, dd, day):
        btns = []
        date_str = f"{y}-{m}-{dd}"
        if day["day_key"]:
            url = presign(day["day_key"])
            btns.append(
                f'<button class="vbtn primary" data-src="{url}" '
                f'data-key="{day["day_key"]}" '
                f'data-label="{date_str} whole day">▶ Whole day</button>')
        for hh, k in day["hourly"]:
            url = presign(k)
            btns.append(
                f'<button class="vbtn" data-src="{url}" '
                f'data-key="{k}" '
                f'data-label="{date_str} {hh}">{hh}</button>')
        return (f'<div class="day-card"><div class="day-label">{date_str}</div>'
                f'<div class="btn-row">{"".join(btns)}</div></div>')

    sections = []
    years_sorted = sorted(tree.keys(), reverse=True)
    for y in years_sorted:
        months = tree[y]
        is_current_year = (y == today_ymd[0])
        year_total = sum(len(months[m]) for m in months)
        year_open = " open" if is_current_year else ""
        month_blocks = []
        for m in sorted(months.keys(), reverse=True):
            days = months[m]
            is_current_month = (y, m) == today_ymd[:2]
            month_open = " open" if is_current_month else ""
            day_blocks = [render_day(y, m, dd, days[dd])
                          for dd in sorted(days.keys(), reverse=True)]
            month_blocks.append(
                f'<details class="lvl-month"{month_open}>'
                f'<summary>{_MONTH_NAMES[int(m)]} {y} '
                f'<span class="count">({len(days)} days)</span></summary>'
                f'{"".join(day_blocks)}</details>')
        sections.append(
            f'<details class="lvl-year"{year_open}>'
            f'<summary>{y} <span class="count">({year_total} days)</span></summary>'
            f'{"".join(month_blocks)}</details>')

    tl_tag = _build_tag(_GC_VERSION, _GC_COMMIT, _GC_COMMIT_TIME)

    return f'''<!doctype html><html><head><meta charset="utf-8">
<title>Skycam Timelapse</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;
    background:#000; color:#E0E0E0; margin:0; padding:1rem; }}
  a {{ color:#007AFF; text-decoration:none; }}
  .nav {{ text-align:center; margin-bottom:1rem; }}
  .tag {{ color:#8E8E93; font-size:0.8rem; text-align:center; margin-bottom:1rem; }}
  .player {{ position:sticky; top:0; z-index:10; background:#000;
    padding:0.5rem 0; border-bottom:1px solid #2C2C2E; }}
  video {{ width:100%; max-width:1200px; display:block; margin:0 auto;
    background:#000; }}
  .now-playing {{ text-align:center; color:#8E8E93; font-size:0.85rem;
    margin-top:0.4rem; }}
  .lvl-year, .lvl-month {{ max-width:1200px; margin:0.5rem auto; }}
  .lvl-year > summary {{ font-size:1.2rem; font-weight:600; padding:0.6rem 1rem;
    background:#161616; border-radius:12px; cursor:pointer; list-style:none;
    color:#E0E0E0; }}
  .lvl-month > summary {{ font-size:1rem; padding:0.4rem 1rem;
    margin:0.4rem 0 0.2rem 1rem; cursor:pointer; list-style:none;
    color:#8E8E93; }}
  details > summary::before {{ content:"▸ "; display:inline-block;
    transition:transform 0.15s; }}
  details[open] > summary::before {{ transform:rotate(90deg); }}
  .count {{ color:#8E8E93; font-weight:400; font-size:0.85em; }}
  .day-card {{ background:#161616; border-radius:12px; padding:1rem;
    margin:0.5rem 1rem; }}
  .day-label {{ color:#8E8E93; font-size:0.9rem; margin-bottom:0.5rem; }}
  .btn-row {{ display:flex; flex-wrap:wrap; gap:0.4rem; }}
  .vbtn {{ background:#2C2C2E; color:#E0E0E0; border:none;
    border-radius:8px; padding:0.5rem 0.8rem; font:inherit; font-size:0.9rem;
    cursor:pointer; }}
  .vbtn.primary {{ background:#007AFF; color:#fff; }}
  .vbtn:hover {{ background:#3a3a3c; }}
  .vbtn.primary:hover {{ background:#0a84ff; }}
  .vbtn.active {{ outline:2px solid #007AFF; }}
</style></head><body>
<div class="nav"><a href="/skycam">← Skycam</a> · <a href="/contents">Home</a></div>
<div class="tag">{tl_tag}</div>
<div class="player">
  <video id="v" controls playsinline preload="metadata"></video>
  <div class="now-playing" id="np">Pick a video below</div>
  <div style="text-align:center; margin-top:0.4rem;">
    <a id="adv" href="#" target="_blank"
       style="display:none; color:#007AFF; font-size:0.85rem;">⚙ Open in advanced player ↗</a>
  </div>
</div>
{"".join(sections) if sections else "<p style='text-align:center;color:#8E8E93'>No videos yet.</p>"}
<script>
  const v = document.getElementById('v');
  const np = document.getElementById('np');
  const adv = document.getElementById('adv');
  let active = null;
  document.querySelectorAll('.vbtn').forEach(b => {{
    b.addEventListener('click', () => {{
      if (active) active.classList.remove('active');
      active = b; b.classList.add('active');
      v.src = b.dataset.src; np.textContent = b.dataset.label;
      if (b.dataset.key) {{
        adv.href = '/skycam/player?key=' + encodeURIComponent(b.dataset.key);
        adv.style.display = 'inline';
      }} else {{
        adv.style.display = 'none';
      }}
      v.play().catch(() => {{}});
      v.scrollIntoView({{behavior:'smooth', block:'start'}});
    }});
  }});
</script>
</body></html>'''


def render_player_poc_landing():
    """Landing page at /skycam/player-poc — lists the most recent day's MP4s,
    each link goes to /skycam/player?key=... (the custom POC player)."""
    from urllib.parse import quote
    days = _list_rerender_days(max_days=7)
    pp_tag = _build_tag(_MW_VERSION, _MW_COMMIT, _MW_COMMIT_TIME, _MW_DEPLOY)
    if not days:
        body = '<p style="text-align:center;color:#8E8E93">No videos yet.</p>'
    else:
        d = days[0]
        links = []
        if d["day_key"]:
            links.append(
                f'<a class="vbtn primary" '
                f'href="/skycam/player?key={quote(d["day_key"], safe="")}">'
                f'▶ Whole day</a>')
        for hh, k in d["hourly"]:
            links.append(
                f'<a class="vbtn" '
                f'href="/skycam/player?key={quote(k, safe="")}">{hh}:00</a>')
        body = (
            f'<div class="day-card"><div class="day-label">{d["date"]}</div>'
            f'<div class="btn-row">{"".join(links)}</div></div>')
    return f'''<!doctype html><html><head><meta charset="utf-8">
<title>Skycam Player POC</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;
    background:#000; color:#E0E0E0; margin:0; padding:1rem; }}
  a {{ color:#007AFF; text-decoration:none; }}
  .nav {{ text-align:center; margin-bottom:1rem; }}
  .tag {{ color:#8E8E93; font-size:0.8rem; text-align:center; margin-bottom:1rem; }}
  .day-card {{ background:#161616; border-radius:12px; padding:1rem;
    margin:0.75rem auto; max-width:1200px; }}
  .day-label {{ color:#8E8E93; font-size:0.9rem; margin-bottom:0.5rem; }}
  .btn-row {{ display:flex; flex-wrap:wrap; gap:0.4rem; }}
  .vbtn {{ background:#2C2C2E; color:#E0E0E0; border-radius:8px;
    padding:0.5rem 0.8rem; font-size:0.9rem; display:inline-block; }}
  .vbtn.primary {{ background:#007AFF; color:#fff; }}
</style></head><body>
<div class="nav"><a href="/skycam">← Skycam</a> · <a href="/contents">Home</a></div>
<div class="tag">{pp_tag}</div>
<h2 style="text-align:center;color:#E0E0E0">Player POC</h2>
<p style="text-align:center;color:#8E8E93;font-size:0.9rem">
  Experimental custom player. If broken, use <a href="/skycam/timelapse">Timelapse videos</a>.</p>
{body}
</body></html>'''


def render_skycam_player(key, in_sec=None, out_sec=None, src=None, srcs=None):
    """Render a self-contained custom video player.

    Three ways to specify the video(s):
      - key=skycam/...           presigns the gardencam S3 bucket
      - src=<https URL>          plays a publicly hosted mp4
      - srcs=[<URL>, <URL>, ...] multi-source: first plays, ↑/↓ cycle

    Hostnames are whitelisted to petergrecian.co.uk and *.amazonaws.com.
    """
    from urllib.parse import urlparse
    ALLOWED_HOSTS = ("www.petergrecian.co.uk", "petergrecian.co.uk")

    def _validate(s):
        u = urlparse(s)
        ok = (u.scheme == "https"
              and (u.hostname in ALLOWED_HOSTS
                   or (u.hostname or "").endswith(".amazonaws.com"))
              and ".." not in u.path)
        return (s, u.path.rsplit("/", 1)[-1] or "video") if ok else None

    sources = []  # list of (url, label)
    if srcs:
        for s in srcs:
            v = _validate(s)
            if v is None:
                return None
            sources.append(v)
    elif src:
        v = _validate(src)
        if v is None:
            return None
        sources.append(v)
    else:
        import boto3
        if not key.startswith("skycam/") or ".." in key:
            return None
        s3 = boto3.client("s3", region_name="eu-west-1")
        bucket = "gardencam-berrylands-eu-west-1"
        try:
            url = s3.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
        except Exception:
            return None
        sources.append((url, key.rsplit("/", 1)[-1]))

    video_url, title = sources[0]
    in_attr  = f"{in_sec:.3f}"  if in_sec  is not None else "null"
    out_attr = f"{out_sec:.3f}" if out_sec is not None else "null"
    import json as _json
    import re as _re
    from datetime import datetime as _dt, timezone as _tz

    def _hour_epoch(label):
        """Parse 'sky_YYYYMMDD_HH.mp4' → unix epoch of hour start (UTC).
        Returns None for unrecognised names (e.g. seam_gold.mp4 or _daily)."""
        m = _re.match(r"sky_(\d{4})(\d{2})(\d{2})_(\d{2})\.mp4", label)
        if not m:
            return None
        y, mo, d, h = (int(x) for x in m.groups())
        return int(_dt(y, mo, d, h, tzinfo=_tz.utc).timestamp())

    sources_json = _json.dumps([
        {"url": u, "label": l, "hourEpoch": _hour_epoch(l)} for u, l in sources
    ])

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
    <span class="filename" id="filename">{title}</span>
  </div>
  <div class="controls" id="sourcePicker" style="display:none;"></div>
  <div style="position:relative; max-width:1200px; margin:0 auto;">
    <video id="v" src="{video_url}" preload="auto" playsinline
           x-webkit-airplay="allow"></video>
    <div id="spinner" style="display:none; position:absolute; top:50%; left:50%;
         transform:translate(-50%,-50%); width:48px; height:48px;
         border:4px solid #ffffff44; border-top-color:#fff; border-radius:50%;
         animation:spin 0.8s linear infinite; pointer-events:none;"></div>
  </div>
  <style>@keyframes spin {{ to {{ transform: translate(-50%,-50%) rotate(360deg); }} }}</style>
  <div class="scrub">
    <div class="bar" id="bar"></div>
    <div class="play-region" id="region"></div>
    <div class="marker" id="markIn"  data-label="in"></div>
    <div class="marker" id="markOut" data-label="out"></div>
    <div class="head" id="head"></div>
  </div>
  <div class="controls">
    <button id="rev">◀ Reverse</button>
    <button id="pause">❚❚ Pause</button>
    <button id="fwd" class="active">▶ Forward</button>
    <span class="time" id="time">0.000 / 0.000</span>
    <button data-speed="0.25">¼×</button>
    <button data-speed="0.5">½×</button>
    <button data-speed="1" class="active">1×</button>
    <button data-speed="2">2×</button>
    <button data-speed="4">4×</button>
    <button id="setIn">[ in</button>
    <button id="setOut">out ]</button>
    <button id="clearMarks">clear</button>
    <button id="loop" class="active" title="loop mode">↔</button>
    <button id="share">share</button>
    <button id="fs" title="fullscreen">⛶</button>
    <button id="pip" title="picture-in-picture" style="display:none;">▭</button>
    <button id="airplay" title="AirPlay" style="display:none;">📺</button>
    <a id="dl" class="btn" href="#" download title="download">⤓</a>
  </div>
  <div id="stats" style="max-width:1200px; margin:0.25rem auto;
       color:var(--text-secondary); font-size:0.8rem; text-align:center;
       font-variant-numeric: tabular-nums;">
    <span id="wallTime">—</span> ·
    frame <span id="frameCur">—</span>/<span id="frameTot">—</span> ·
    fps <span id="fpsActual">—</span>/60 ·
    dropped <span id="dropped">0</span>
    <span id="bufferWarn" style="display:none; color:#FF9500;"> ⚠ buffering</span>
  </div>
  <div class="help">space play/pause · ←/→ frame step · ,/. speed · [ / ] markers · L loop mode · R reverse direction · ↑/↓ switch source · F fullscreen</div>
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

  const SOURCES = {sources_json};
  let curIdx = 0;

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

  // Forward play uses the native <video> element. Reverse uses a JS
  // frame-stepper since browsers don't support negative playbackRate for
  // compressed video. There's exactly one playing-state at a time.
  let playing = false;

  function setActive(id) {{
    ["rev", "fwd", "pause"].forEach(x =>
      document.getElementById(x).classList.toggle("active", x === id));
  }}

  function reverseStep(ts) {{
    if (lastTs == null) lastTs = ts;
    const dt = (ts - lastTs) / 1000;
    lastTs = ts;
    let t = v.currentTime - speed * dt;
    if (t <= lo()) {{
      if (loopMode === "pingpong") {{ v.currentTime = lo(); pause(); playForward(); return; }}
      else if (loopMode === "loop") {{ t = hi(); }}
      else {{ v.currentTime = lo(); pause(); return; }}
    }}
    v.currentTime = t;
    rafId = requestAnimationFrame(reverseStep);
  }}

  function playForward() {{
    pause();
    dir = 1;
    if (v.currentTime >= hi() - 0.001) v.currentTime = lo();
    v.playbackRate = speed;
    v.play().catch(() => {{}});
    playing = true;
    setActive("fwd");
  }}
  function playReverse() {{
    pause();
    dir = -1;
    if (v.currentTime <= lo() + 0.001) v.currentTime = hi();
    lastTs = null;
    rafId = requestAnimationFrame(reverseStep);
    playing = true;
    setActive("rev");
  }}
  function pause() {{
    v.pause();
    if (rafId != null) {{ cancelAnimationFrame(rafId); rafId = null; }}
    lastTs = null;
    playing = false;
    setActive("pause");
  }}
  function toggle() {{
    if (playing) pause();
    else if (dir < 0) playReverse();
    else playForward();
  }}

  document.getElementById("pause").onclick = pause;
  document.getElementById("rev").onclick   = playReverse;
  document.getElementById("fwd").onclick   = playForward;
  document.querySelectorAll("[data-speed]").forEach(b => {{
    b.onclick = () => {{
      speed = parseFloat(b.dataset.speed);
      document.querySelectorAll("[data-speed]").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      if (playing && dir > 0) v.playbackRate = speed;
    }};
  }});
  document.getElementById("setIn").onclick  = () => {{ inPt  = v.currentTime; if (outPt != null && inPt > outPt) outPt = null; repaint(); }};
  document.getElementById("setOut").onclick = () => {{ outPt = v.currentTime; if (inPt  != null && outPt < inPt) inPt = null;  repaint(); }};
  document.getElementById("clearMarks").onclick = () => {{ inPt = outPt = null; repaint(); }};
  document.getElementById("loop").onclick = () => {{
    loopMode = loopMode === "pingpong" ? "loop" : loopMode === "loop" ? "once" : "pingpong";
    const glyph = loopMode === "pingpong" ? "↔" : loopMode === "loop" ? "↻" : "→";
    const btn = document.getElementById("loop");
    btn.textContent = glyph;
    btn.title = "loop: " + loopMode;
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
    else if (e.key === "r" || e.key === "R") {{ if (dir > 0) playReverse(); else playForward(); }}
    else if (e.code === "ArrowUp")   {{ e.preventDefault(); swap(curIdx - 1); }}
    else if (e.code === "ArrowDown") {{ e.preventDefault(); swap(curIdx + 1); }}
    else if (e.key >= "1" && e.key <= "9") {{ const i = parseInt(e.key, 10) - 1; if (i < SOURCES.length) swap(i); }}
    else if (e.key === "f" || e.key === "F") document.getElementById("fs").click();
  }});

  v.addEventListener("loadedmetadata", () => {{
    if (inPt  != null) inPt  = Math.max(0, Math.min(dur(), inPt));
    if (outPt != null) outPt = Math.max(0, Math.min(dur(), outPt));
    if (inPt != null) v.currentTime = inPt;
    repaint();
  }});

  // Enforce the out-marker / loop mode during native forward play.
  v.addEventListener("timeupdate", () => {{
    repaint();
    if (playing && dir > 0 && v.currentTime >= hi() - 0.01) {{
      if (loopMode === "pingpong") {{ v.currentTime = hi(); pause(); playReverse(); }}
      else if (loopMode === "loop") {{ v.currentTime = lo(); }}
      else {{ pause(); v.currentTime = hi(); }}
    }}
  }});

  // ---- Stats / world time / fullscreen / pip / airplay / dl ----
  const WALLCLOCK_PER_VIDEO_SEC = 180;
  const OUTPUT_FPS = 60;
  const wallEl    = document.getElementById("wallTime");
  const frameCur  = document.getElementById("frameCur");
  const frameTot  = document.getElementById("frameTot");
  const fpsActual = document.getElementById("fpsActual");
  const droppedEl = document.getElementById("dropped");
  const bufferWarn= document.getElementById("bufferWarn");
  const spinner   = document.getElementById("spinner");

  function fmtWall(sec) {{
    const d = new Date(sec * 1000);
    return d.toLocaleTimeString("en-GB", {{ hour:"2-digit", minute:"2-digit",
        second:"2-digit", timeZone:"Europe/London" }});
  }}

  function updateStats() {{
    const D = dur();
    if (D) frameTot.textContent = Math.round(D * OUTPUT_FPS);
    frameCur.textContent = Math.round(v.currentTime * OUTPUT_FPS);
    const cur = SOURCES[curIdx];
    if (cur && cur.hourEpoch != null) {{
      wallEl.textContent = fmtWall(cur.hourEpoch + v.currentTime * WALLCLOCK_PER_VIDEO_SEC);
    }} else {{
      wallEl.textContent = "—";
    }}
  }}

  // FPS measurement + dropped frames via requestVideoFrameCallback if available.
  let lastVFCTs = null, vfcFrames = 0, fpsWindow = [];
  let droppedBase = 0;
  function vfc(now, meta) {{
    if (lastVFCTs != null) {{
      const dt = (now - lastVFCTs) / 1000;
      if (dt > 0 && dt < 1) fpsWindow.push(1 / dt);
      if (fpsWindow.length > 30) fpsWindow.shift();
      const avg = fpsWindow.reduce((a, b) => a + b, 0) / fpsWindow.length;
      fpsActual.textContent = avg.toFixed(1);
    }}
    lastVFCTs = now;
    vfcFrames++;
    if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(vfc);
  }}
  if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(vfc);

  setInterval(() => {{
    updateStats();
    if (v.getVideoPlaybackQuality) {{
      const q = v.getVideoPlaybackQuality();
      droppedEl.textContent = (q.droppedVideoFrames - droppedBase);
    }}
    // Buffered indicator: warn if currentTime is past the buffered end.
    let inBuf = false;
    for (let i = 0; i < v.buffered.length; i++) {{
      if (v.currentTime >= v.buffered.start(i) - 0.1 &&
          v.currentTime <= v.buffered.end(i) + 0.1) {{ inBuf = true; break; }}
    }}
    bufferWarn.style.display = (!playing || inBuf) ? "none" : "inline";
  }}, 250);

  v.addEventListener("playing", () => {{ spinner.style.display = "none"; }});
  v.addEventListener("waiting", () => {{ spinner.style.display = playing ? "block" : "none"; }});
  v.addEventListener("canplay", () => {{ spinner.style.display = "none"; }});
  // Reset dropped baseline when switching sources or starting fresh playback.
  v.addEventListener("loadstart", () => {{
    if (v.getVideoPlaybackQuality) droppedBase = v.getVideoPlaybackQuality().droppedVideoFrames;
    fpsWindow = []; lastVFCTs = null;
  }});

  // Fullscreen / PiP / AirPlay / Download wiring.
  document.getElementById("fs").onclick = () => {{
    if (document.fullscreenElement) document.exitFullscreen();
    else v.requestFullscreen?.();
  }};
  const pipBtn = document.getElementById("pip");
  if (document.pictureInPictureEnabled) {{
    pipBtn.style.display = "";
    pipBtn.onclick = async () => {{
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else await v.requestPictureInPicture();
    }};
  }}
  const apBtn = document.getElementById("airplay");
  if (window.WebKitPlaybackTargetAvailabilityEvent) {{
    apBtn.style.display = "";
    apBtn.onclick = () => v.webkitShowPlaybackTargetPicker?.();
  }}
  // Download link: use current source URL, force a sensible filename.
  function refreshDownload() {{
    const cur = SOURCES[curIdx];
    if (!cur) return;
    const dl = document.getElementById("dl");
    dl.href = cur.url;
    dl.setAttribute("download", cur.label || "video.mp4");
  }}
  refreshDownload();

  // Media Session API: hardware keys / lockscreen integration.
  if ("mediaSession" in navigator) {{
    navigator.mediaSession.setActionHandler("play", playForward);
    navigator.mediaSession.setActionHandler("pause", pause);
  }}

  // ---- Multi-source A/B ----
  function swap(i) {{
    if (i < 0) i = SOURCES.length - 1;
    if (i >= SOURCES.length) i = 0;
    if (i === curIdx || !SOURCES[i]) return;
    const wasPlaying = playing;
    const wasDir = dir;
    const t = v.currentTime;
    curIdx = i;
    document.getElementById("filename").textContent = SOURCES[i].label;
    document.querySelectorAll("#sourcePicker button").forEach((b, j) =>
      b.classList.toggle("active", j === i));
    refreshDownload();
    pause();
    v.src = SOURCES[i].url;
    const onMeta = () => {{
      v.removeEventListener("loadedmetadata", onMeta);
      v.currentTime = Math.min(t, dur());
      repaint();
      if (wasPlaying) {{ wasDir > 0 ? playForward() : playReverse(); }}
    }};
    v.addEventListener("loadedmetadata", onMeta);
    v.load();
  }}

  if (SOURCES.length > 1) {{
    const picker = document.getElementById("sourcePicker");
    picker.style.display = "flex";
    SOURCES.forEach((s, i) => {{
      const b = document.createElement("button");
      b.textContent = (i + 1) + ". " + s.label;
      if (i === 0) b.classList.add("active");
      b.onclick = () => swap(i);
      picker.appendChild(b);
    }});
  }}
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
            {build_skycam_top_bar()}
            <h1>Sky Camera</h1>
            <div style="margin-bottom: 1rem;">
                <a href="gardencam/gallery" class="gallery-link">Stills</a>
                <a href="/skycam/videos" class="gallery-link" style="margin-left: 0.5rem;">Videos</a>
                <a href="/skycam/starcam" class="gallery-link" style="margin-left: 0.5rem;">Starcam</a>
                <span style="color: var(--text-secondary); margin-left: 0.5rem; font-size: 0.85rem;">see also springcam (offline)</span>
            </div>
            {poc_banner_html}
            <div style="margin-bottom: 1rem;">
                <a href="gardencam/stats" class="gallery-link">Capture Stats</a>
                <a href="gardencam/s3-stats" class="gallery-link" style="margin-left: 0.5rem;">Storage Stats</a>
                <button id="captureBtn" class="gallery-link" style="margin-left: 0.5rem; cursor: pointer;">📷 Capture Now</button>
            </div>
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
