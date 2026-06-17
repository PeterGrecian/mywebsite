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
        '<a href="/skycam/timelapse" class="gallery-link">⚙ Advanced player</a>'
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


def _list_video_tree(bucket="gardencam-berrylands-eu-west-1",
                     video_prefix="skycam/videos/",
                     rerender_prefix="skycam/rerender/"):
    """Scan <bucket>/<video_prefix> (and optionally <rerender_prefix>) and
    return a nested tree:
        { 'YYYY': { 'MM': { 'DD': {'day_key': k|None, 'hourly': [(hh,k)...]} } } }
    Prefers rerender/ entries when both exist for the same day.

    Filename conventions handled (after the camera-name prefix):
      <name>_YYYYMMDD_HH.mp4       — live hourly
      <name>_YYYYMMDD_daily.mp4    — live day
      <name>_YYYYMMDD_night.mp4    — night
      <name>_YYYYMMDD[_HH]_rerender.mp4 — post-processed rerender
    The split-on-underscore tree-builder only inspects seg[2] for the tag,
    so it works for any camera-name prefix (sky/starcam/etc.).

    rerender_prefix=None disables the rerender scan (starcam has no
    rerender pipeline yet)."""
    import boto3
    s3 = boto3.client("s3", region_name="eu-west-1")
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

    videos = collect(video_prefix, ".mp4")
    rerender = collect(rerender_prefix, "_rerender.mp4") if rerender_prefix else {}

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


def _render_day_card(y, m, dd, day, presign=None, camera=None):
    """Render one day's card (label + button row). Used both at page render
    and for the lazy /<camera>/timelapse-day endpoint. Clicks go to the
    advanced player at /<camera>/player?key=...; the wiring JS reads the
    camera prefix from data-key, so no need to thread camera_name through
    here. presign kept as optional for back-compat.

    When camera is provided, also renders a sightings strip (bird/ufo
    crops detected by starcam_debird.py) underneath the buttons."""
    btns = []
    date_str = f"{y}-{m}-{dd}"
    if day["day_key"]:
        btns.append(
            f'<button class="vbtn primary" data-key="{day["day_key"]}" '
            f'data-label="{date_str} whole day">▶ Whole day</button>')
    for hh, k in day["hourly"]:
        btns.append(
            f'<button class="vbtn" data-key="{k}" '
            f'data-label="{date_str} {hh}">{hh}</button>')

    strip = _render_sightings_strip(y, m, dd, camera) if camera else ""

    return (f'<div class="day-card"><div class="day-label">{date_str}</div>'
            f'<div class="btn-row">{"".join(btns)}</div>'
            f'{strip}</div>')


def _render_sightings_strip(y, m, dd, camera):
    """Fetch any sighting crops for this day from S3 and render them as a
    thumbnail strip under the hour buttons. Empty string if no sightings."""
    cfg = _CAMERA_CONFIGS.get(camera)
    if not cfg:
        return ""
    bucket = cfg["bucket"]
    prefix = f"sightings/{y}/{m}/{dd}/"

    import boto3
    s3 = boto3.client("s3", region_name="eu-west-1")
    paginator = s3.get_paginator("list_objects_v2")
    manifests = []
    crops = {}
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if k.endswith("/index.json"):
                    manifests.append(k)
                elif k.endswith(".jpg"):
                    crops[k.rsplit("/", 1)[-1]] = k
    except Exception:
        return ""

    sightings = []
    for mk in manifests:
        try:
            body = s3.get_object(Bucket=bucket, Key=mk)["Body"].read()
            for line in body.decode().splitlines():
                try:
                    sightings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except Exception:
            continue
    if not sightings:
        return ""

    # Group sightings by source frame (epoch_ms). One tile per frame
    # uses the *composite* image we write alongside the per-sighting
    # crops — shows every trigger on that frame painted at its real
    # bbox so you can see spatial relationships at a glance.
    by_frame: dict[int, list[dict]] = {}
    for s in sightings:
        by_frame.setdefault(s["epoch_ms"], []).append(s)

    # Sort frames by daily index ascending (read L→R in time).
    def _daily_idx(group):
        return group[0].get("daily_frame_idx", 0)
    grouped = sorted(by_frame.values(), key=_daily_idx)

    tiles = []
    for group in grouped:
        epoch_ms = group[0]["epoch_ms"]
        composite_name = f"{epoch_ms}_composite.jpg"
        composite_key = crops.get(composite_name)
        if not composite_key:
            continue
        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": composite_key},
                ExpiresIn=3600,
            )
        except Exception:
            continue
        # Pick the most prominent sighting on this frame to represent it
        # in the title / evidence-pack click target.
        rep = max(group, key=lambda s: s.get("dark_delta", 0))
        hour_mp4 = rep.get("hour_mp4", "?")
        h_idx = rep.get("hour_frame_idx")
        d_idx = rep.get("daily_frame_idx", "?")
        n = len(group)
        max_dark = max(s.get("dark_delta", 0) for s in group)
        total_area = sum(s.get("area", 0) for s in group)

        # Click target: the puppy-sightings viewer (LAN-only). Evidence
        # packs live on puppy's local disk and are served by
        # ~/super/services/puppy_sightings.py over plain HTTP — this is
        # diagnostic data so home-network-only is by design.
        # Note: browsers may flag the http→ link from this HTTPS page as
        # mixed-content on first click; that's acceptable for the LAN
        # diagnostic surface.
        href = None
        if hour_mp4 != "?":
            try:
                hh = hour_mp4.rsplit("_", 1)[1].split(".", 1)[0]
                sid = f"{rep['epoch_ms']}_{rep['cx']}_{rep['cy']}"
                href = (f"http://192.168.4.138:8910/sighting"
                        f"?date={y}-{m}-{dd}&hour={hh}&id={sid}")
            except Exception:
                href = None

        label = f"{hour_mp4} f{h_idx}" + (f" ×{n}" if n > 1 else "")
        title = (f"daily f{d_idx} · {hour_mp4} f{h_idx} · "
                 f"{n} trigger(s) · area={total_area} dark={max_dark}")

        tile = (f'<figure class="sight-tile">'
                f'<img class="sight" src="{url}" title="{title}" alt="{title}">'
                f'<figcaption class="sight-label">{label}</figcaption>'
                f'</figure>')
        if href:
            tile = f'<a class="sight-link" href="{href}">{tile}</a>'
        tiles.append(tile)

    if not tiles:
        return ""
    return ('<div class="sightings-strip">'
            f'<div class="sightings-label">Sightings ({len(tiles)})</div>'
            f'<div class="sightings-tiles">{"".join(tiles)}</div>'
            '</div>')



def _render_calendars_html(tree, today_ymd, yesterday_ymd):
    """Render `cal`-style month grids for every month with content, newest first.
    Clickable cells are days with content (excluding today/yesterday which
    render as eager cards). Today/yesterday cells are highlighted but not
    clickable in the calendar (you're already looking at them)."""
    import calendar as _cal
    out = []
    years_sorted = sorted(tree.keys(), reverse=True)
    for y in years_sorted:
        months = tree[y]
        for m in sorted(months.keys(), reverse=True):
            days = months[m]
            yi, mi = int(y), int(m)
            cal = _cal.Calendar(firstweekday=6)  # Sunday-first to match `cal`
            weeks = cal.monthdayscalendar(yi, mi)
            rows = []
            for wk in weeks:
                cells = []
                for d in wk:
                    if d == 0:
                        cells.append('<td class="cal-empty"></td>')
                        continue
                    dd = f"{d:02d}"
                    date_str = f"{y}-{m}-{dd}"
                    has = dd in days
                    is_today = (y, m, dd) == today_ymd
                    is_yest  = (y, m, dd) == yesterday_ymd
                    classes = ["cal-day"]
                    if not has: classes.append("cal-none")
                    if is_today: classes.append("cal-today")
                    if is_yest:  classes.append("cal-yest")
                    if has and not is_today and not is_yest:
                        classes.append("cal-clickable")
                        cells.append(f'<td class="{" ".join(classes)}" '
                                     f'data-date="{date_str}">{d}</td>')
                    else:
                        cells.append(f'<td class="{" ".join(classes)}">{d}</td>')
                rows.append(f"<tr>{''.join(cells)}</tr>")
            out.append(
                f'<table class="cal">'
                f'<caption>{_MONTH_NAMES[mi]} {y}</caption>'
                f'<thead><tr>'
                f'<th>Su</th><th>Mo</th><th>Tu</th><th>We</th>'
                f'<th>Th</th><th>Fr</th><th>Sa</th>'
                f'</tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table>')
    return "".join(out)


_CAMERA_CONFIGS = {
    "skycam": {
        "title": "Skycam Timelapse",
        "bucket": "gardencam-berrylands-eu-west-1",
        "video_prefix": "skycam/videos/",
        "rerender_prefix": "skycam/rerender/",
        "back_label": "← Skycam",
        "back_url": "/skycam",
    },
    "starcam": {
        "title": "Starcam Timelapse",
        "bucket": "starcam-berrylands-eu-west-1",
        "video_prefix": "videos/",
        "rerender_prefix": None,
        "back_label": "← Starcam",
        "back_url": "/starcam",
    },
}


def render_timelapse_index(focus_date=None, camera="skycam"):
    """Default: today + yesterday eager, older months as cal-style grids.
    If focus_date='YYYY-MM-DD', show focus_date + previous-day pair instead."""
    from datetime import datetime, timezone, timedelta
    cfg = _CAMERA_CONFIGS[camera]
    tree = _list_video_tree(
        bucket=cfg["bucket"],
        video_prefix=cfg["video_prefix"],
        rerender_prefix=cfg["rerender_prefix"],
    )

    today_dt = datetime.now(timezone.utc)
    if focus_date:
        try:
            anchor = datetime.strptime(focus_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            anchor = today_dt
    else:
        anchor = today_dt
    prev_dt = anchor - timedelta(days=1)

    def _ymd(dt):
        return (dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d"))

    anchor_ymd = _ymd(anchor)
    prev_ymd   = _ymd(prev_dt)
    today_ymd  = _ymd(today_dt)
    yesterday_ymd = _ymd(today_dt - timedelta(days=1))

    eager_cards = []
    for (y, m, dd) in (anchor_ymd, prev_ymd):
        day = tree.get(y, {}).get(m, {}).get(dd)
        if day is not None:
            eager_cards.append(_render_day_card(y, m, dd, day, camera=camera))

    eager_html = "".join(eager_cards) or (
        '<p style="text-align:center;color:#8E8E93">'
        'No videos for the selected day(s).</p>')

    calendars_html = _render_calendars_html(tree, today_ymd, yesterday_ymd)

    tl_tag = _build_tag(_GC_VERSION, _GC_COMMIT, _GC_COMMIT_TIME)
    is_focused = focus_date is not None
    reset_link = (
        f'<a href="/{camera}/timelapse" class="reset-link">↻ Back to today</a>'
        if is_focused else '')

    return f'''<!doctype html><html><head><meta charset="utf-8">
<title>{cfg["title"]}</title>
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
  .reset-link {{ display:inline-block; margin:0.5rem auto; padding:0.4rem 0.8rem;
    background:#161616; border:1px solid #2C2C2E; border-radius:8px;
    color:#007AFF; font-size:0.9rem; }}
  .day-card {{ background:#161616; border-radius:12px; padding:1rem;
    margin:0.5rem auto; max-width:1200px; }}
  .day-label {{ color:#8E8E93; font-size:0.9rem; margin-bottom:0.5rem; }}
  .btn-row {{ display:flex; flex-wrap:wrap; gap:0.4rem; }}
  .vbtn {{ background:#2C2C2E; color:#E0E0E0; border:none;
    border-radius:8px; padding:0.5rem 0.8rem; font:inherit; font-size:0.9rem;
    cursor:pointer; }}
  .vbtn.primary {{ background:#007AFF; color:#fff; }}
  .vbtn:hover {{ background:#3a3a3c; }}
  .vbtn.primary:hover {{ background:#0a84ff; }}
  .vbtn.active {{ outline:2px solid #007AFF; }}
  .sightings-strip {{ margin-top:0.8rem; padding-top:0.6rem;
    border-top:1px solid #2C2C2E; }}
  .sightings-label {{ color:#8E8E93; font-size:0.8rem;
    margin-bottom:0.4rem; }}
  .sightings-tiles {{ display:flex; flex-wrap:wrap; gap:0.6rem; }}
  .sight-link {{ display:inline-block; text-decoration:none; }}
  .sight-tile {{ margin:0; display:flex; flex-direction:column;
    align-items:center; gap:2px; }}
  .sight {{ height:64px; width:auto; border-radius:6px;
    background:#000; display:block; }}
  .sight-link:hover .sight {{ outline:2px solid #007AFF; }}
  .sight-label {{ color:#8E8E93; font-size:0.7rem;
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    white-space:nowrap; }}
  .sight-link:hover .sight-label {{ color:#007AFF; }}
  #cards {{ margin-bottom:1.5rem; }}
  #cals {{ max-width:1200px; margin:0 auto; display:flex; flex-wrap:wrap;
    gap:1rem; justify-content:center; }}
  table.cal {{ background:#161616; border-radius:12px; padding:0.75rem 1rem;
    border-collapse:separate; border-spacing:2px; font-variant-numeric:tabular-nums; }}
  table.cal caption {{ color:#E0E0E0; font-size:0.95rem; font-weight:600;
    padding-bottom:0.4rem; caption-side:top; }}
  table.cal th {{ color:#8E8E93; font-weight:400; font-size:0.75rem;
    padding:2px 6px; text-align:center; }}
  table.cal td {{ text-align:center; padding:6px 8px; min-width:1.8em;
    font-size:0.85rem; color:#E0E0E0; }}
  table.cal td.cal-none {{ color:#3a3a3c; }}
  table.cal td.cal-clickable {{ cursor:pointer; background:#2C2C2E;
    border-radius:6px; }}
  table.cal td.cal-clickable:hover {{ background:#007AFF; color:#fff; }}
  table.cal td.cal-today {{ outline:2px solid #007AFF; border-radius:6px;
    color:#007AFF; font-weight:600; }}
  table.cal td.cal-yest {{ outline:1px solid #007AFF; border-radius:6px;
    color:#E0E0E0; }}
  table.cal td.cal-empty {{ color:transparent; }}
</style></head><body>
<div class="nav"><a href="{cfg["back_url"]}">{cfg["back_label"]}</a> · <a href="/contents">Home</a></div>
<div class="tag">{tl_tag}</div>
<div style="text-align:center;">{reset_link}</div>
<div id="cards">{eager_html}</div>
<div id="cals">{calendars_html}</div>
<script>
  function wireButtons(root) {{
    root.querySelectorAll('.vbtn').forEach(b => {{
      if (b.dataset.wired) return;
      b.dataset.wired = '1';
      b.addEventListener('click', () => {{
        if (!b.dataset.key) return;
        const url = '/{camera}/player?key=' + encodeURIComponent(b.dataset.key);
        window.open(url, '_blank');
      }});
    }});
  }}
  wireButtons(document);

  // Calendar day click → fetch that day + previous, replace #cards.
  document.querySelectorAll('table.cal td.cal-clickable').forEach(td => {{
    td.addEventListener('click', async () => {{
      const date = td.dataset.date;
      const cards = document.getElementById('cards');
      cards.innerHTML = '<p style="text-align:center;color:#8E8E93">Loading…</p>';
      try {{
        const resp = await fetch('/{camera}/timelapse-day?date=' + encodeURIComponent(date));
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        cards.innerHTML = await resp.text();
        wireButtons(cards);
        history.pushState({{date}}, '', '/{camera}/timelapse?date=' + encodeURIComponent(date));
        cards.scrollIntoView({{behavior:'smooth', block:'start'}});
      }} catch (e) {{
        cards.innerHTML = '<p style="text-align:center;color:#FF3B30">Load failed: ' + e + '</p>';
      }}
    }});
  }});
</script>
</body></html>'''


def render_timelapse_day_fragment(date_str, camera="skycam"):
    """Return HTML fragment of <date_str> + previous-day cards.
    Used by the calendar's click handler to lazy-load day pairs."""
    from datetime import datetime, timezone, timedelta
    try:
        anchor = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    prev = anchor - timedelta(days=1)
    cfg = _CAMERA_CONFIGS[camera]
    tree = _list_video_tree(
        bucket=cfg["bucket"],
        video_prefix=cfg["video_prefix"],
        rerender_prefix=cfg["rerender_prefix"],
    )
    cards = []
    for dt in (anchor, prev):
        y, m, dd = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
        day = tree.get(y, {}).get(m, {}).get(dd)
        if day is not None:
            cards.append(_render_day_card(y, m, dd, day, camera=camera))
    return "".join(cards) or (
        '<p style="text-align:center;color:#8E8E93">No videos for this day.</p>')


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


def render_skycam_player(key, in_sec=None, out_sec=None, src=None, srcs=None, clips=None):
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
        if ".." in key:
            return None
        # Key shape -> bucket. Skycam keys all live under skycam/ in the
        # shared gardencam bucket; starcam has its own bucket with no
        # camera-name prefix (just videos/ or rerender/).
        if key.startswith("skycam/"):
            bucket = "gardencam-berrylands-eu-west-1"
        elif key.startswith("videos/") or key.startswith("rerender/"):
            bucket = "starcam-berrylands-eu-west-1"
        else:
            return None
        s3 = boto3.client("s3", region_name="eu-west-1")
        try:
            url = s3.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
        except Exception:
            return None
        sources.append((url, key.rsplit("/", 1)[-1]))

    video_url, title = sources[0]
    # Build initial clips list: prefer `clips` (new), fall back to in/out (legacy).
    clip_list = []
    if clips:
        for pair in clips:
            try:
                a, b = pair
                a = float(a); b = float(b)
                if a < b: clip_list.append((a, b))
            except (TypeError, ValueError):
                continue
    elif in_sec is not None or out_sec is not None:
        # legacy: single clip from ?in&out (either may be omitted)
        a = float(in_sec)  if in_sec  is not None else 0.0
        b = float(out_sec) if out_sec is not None else None
        clip_list.append((a, b))
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
    clips_json = _json.dumps([{"in": a, "out": b} for (a, b) in clip_list])

    return f'''<!doctype html>
<html lang="en"><head>
{_THEME_CSS_JS}
<title>Sky Camera — {title}</title>
<style>
  body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
  .top {{ display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem; }}
  .top a {{ color: var(--accent); text-decoration: none; }}
  .filename {{ color: var(--text-secondary); font-size: 0.9rem; }}
  video {{ width: 100%; max-width: 1200px; display: block; margin: 0 auto; background: #000; }}
  .controls {{ max-width: 1200px; margin: 0.75rem auto; display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; justify-content: center; }}
  button, .btn {{ font: inherit; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; padding: 0.4rem 0.8rem; cursor: pointer; }}
  button:hover {{ opacity: 0.8; }}
  button.active {{ background: var(--accent); color: white; }}
  .scrub {{ max-width: 1200px; margin: 0.5rem auto; position: relative; height: 40px; }}
  .bar {{ position: absolute; top: 16px; left: 0; right: 0; height: 8px; background: var(--divider); border-radius: 4px; cursor: pointer; }}
  .play-region {{ position: absolute; top: 16px; height: 8px; background: var(--accent); opacity: 0.4; border-radius: 4px; pointer-events: none; }}
  .clip-band {{ position: absolute; height: 8px; background: var(--accent); opacity: 0.18; border-radius: 4px; }}
  .clip-band.active {{ opacity: 0.55; }}
  .clip-mark {{ position: absolute; width: 2px; height: 24px; background: var(--accent); opacity: 0.4; }}
  .clip-mark.active {{ opacity: 1; }}
  .scrub {{ touch-action: none; }}
  select.ctl, .menu {{ font: inherit; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; padding: 0.4rem 0.8rem; cursor: pointer; }}
  .menu-wrap {{ position: relative; display: inline-block; }}
  .menu-pop {{ display: none; position: absolute; right: 0; top: 100%; margin-top: 4px; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; min-width: 180px; z-index: 20; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}
  .menu-pop.open {{ display: block; }}
  .menu-pop button {{ display: block; width: 100%; text-align: left; border: none; background: transparent; padding: 0.5rem 0.8rem; color: var(--text); border-radius: 0; }}
  .menu-pop button:hover {{ background: var(--divider); }}
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
  <div style="position:relative; max-width:1200px; margin:0 auto; overflow:hidden;">
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
    <div id="clipBands" style="position:absolute; top:16px; left:0; right:0;
         height:8px; pointer-events:none;"></div>
    <div id="clipMarkers" style="position:absolute; top:8px; left:0; right:0;
         height:24px; pointer-events:none;"></div>
    <div class="head" id="head"></div>
  </div>
  <div class="controls">
    <select id="clipsSel" class="ctl" title="clips"></select>
    <button id="clipAdd" title="new clip from playhead">+</button>
    <button id="clipDel" title="delete clip containing playhead">−</button>
    <button id="play" title="play / pause" style="min-width:3rem;">▶</button>
    <span class="time" id="time">0.000 / 0.000</span>
    <select id="loopSel" class="ctl" title="loop mode">
      <option value="fwd-once">→</option>
      <option value="fwd-loop" selected>↻</option>
      <option value="pingpong">↔</option>
      <option value="rev-once">←</option>
      <option value="rev-loop">↺</option>
      <option value="all-loop">↻↻</option>
      <option value="all-pingpong">↔↔</option>
    </select>
    <select id="speedSel" class="ctl" title="speed">
      <option value="0.25">¼×</option>
      <option value="0.5">½×</option>
      <option value="1" selected>1×</option>
      <option value="2">2×</option>
      <option value="4">4×</option>
    </select>
    <span class="menu-wrap">
      <button id="actionsBtn" class="menu" title="more">⋯</button>
      <div id="actionsPop" class="menu-pop">
        <button id="share">Share clip URL</button>
        <button id="fs">Fullscreen</button>
        <button id="pip" style="display:none;">Picture-in-picture</button>
        <button id="airplay" style="display:none;">AirPlay</button>
        <button id="cast" style="display:none;">Cast (Chromecast)</button>
        <button id="dl">Download</button>
      </div>
    </span>
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
  <div class="help">press H for help · space play/pause</div>
  <div id="helpHud" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.85); z-index:50; padding:2rem; overflow:auto;">
    <div style="max-width:600px; margin:0 auto; color:var(--text); font-size:0.95rem;">
      <h2 style="color:var(--accent); margin-top:0;">Keyboard shortcuts</h2>
      <table style="width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums;">
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">space</td><td>play / pause</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">, .</td><td>play backward · play forward (transport)</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">← →</td><td>step one frame</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">p P</td><td>pace slower · faster (¼× ½× 1× 2× 4×)</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">m</td><td>cycle loop mode</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">↑ ↓</td><td>switch source (cycle)</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">0 1 2</td><td>zoom: fit · 1× · 2× (zooms toward the mouse)</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">3 4</td><td>brightness down · up (hold to ramp)</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">[ ]</td><td>set in / out of active clip</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">+ −</td><td>add clip at playhead · delete clip containing playhead</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">F</td><td>fullscreen</td></tr>
        <tr><td style="padding:0.3rem 0.8rem; color:var(--accent);">H / Esc</td><td>this help / close</td></tr>
      </table>
      <p style="color:var(--text-secondary); margin-top:1.5rem;">
        Click timeline to seek · drag the playhead to scrub
      </p>
    </div>
  </div>
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
<script>
(function() {{
  const v = document.getElementById("v");
  const head = document.getElementById("head");
  const bar  = document.getElementById("bar");
  const bandsEl = document.getElementById("clipBands");
  const marksEl = document.getElementById("clipMarkers");
  const timeEl = document.getElementById("time");
  // Default matches what we produce (image2 @ 60 fps for every hour
  // and day mp4 on both starcam and skycam). The rVFC probe below
  // refines this *if* the user plays the video, but until then 60 is
  // the right answer for any of our keys. Defaulting to 30 caused
  // arrow-key stepping to advance by 2 source frames at a time when
  // the user opened the player and immediately pressed an arrow
  // without playing first.
  //
  // NEVER use getVideoPlaybackQuality().totalVideoFrames here — that's
  // a running count of frames rendered so far, not a per-file frame
  // count.
  let FPS = 60;
  const hasRVFC = 'requestVideoFrameCallback' in HTMLVideoElement.prototype;
  if (hasRVFC) {{
    const samples = [];
    let lastMediaTime = null;
    const probe = (now, meta) => {{
      const t = meta.mediaTime;
      // Only sample during natural playback. Skip if seeking, paused, or
      // if the dt is too big to plausibly be one frame (catches frames
      // presented immediately after a seek). 0.003 s = 333 fps; 0.07 s
      // = 14 fps. Inside that band, the median is the per-file frame
      // duration. Refines continuously: every natural-playback frame
      // adds a sample, FPS updates on each one once we have >=12.
      const dt = lastMediaTime === null ? 0 : t - lastMediaTime;
      lastMediaTime = t;
      const playingNaturally = !v.seeking && !v.paused;
      if (playingNaturally && dt > 0.003 && dt < 0.07) {{
        samples.push(dt);
        if (samples.length > 60) samples.shift();
        if (samples.length >= 12) {{
          const sorted = samples.slice().sort((a, b) => a - b);
          const median = sorted[sorted.length >> 1];
          const f = 1 / median;
          if (f > 1 && f < 240) FPS = Math.round(f);
        }}
      }}
      v.requestVideoFrameCallback(probe);
    }};
    v.requestVideoFrameCallback(probe);
    // rVFC only fires while frames are being presented. The probe
    // refines FPS within ~12 frames of natural playback in case the
    // source isn't actually 60 fps; the 60 default above means
    // stepping is correct from the very first arrow-key press for our
    // standard output.
  }}

  function stepFrame(direction) {{
    pause();
    const step = 1 / FPS;
    const t = direction > 0
      ? Math.min(hi(), v.currentTime + step)
      : Math.max(lo(), v.currentTime - step);
    v.currentTime = t;
    // requestVideoFrameCallback fires after the seek's new frame is
    // composited — repaint then so HUD reflects the displayed frame,
    // not the requested time.
    if (hasRVFC) v.requestVideoFrameCallback(() => repaint());
    else repaint();
  }}
  let dir = 1;       // +1 fwd, -1 reverse
  let speed = 1.0;
  // loopMode: 'fwd-once' | 'fwd-loop' | 'pingpong' | 'rev-once' | 'rev-loop'
  // Default per design/splay-and-player-conventions.md = loop.
  //         | 'all-loop' | 'all-pingpong'
  let loopMode = "fwd-loop";
  let rafId = null;
  let lastTs = null;

  const SOURCES = {sources_json};
  let curIdx = 0;

  // Clips: array of {{in, out}}. Active clip drives the in/out used by
  // playback. 'all-*' modes iterate through all clips.
  let CLIPS = {clips_json};
  let activeClip = CLIPS.length > 0 ? 0 : -1;

  function modeDir(mode) {{
    if (mode === "fwd-once" || mode === "fwd-loop" || mode === "all-loop") return 1;
    if (mode === "rev-once" || mode === "rev-loop") return -1;
    return 0; // pingpong: keep current dir
  }}
  function isAllMode(m) {{ return m === "all-loop" || m === "all-pingpong"; }}

  function dur() {{ return v.duration || 0; }}
  function clip(i) {{ return CLIPS[i]; }}
  function loOf(c) {{ return c ? c.in  : 0; }}
  function hiOf(c) {{ return c ? (c.out != null ? c.out : dur()) : dur(); }}
  function lo() {{ return loOf(clip(activeClip)); }}
  function hi() {{ return hiOf(clip(activeClip)); }}

  function fmt(t) {{ if (!isFinite(t)) return "—"; return t.toFixed(3) + "s"; }}
  function repaint() {{
    const D = dur(); if (!D) return;
    head.style.left = (v.currentTime / D * 100) + "%";
    // Render all clip bands + markers.
    bandsEl.innerHTML = "";
    marksEl.innerHTML = "";
    CLIPS.forEach((c, i) => {{
      const a = loOf(c), b = hiOf(c);
      const left = (a / D * 100), width = ((b - a) / D * 100);
      const band = document.createElement("div");
      band.className = "clip-band" + (i === activeClip ? " active" : "");
      band.style.left  = left + "%";
      band.style.width = width + "%";
      bandsEl.appendChild(band);
      const m1 = document.createElement("div");
      m1.className = "clip-mark" + (i === activeClip ? " active" : "");
      m1.style.left = left + "%";
      marksEl.appendChild(m1);
      const m2 = document.createElement("div");
      m2.className = "clip-mark" + (i === activeClip ? " active" : "");
      m2.style.left = ((b / D) * 100) + "%";
      marksEl.appendChild(m2);
    }});
    timeEl.textContent = fmt(v.currentTime) + " / " + fmt(D);
  }}

  function rebuildClipsDropdown() {{
    const sel = document.getElementById("clipsSel");
    sel.innerHTML = "";
    if (CLIPS.length === 0) {{
      const o = document.createElement("option");
      o.value = "-1"; o.textContent = "no clips";
      sel.appendChild(o);
      sel.value = "-1";
    }} else {{
      CLIPS.forEach((c, i) => {{
        const o = document.createElement("option");
        o.value = String(i);
        o.textContent = `clip ${{i + 1}}: ${{loOf(c).toFixed(2)}}–${{hiOf(c).toFixed(2)}}s`;
        sel.appendChild(o);
      }});
      sel.value = String(activeClip);
    }}
  }}

  // Forward play uses the native <video> element. Reverse uses a JS
  // frame-stepper since browsers don't support negative playbackRate for
  // compressed video. There's exactly one playing-state at a time.
  let playing = false;
  const playBtn = document.getElementById("play");

  function setPlayGlyph() {{ playBtn.textContent = playing ? "❚❚" : "▶"; }}

  function isLoopMode(m) {{ return m === "fwd-loop" || m === "rev-loop"; }}
  function isOnceMode(m) {{ return m === "fwd-once" || m === "rev-once"; }}

  function reverseStep(ts) {{
    if (lastTs == null) lastTs = ts;
    const dt = (ts - lastTs) / 1000;
    lastTs = ts;
    let t = v.currentTime - speed * dt;
    if (t <= lo()) {{
      if (loopMode === "pingpong" || loopMode === "all-pingpong") {{
        if (loopMode === "all-pingpong" && CLIPS.length > 1 && activeClip > 0) {{
          jumpToClip(activeClip - 1);
          rafId = requestAnimationFrame(reverseStep);
          return;
        }}
        v.currentTime = lo(); pause(); playForward(); return;
      }}
      else if (loopMode === "rev-loop") {{ t = hi(); }}
      else if (loopMode === "all-loop") {{
        if (CLIPS.length > 0) {{
          const next = (activeClip - 1 + CLIPS.length) % CLIPS.length;
          jumpToClip(next);
          rafId = requestAnimationFrame(reverseStep);
          return;
        }} else {{ t = hi(); }}
      }}
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
    setPlayGlyph();
  }}
  function playReverse() {{
    pause();
    dir = -1;
    if (v.currentTime <= lo() + 0.001) v.currentTime = hi();
    lastTs = null;
    rafId = requestAnimationFrame(reverseStep);
    playing = true;
    setPlayGlyph();
  }}
  function pause() {{
    v.pause();
    if (rafId != null) {{ cancelAnimationFrame(rafId); rafId = null; }}
    lastTs = null;
    playing = false;
    setPlayGlyph();
  }}
  function playInModeDirection() {{
    const d = modeDir(loopMode);
    if (d === -1) playReverse();
    else if (d === 1) playForward();
    else (dir < 0 ? playReverse() : playForward());
  }}
  function toggle() {{
    if (playing) pause();
    else playInModeDirection();
  }}

  playBtn.onclick = toggle;

  const speedSel = document.getElementById("speedSel");
  speedSel.onchange = () => {{
    speed = parseFloat(speedSel.value);
    if (playing && dir > 0) v.playbackRate = speed;
    speedSel.blur();  // return focus to body so keybindings fire
  }};

  const loopSel = document.getElementById("loopSel");
  loopSel.onchange = () => {{
    loopMode = loopSel.value;
    // Apply direction immediately if playing.
    if (playing) {{
      const want = modeDir(loopMode);
      if (want === 1 && dir < 0) playForward();
      else if (want === -1 && dir > 0) playReverse();
    }}
    loopSel.blur();  // return focus to body so keybindings fire
  }};

  // Clip operations.
  function setActiveClip(i) {{
    if (i < 0 || i >= CLIPS.length) {{ activeClip = -1; rebuildClipsDropdown(); repaint(); return; }}
    activeClip = i;
    const c = CLIPS[i];
    if (v.currentTime < c.in || v.currentTime > hiOf(c)) v.currentTime = c.in;
    rebuildClipsDropdown(); repaint();
  }}
  function addClipAtPlayhead() {{
    const D = dur(); if (!D) return;
    const a = Math.max(0, v.currentTime - 0.5);
    const b = Math.min(D, v.currentTime + 0.5);
    CLIPS.push({{in: a, out: b}});
    activeClip = CLIPS.length - 1;
    rebuildClipsDropdown(); repaint();
  }}
  function delClipContainingPlayhead() {{
    const t = v.currentTime;
    const idx = CLIPS.findIndex(c => t >= loOf(c) && t <= hiOf(c));
    if (idx < 0) return;
    CLIPS.splice(idx, 1);
    if (CLIPS.length === 0) activeClip = -1;
    else if (activeClip >= CLIPS.length) activeClip = CLIPS.length - 1;
    rebuildClipsDropdown(); repaint();
  }}
  function setActiveClipIn(t)  {{ if (activeClip < 0) return; CLIPS[activeClip].in  = Math.min(t, hiOf(CLIPS[activeClip])); rebuildClipsDropdown(); repaint(); }}
  function setActiveClipOut(t) {{ if (activeClip < 0) return; CLIPS[activeClip].out = Math.max(t, loOf(CLIPS[activeClip])); rebuildClipsDropdown(); repaint(); }}

  document.getElementById("clipAdd").onclick = addClipAtPlayhead;
  document.getElementById("clipDel").onclick = delClipContainingPlayhead;
  document.getElementById("clipsSel").onchange = (e) => {{
    setActiveClip(parseInt(e.target.value, 10));
    e.target.blur();  // return focus to body so keybindings fire
  }};

  function cycleLoopMode() {{
    const order = ["fwd-once","fwd-loop","pingpong","rev-once","rev-loop","all-loop","all-pingpong"];
    const i = order.indexOf(loopMode);
    loopMode = order[(i + 1) % order.length];
    loopSel.value = loopMode;
    loopSel.onchange();
  }}

  document.getElementById("share").onclick = () => {{
    const u = new URL(location.href);
    u.searchParams.delete("in");
    u.searchParams.delete("out");
    if (CLIPS.length === 0) {{
      u.searchParams.delete("clip");
    }} else {{
      u.searchParams.delete("clip");
      // Encode each clip as in-out (comma-joined). API Gateway preserves
      // repeated params so we serialise as one comma-list.
      const enc = CLIPS.map(c => `${{loOf(c).toFixed(3)}}-${{hiOf(c).toFixed(3)}}`).join(",");
      u.searchParams.set("clip", enc);
    }}
    history.replaceState(null, "", u);
    navigator.clipboard?.writeText(u.toString());
    const share = document.getElementById("share");
    const orig = share.textContent;
    share.textContent = "copied";
    setTimeout(() => share.textContent = orig, 1200);
  }};

  // Timeline: click to seek; drag the bar to scrub.
  // Throttled via rAF — pointermove fires hundreds of times/sec on a
  // fast trackpad, and every currentTime= triggers a fresh decode.
  // We coalesce to at most one seek per animation frame, using
  // fastSeek() where the browser offers it (Firefox; Chrome ignores
  // harmlessly) so the seek lands on the nearest keyframe during drag.
  let scrubbing = false;
  let pendingX = null, rafSeek = null;
  function applyPendingSeek() {{
    rafSeek = null;
    if (pendingX == null) return;
    const r = bar.getBoundingClientRect();
    const t = (pendingX / r.width) * dur();
    pendingX = null;
    if (typeof v.fastSeek === "function") v.fastSeek(t);
    else v.currentTime = t;
    repaint();
  }}
  function queueSeek(e) {{
    const r = bar.getBoundingClientRect();
    pendingX = Math.max(0, Math.min(r.width, e.clientX - r.left));
    if (rafSeek == null) rafSeek = requestAnimationFrame(applyPendingSeek);
  }}
  bar.addEventListener("pointerdown", e => {{
    scrubbing = true; bar.setPointerCapture(e.pointerId); queueSeek(e);
  }});
  bar.addEventListener("pointermove", e => {{ if (scrubbing) queueSeek(e); }});
  bar.addEventListener("pointerup",   e => {{
    scrubbing = false; try {{ bar.releasePointerCapture(e.pointerId); }} catch(_){{}}
    // Final precise seek (not fastSeek) so the landing position is exact.
    if (pendingX != null) {{
      const r = bar.getBoundingClientRect();
      v.currentTime = (pendingX / r.width) * dur();
      pendingX = null; if (rafSeek != null) {{ cancelAnimationFrame(rafSeek); rafSeek = null; }}
      repaint();
    }}
  }});
  bar.addEventListener("pointercancel", () => {{ scrubbing = false; }});

  // Actions dropdown wiring.
  const actionsBtn = document.getElementById("actionsBtn");
  const actionsPop = document.getElementById("actionsPop");
  actionsBtn.onclick = (e) => {{
    e.stopPropagation();
    actionsPop.classList.toggle("open");
  }};
  document.addEventListener("click", e => {{
    if (!actionsPop.contains(e.target) && e.target !== actionsBtn) {{
      actionsPop.classList.remove("open");
    }}
  }});
  actionsPop.querySelectorAll("button").forEach(b => {{
    b.addEventListener("click", () => actionsPop.classList.remove("open"));
  }});

  const helpHud = document.getElementById("helpHud");
  function setHelp(open) {{ helpHud.style.display = open ? "block" : "none"; }}
  helpHud.addEventListener("click", () => setHelp(false));

  function nudgeSpeed(delta) {{
    const speeds = [0.25, 0.5, 1, 2, 4];
    const i = speeds.indexOf(speed);
    const j = Math.max(0, Math.min(speeds.length - 1, i + delta));
    if (j !== i) {{
      speed = speeds[j];
      speedSel.value = String(speed);
      if (playing && dir > 0) v.playbackRate = speed;
    }}
  }}

  // Zoom + brightness (Splay-aligned): 0 fit, 1 = 1:1, 2 = 2×.
  // 3 darker, 4 brighter (held = ramp). Zoom origin = mouse position
  // when the key is pressed; falls back to centre if pointer hasn't
  // entered the video yet.
  let mouseX = null, mouseY = null;  // last pointer pos over the video, in CSS px
  v.addEventListener("pointermove", e => {{
    const r = v.getBoundingClientRect();
    mouseX = e.clientX - r.left; mouseY = e.clientY - r.top;
  }});
  v.addEventListener("pointerleave", () => {{ mouseX = mouseY = null; }});

  let zoom = 1.0;       // 1.0 = fit; >1 = magnified
  let panX = 0, panY = 0;  // CSS translate in px (negative = pan up/left)
  let bright = 1.0;     // CSS filter: brightness multiplier
  function applyTransform() {{
    v.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{zoom}})`;
    v.style.transformOrigin = "0 0";
    v.style.filter = bright === 1.0 ? "" : `brightness(${{bright}})`;
  }}
  function setZoom(target, ox, oy) {{
    // target: "fit" | 1 | 2 — scale relative to fit. (CSS already
    // displays video at "fit" size; 1 here means "1×fit" not 1px=1px.
    // True 1:1 would need knowing the native size; defer.)
    const r = v.getBoundingClientRect();
    if (ox == null) {{ ox = r.width / 2; oy = r.height / 2; }}
    // Convert old viewport-relative origin to content space, then keep
    // that content point under (ox, oy) after the new zoom.
    const cx = (ox - panX) / zoom;
    const cy = (oy - panY) / zoom;
    if (target === "fit") {{ zoom = 1.0; panX = 0; panY = 0; }}
    else {{ zoom = target; panX = ox - cx * zoom; panY = oy - cy * zoom; }}
    applyTransform();
  }}
  function nudgeBright(delta) {{
    // Multiplicative steps so held-key ramp feels linear in stops.
    const factor = delta > 0 ? 1.15 : 1 / 1.15;
    bright = Math.max(0.05, Math.min(20.0, bright * factor));
    applyTransform();
  }}

  document.addEventListener("keydown", e => {{
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.key === "Escape") {{ setHelp(false); return; }}
    if (e.key === "h" || e.key === "H") {{ setHelp(helpHud.style.display === "none"); return; }}
    if (e.code === "Space") {{ e.preventDefault(); toggle(); }}
    else if (e.code === "ArrowLeft")  {{ stepFrame(-1); }}
    else if (e.code === "ArrowRight") {{ stepFrame(+1); }}
    // Transport (per design/splay-and-player-conventions.md):
    //   , play backward · . play forward
    //   p pace slower   · P pace faster
    //   m cycle loop mode (was 'l'; freed for stills mode in Splay)
    else if (e.key === ",") playReverse();
    else if (e.key === ".") playForward();
    else if (e.key === "p") nudgeSpeed(-1);
    else if (e.key === "P") nudgeSpeed(+1);
    else if (e.key === "m" || e.key === "M") cycleLoopMode();
    else if (e.key === "[") setActiveClipIn(v.currentTime);
    else if (e.key === "]") setActiveClipOut(v.currentTime);
    else if (e.key === "+" || e.key === "=") addClipAtPlayhead();
    else if (e.key === "-" || e.key === "_") delClipContainingPlayhead();
    else if (e.code === "ArrowUp")   {{ e.preventDefault(); swap(curIdx - 1); }}
    else if (e.code === "ArrowDown") {{ e.preventDefault(); swap(curIdx + 1); }}
    // Zoom + brightness (Splay convention, source jump dropped):
    //   0 fit · 1 = 1× (= fit) · 2 = 2× zoom · 3 darker · 4 brighter
    else if (e.key === "0") setZoom("fit", mouseX, mouseY);
    else if (e.key === "1") setZoom(1.0, mouseX, mouseY);
    else if (e.key === "2") setZoom(2.0, mouseX, mouseY);
    else if (e.key === "3") nudgeBright(-1);
    else if (e.key === "4") nudgeBright(+1);
    else if (e.key === "f" || e.key === "F") document.getElementById("fs").click();
  }});

  v.addEventListener("loadedmetadata", () => {{
    // Clamp clip times to [0, dur].
    const D = dur();
    CLIPS.forEach(c => {{
      c.in = Math.max(0, Math.min(D, c.in));
      c.out = Math.max(c.in, Math.min(D, c.out != null ? c.out : D));
    }});
    if (activeClip >= 0) v.currentTime = lo();
    rebuildClipsDropdown();
    repaint();
  }});

  function jumpToClip(i) {{
    if (i < 0 || i >= CLIPS.length) return;
    activeClip = i;
    rebuildClipsDropdown(); repaint();
    if (dir > 0) v.currentTime = lo();
    else v.currentTime = hi();
  }}

  // Enforce the out-marker / loop mode during native forward play.
  function enforceLoopAtEnd() {{
    if (loopMode === "pingpong" || loopMode === "all-pingpong") {{
      if (loopMode === "all-pingpong" && CLIPS.length > 1) {{
        if (activeClip < CLIPS.length - 1) {{ jumpToClip(activeClip + 1); }}
        else {{ v.currentTime = hi(); pause(); playReverse(); }}
      }} else {{
        v.currentTime = hi(); pause(); playReverse();
      }}
    }}
    else if (loopMode === "fwd-loop") {{
      v.currentTime = lo();
      if (v.paused) v.play().catch(() => {{}});
    }}
    else if (loopMode === "all-loop") {{
      const next = (activeClip + 1) % Math.max(1, CLIPS.length);
      if (CLIPS.length > 0) jumpToClip(next);
      else {{ v.currentTime = lo();
              if (v.paused) v.play().catch(() => {{}}); }}
    }}
    else {{ pause(); v.currentTime = hi(); }}
  }}
  v.addEventListener("timeupdate", () => {{
    repaint();
    if (playing && dir > 0 && v.currentTime >= hi() - 0.01) {{
      enforceLoopAtEnd();
    }}
  }});
  // Browser fires `ended` and pauses the <video> on natural EOF. If
  // timeupdate didn't catch the wrap first (it can lag), the video
  // sits paused with `playing` still true — the play glyph stays as
  // pause and nothing happens. Run the same loop logic from `ended`.
  v.addEventListener("ended", () => {{
    if (playing && dir > 0) enforceLoopAtEnd();
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

  // Chromecast via the Cast SDK. cast_sender.js calls __onGCastApiAvailable
  // once the framework is ready. Default media receiver app ID = CC1AD845.
  const castBtn = document.getElementById("cast");
  window.__onGCastApiAvailable = function(isAvailable) {{
    if (!isAvailable) return;
    try {{
      cast.framework.CastContext.getInstance().setOptions({{
        receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED,
      }});
      castBtn.style.display = "";
      castBtn.onclick = async () => {{
        const ctx = cast.framework.CastContext.getInstance();
        try {{
          await ctx.requestSession();
        }} catch (e) {{ /* user cancelled or no devices */ return; }}
        const session = ctx.getCurrentSession();
        if (!session) return;
        const cur = SOURCES[curIdx];
        const mediaInfo = new chrome.cast.media.MediaInfo(cur.url, "video/mp4");
        mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
        mediaInfo.metadata.title = cur.label || "gardencam";
        const request = new chrome.cast.media.LoadRequest(mediaInfo);
        request.currentTime = v.currentTime;
        await session.loadMedia(request);
      }};
    }} catch (e) {{ /* SDK loaded but Cast not supported */ }}
  }};
  // Download: open the source URL in a new tab. Cross-origin S3 ignores
  // the HTMLAnchorElement download attribute, so this is the cleanest path.
  function refreshDownload() {{}}
  document.getElementById("dl").onclick = () => {{
    const cur = SOURCES[curIdx];
    if (cur) window.open(cur.url, "_blank");
  }};

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

  rebuildClipsDropdown();
}})();
</script>
</body></html>'''


def render_gardencam_main(images, image_cards, poc_banner_html=""):
    """Render the /skycam landing page.

    Simplified 2026-05-20: dropped the 3-latest-images carousel (the
    stills were often hours stale and pushed everything else below the
    fold); dropped the Starcam link (starcam has its own landing page);
    promoted the advanced player to primary CTA.

    `images` and `image_cards` args kept for API compat with the caller;
    no longer used in the body.
    """
    return f'''\
{_THEME_CSS_JS}
            <title>Sky Camera</title>
            <style>
                body {{ font-family: var(--font); text-align: center; margin: 1rem;
                    background: var(--bg); color: var(--text); }}
                h1 {{ margin: 0.6rem 0; font-size: 1.4rem; }}
                .links {{ display: flex; flex-wrap: wrap; gap: 0.4rem;
                    justify-content: center; align-items: center;
                    max-width: 900px; margin: 0.4rem auto; }}
                .link {{ display: inline-block; padding: 0.35rem 0.9rem;
                    background: var(--card-bg); color: var(--accent);
                    text-decoration: none; border-radius: 8px;
                    border: 1px solid var(--divider); font-size: 0.9rem;
                    transition: opacity 0.2s; }}
                .link:hover {{ opacity: 0.8; }}
                .link.primary {{ background: var(--accent); color: white;
                    font-weight: 600; padding: 0.45rem 1.1rem; }}
                .link.secondary {{ opacity: 0.7; font-size: 0.82rem; }}
                button.link {{ cursor: pointer; font-family: inherit; }}
                #captureStatus {{ font-size: 0.85rem;
                    color: var(--text-secondary); margin-top: 0.3rem; }}
            </style>
            {build_skycam_top_bar()}
            <h1>Sky Camera</h1>
            <div class="links">
              <a href="/skycam/timelapse" class="link primary">▶ Advanced player</a>
              <a href="/skycam/videos" class="link">Videos</a>
              <a href="/skycam/clouds" class="link">☁ Clouds: The Movie</a>
            </div>
            {poc_banner_html}
            <div class="links">
              <a href="gardencam/stats" class="link secondary">Capture Stats</a>
              <a href="gardencam/s3-stats" class="link secondary">Storage Stats</a>
              <button id="captureBtn" class="link secondary">📷 Capture Now</button>
            </div>
            <div id="captureStatus"></div>
            <script>
            document.getElementById('captureBtn').addEventListener('click', function() {{
                const btn = this;
                const status = document.getElementById('captureStatus');
                btn.disabled = true;
                btn.textContent = '📷 Capturing...';
                status.textContent = 'Sending capture command...';

                fetch('gardencam/capture', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        status.textContent = data.message || 'Capture command sent! Image will appear in ~30 seconds.';
                        setTimeout(() => {{
                            btn.disabled = false;
                            btn.textContent = '📷 Capture Now';
                        }}, 3000);
                    }})
                    .catch(error => {{
                        status.textContent = 'Error: ' + error.message;
                        btn.disabled = false;
                        btn.textContent = '📷 Capture Now';
                    }});
            }});
            </script>'''


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
