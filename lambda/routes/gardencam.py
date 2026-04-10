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


def render_timelapse_index(total_videos, weekly_videos, daily_videos, latest_weekly, latest_daily):
    """Render the timelapse index page."""
    weekly_items = ''
    for video in latest_weekly:
        weekly_items += f'''
                <li>
                    <div>
                        <div class="video-title">Week of {video['start_date']}</div>
                        <div class="video-date">{video['start_date']} to {video['end_date']} &bull; {video['size_mb']:.1f} MB</div>
                    </div>
                    <a href="video?id={video['id']}" class="button">Watch</a>
                </li>
            '''

    daily_items = ''
    for video in latest_daily:
        daily_items += f'''
                <li>
                    <div>
                        <div class="video-title">{video['start_date']}</div>
                        <div class="video-date">{video['size_mb']:.1f} MB</div>
                    </div>
                    <a href="video?id={video['id']}" class="button">Watch</a>
                </li>
            '''

    return f'''
        <title>Timelapse Videos - Garden Camera</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .info-section {{ background: #2a2a2a; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
            .info-section h2 {{ margin-top: 0; color: #4a9eff; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }}
            .stat-box {{ background: #1a1a1a; padding: 1.5rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2.5rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .latest-videos {{ margin-top: 2rem; }}
            .video-list {{ list-style: none; padding: 0; }}
            .video-list li {{ background: #1a1a1a; padding: 1rem; margin: 0.5rem 0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }}
            .video-list li:hover {{ background: #252525; }}
            .video-title {{ color: #4a9eff; font-weight: bold; }}
            .video-date {{ color: #888; font-size: 0.9rem; }}
            .button {{ display: inline-block; padding: 0.75rem 1.5rem; background: #4a9eff; color: #fff; text-decoration: none; border-radius: 6px; margin: 0.5rem; }}
            .button:hover {{ background: #3a8eef; }}
            .button.secondary {{ background: #2a2a2a; }}
            .button.secondary:hover {{ background: #3a3a3a; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="videos">All Videos</a>
            <a href="timelapse/schedule">Schedule</a>
        </div>
        <div class="container">
            <h1>Garden Timelapse Videos</h1>

            <div class="info-section">
                <h2>Overview</h2>
                <p>Automated timelapse videos created from garden camera images:</p>
                <ul style="color: #aaa; margin: 1rem 0;">
                    <li><strong>Weekly:</strong> 7 days condensed, 24fps, ~5 seconds</li>
                    <li><strong>Daily:</strong> 24 hours, 12fps, all captures shown</li>
                </ul>

                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{total_videos}</div>
                        <div class="stat-label">Total Videos</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(weekly_videos)}</div>
                        <div class="stat-label">Weekly</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(daily_videos)}</div>
                        <div class="stat-label">Daily</div>
                    </div>
                </div>

                <div style="text-align: center; margin-top: 1.5rem;">
                    <a href="videos" class="button">View All Videos</a>
                    <a href="timelapse/schedule" class="button secondary">View Schedule</a>
                </div>
            </div>

            <div class="info-section latest-videos">
                <h2>Latest Weekly Videos</h2>
                <ul class="video-list">
        {weekly_items}
                </ul>
            </div>

            <div class="info-section latest-videos">
                <h2>Latest Daily Videos</h2>
                <ul class="video-list">
        {daily_items}
                </ul>
            </div>
        </div>
        '''


def render_video_player(start_formatted, end_formatted, presigned_url, frame_count, duration, size_mb):
    """Render the single video player page."""
    return f'''
            <meta charset="UTF-8">
            <title>Video: {start_formatted} to {end_formatted} - Garden Camera</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                .nav a:hover {{ background: #3a3a3a; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .video-container {{ background: #2a2a2a; border-radius: 8px; padding: 2rem; }}
                .video-container video {{ width: 100%; max-width: 1200px; display: block; margin: 0 auto; border-radius: 6px; background: #000; }}
                .video-info {{ margin-top: 2rem; padding: 1.5rem; background: #1a1a1a; border-radius: 6px; }}
                .video-info h2 {{ margin: 0 0 1rem 0; color: #4a9eff; }}
                .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }}
                .info-item {{ padding: 1rem; background: #2a2a2a; border-radius: 6px; }}
                .info-label {{ color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }}
                .info-value {{ font-size: 1.5rem; font-weight: bold; color: #4a9eff; }}
                .download-btn {{ display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #4a9eff; color: #fff; text-decoration: none; border-radius: 6px; font-size: 1rem; }}
                .download-btn:hover {{ background: #3a8eef; }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
                <a href="timelapse">Timelapse Index</a>
                <a href="videos">All Videos</a>
            </div>
            <div class="container">
                <div class="video-container">
                    <video controls loop autoplay preload="auto">
                        <source src="{presigned_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="video-info">
                        <h2>Week of {start_formatted} to {end_formatted}</h2>
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Frames</div>
                                <div class="info-value">{frame_count}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Duration</div>
                                <div class="info-value">{duration}s</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">File Size</div>
                                <div class="info-value">{size_mb:.1f} MB</div>
                            </div>
                        </div>
                        <a href="{presigned_url}" download class="download-btn">Download Video (MP4)</a>
                    </div>
                </div>
            </div>
            '''


def render_video_not_found(video_id):
    """Render the video not found error page."""
    return f'''
            <title>Video Not Found - Garden Camera</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .error {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
            </style>
            <div class="error">
                <h1>Video Not Found</h1>
                <p>The requested video "{video_id}" does not exist.</p>
                <p><a href="videos" style="color: #4a9eff;">View all videos</a></p>
            </div>
            '''


def render_video_error():
    """Render the video error page."""
    return '''
            <title>Error - Garden Camera</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
                .error { max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }
            </style>
            <div class="error">
                <h1>Error Loading Video</h1>
                <p>An error occurred while loading the video.</p>
                <p><a href="videos" style="color: #4a9eff;">View all videos</a></p>
            </div>
            '''


def _render_video_card(video, is_weekly=True):
    """Render a single video card for the gallery."""
    title = f"Week of {video['start_date']}" if is_weekly else video['start_date']
    date_line = f"<p>{video['start_date']} to {video['end_date']}</p>" if is_weekly else ""
    return f'''
                    <a href="video?id={video['id']}" class="video-card">
                        <div class="video-thumbnail">
                            <div class="play-icon"></div>
                        </div>
                        <div class="video-metadata">
                            <h3>{title}</h3>
                            {date_line}
                            <div class="video-stats">
                                <div class="stat">
                                    <span class="stat-value">{video['frame_count']}</span>
                                    <span class="stat-label">frames</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['duration']}s</span>
                                    <span class="stat-label">duration</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['size_mb']:.1f} MB</span>
                                    <span class="stat-label">size</span>
                                </div>
                            </div>
                        </div>
                    </a>
                    '''


def render_videos_gallery(weekly_videos, daily_videos, recent_videos=None):
    """Render the timelapse videos gallery page."""
    html = f'''
        <meta charset="UTF-8">
        <title>Timelapse Videos - Garden Camera</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .video-grid {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
            .video-card {{ background: #2a2a2a; border-radius: 8px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; text-decoration: none; display: block; color: inherit; }}
            .video-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 16px rgba(0,0,0,0.3); }}
            .video-thumbnail {{ width: 100%; height: 180px; background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); display: flex; align-items: center; justify-content: center; position: relative; }}
            .play-icon {{ width: 60px; height: 60px; background: rgba(74, 158, 255, 0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
            .play-icon::after {{ content: ''; width: 0; height: 0; border-style: solid; border-width: 12px 0 12px 20px; border-color: transparent transparent transparent #fff; margin-left: 4px; }}
            .video-metadata {{ padding: 1rem; }}
            .video-metadata h3 {{ margin: 0 0 0.75rem 0; color: #4a9eff; font-size: 1rem; }}
            .video-metadata p {{ margin: 0.25rem 0; color: #aaa; font-size: 0.85rem; }}
            .video-stats {{ display: flex; justify-content: space-between; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #3a3a3a; }}
            .stat {{ text-align: center; flex: 1; }}
            .stat-value {{ font-weight: bold; color: #4a9eff; display: block; }}
            .stat-label {{ font-size: 0.75rem; color: #666; }}
            .no-videos {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="timelapse">Timelapse Index</a>
            <a href="timelapse/schedule">Schedule</a>
            <a href="gallery">Gallery</a>
            <a href="stats">Capture Stats</a>
        </div>
        <h1>Timelapse Videos</h1>
        '''

    if recent_videos:
        cards = ''.join(f'''
            <div class="video-card" style="background:#1e2a1e;">
                <div class="video-thumbnail">
                    <a href="{v['url']}" style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;">
                        <div class="play-icon"></div>
                    </a>
                </div>
                <div class="video-metadata">
                    <h3>{v['label']}</h3>
                    <p>100 most recent frames</p>
                    <p style="color:#666;">{v['size_mb']:.1f} MB</p>
                </div>
            </div>''' for v in recent_videos)
        html += f'''
            <div style="max-width: 1400px; margin: 0 auto 3rem auto;">
                <h2 style="color: #4a9eff; margin-bottom: 1rem; padding-left: 0.5rem;">Recent (4-hourly) — {len(recent_videos)} videos</h2>
                <p style="color: #888; margin-bottom: 1.5rem; padding-left: 0.5rem;">Last 100 frames, generated every 4 hours</p>
                <div class="video-grid">{cards}</div>
            </div>'''

    if weekly_videos or daily_videos:
        if weekly_videos:
            cards = ''.join(_render_video_card(v, True) for v in weekly_videos)
            html += f'''
                <div style="max-width: 1400px; margin: 0 auto 3rem auto;">
                    <h2 style="color: #4a9eff; margin-bottom: 1rem; padding-left: 0.5rem;">Weekly Timelapses ({len(weekly_videos)})</h2>
                    <p style="color: #888; margin-bottom: 1.5rem; padding-left: 0.5rem;">7-day timelapses at 24fps, ~5 seconds each</p>
                    <div class="video-grid">
                {cards}</div></div>'''

        if daily_videos:
            cards = ''.join(_render_video_card(v, False) for v in daily_videos)
            html += f'''
                <div style="max-width: 1400px; margin: 0 auto;">
                    <h2 style="color: #4a9eff; margin-bottom: 1rem; padding-left: 0.5rem;">Daily Timelapses ({len(daily_videos)})</h2>
                    <p style="color: #888; margin-bottom: 1.5rem; padding-left: 0.5rem;">24-hour timelapses at 12fps, showing every capture</p>
                    <div class="video-grid">
                {cards}</div></div>'''
        html += '</div>'
    else:
        html += '''
            <div class="no-videos">
                <h2>No Videos Yet</h2>
                <p>Timelapse videos are generated weekly on Sundays at 2 AM UTC.</p>
                <p style="color: #666; margin-top: 1rem;">Videos will appear here once the first weekly generation completes.</p>
            </div>
            '''

    return html


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


def render_gardencam_main(images, image_cards):
    """Render the main gardencam page with latest images."""
    return f'''\
{_THEME_CSS_JS}
            <title>Garden Camera</title>
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
            <h1>Garden Camera</h1>
            <a href="gardencam/gallery" class="gallery-link">View Full Gallery</a>
            <a href="gardencam/videos" class="gallery-link" style="margin-left: 0.5rem;">🎬 Timelapse Videos</a>
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
