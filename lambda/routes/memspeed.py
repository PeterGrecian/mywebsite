"""Extracted from mywebsite.py."""

import json


def render_memspeed_page(results, downloads, *, theme_css_js):
    """Render the memspeed visualization page."""
    # Assign colors to machines
    colors = [
        '#4a9eff', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ]

    # Prepare datasets for Chart.js
    datasets_js = []
    for i, result in enumerate(results):
        machine = result.get('machine', 'Unknown')
        color = colors[i % len(colors)]
        data_points = result.get('data', [])

        # Format data for scatter plot
        points = [{'x': p['size'], 'y': p['speed']} for p in data_points]

        cpu = result.get('cpu', '')
        ram = result.get('ram', '')
        label = machine
        if cpu:
            label += f" ({cpu})"

        datasets_js.append({
            'label': label,
            'data': points,
            'borderColor': color,
            'backgroundColor': color,
            'showLine': True,
            'tension': 0.1,
            'pointRadius': 2,
            'borderWidth': 2
        })

    # Build downloads HTML
    downloads_html = ''
    if downloads:
        downloads_html = '<h2>Downloads</h2><div class="downloads-grid">'
        for dl in downloads:
            size_kb = dl['size'] / 1024
            if size_kb > 1024:
                size_str = f"{size_kb/1024:.1f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            downloads_html += f'''
            <a href="memspeed/download?file={dl['filename']}" class="download-item">
                <span class="filename">{dl['filename']}</span>
                <span class="filesize">{size_str}</span>
            </a>
            '''
        downloads_html += '</div>'

    # Build results table
    results_table = ''
    if results:
        results_table = '''
        <h2>Benchmark Results</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Machine</th>
                    <th>CPU</th>
                    <th>Cache (L1 / L2 / L3)</th>
                    <th>RAM</th>
                    <th>OS</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
        '''
        for result in results:
            cache = result.get('cache', {})
            if cache:
                cache_str = f"{cache.get('L1', '-')} / {cache.get('L2', '-')} / {cache.get('L3', '-')}"
            else:
                cache_str = '-'
            results_table += f'''
                <tr>
                    <td>{result.get('machine', 'Unknown')}</td>
                    <td>{result.get('cpu', '-')}</td>
                    <td>{cache_str}</td>
                    <td>{result.get('ram', '-')}</td>
                    <td>{result.get('os', '-')}</td>
                    <td>{result.get('timestamp', '-')}</td>
                </tr>
            '''
        results_table += '</tbody></table>'

    return f'''{theme_css_js}
    <title>Memory Bandwidth Benchmark</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{ font-family: var(--font); margin: 0; padding: 1rem; background: var(--bg); color: var(--text); }}
        .nav {{ text-align: center; margin-bottom: 1.5rem; }}
        .nav a {{ color: var(--accent); text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 6px; display: inline-block; }}
        .nav a:hover {{ opacity: 0.8; }}
        h1 {{ text-align: center; margin-bottom: 2rem; }}
        h2 {{ color: var(--text-secondary); margin-top: 2rem; }}
        .chart-container {{ max-width: 1400px; margin: 0 auto 2rem auto; background: var(--card-bg); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--divider); }}
        .chart-title {{ font-size: 1.2rem; margin-bottom: 1rem; color: var(--text-secondary); text-align: center; }}
        canvas {{ max-height: 500px; }}
        .upload-section {{ max-width: 600px; margin: 2rem auto; padding: 1.5rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; }}
        .upload-section h2 {{ margin-top: 0; }}
        .upload-form {{ display: flex; flex-direction: column; gap: 1rem; }}
        .upload-form input[type="file"] {{ padding: 0.5rem; background: var(--bg); border: 1px solid var(--divider); border-radius: 4px; color: var(--text); }}
        .upload-form button {{ padding: 0.75rem 1.5rem; background: var(--accent); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; }}
        .upload-form button:hover {{ opacity: 0.85; }}
        .upload-form button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        #uploadStatus {{ margin-top: 0.5rem; font-size: 0.9rem; }}
        .downloads-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem; }}
        .download-item {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--card-bg); border-radius: 6px; text-decoration: none; color: var(--accent); border: 1px solid var(--divider); transition: background 0.2s; }}
        .download-item:hover {{ background: rgba(142,142,147,0.1); }}
        .filename {{ font-family: monospace; }}
        .filesize {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .results-table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        .results-table th, .results-table td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--divider); }}
        .results-table th {{ color: var(--text-secondary); background: var(--bg); }}
        .results-table td {{ font-family: monospace; font-size: 0.9rem; }}
        .no-data {{ text-align: center; color: var(--text-secondary); padding: 2rem; }}
        .about-section {{ max-width: 900px; margin: 0 auto 2rem auto; padding: 1.5rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; line-height: 1.6; }}
        .about-section h2 {{ margin-top: 0; color: var(--text-secondary); }}
        .about-section p {{ color: var(--text-secondary); margin: 1rem 0; }}
        .about-section code {{ background: var(--bg); padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; }}
        .about-section pre {{ background: var(--bg); padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.9rem; }}
        .about-section ul {{ color: var(--text-secondary); margin: 1rem 0; padding-left: 1.5rem; }}
        .about-section li {{ margin: 0.5rem 0; }}
    </style>
    <div class="nav">
        <a href="contents">Home</a>
        <a href="memspeed/data">JSON API</a>
    </div>
    <h1>Memory Bandwidth Benchmark</h1>

    <div class="about-section">
        <h2>About</h2>
        <p>
            This tool measures memory bandwidth by writing to buffers of increasing size.
            The resulting curve reveals CPU cache hierarchy: L1 cache (fastest), L2, L3, and main RAM (slowest).
            Sharp drops in speed indicate transitions between cache levels.
        </p>
        <p>
            The chart uses a log-log scale to clearly show performance across buffer sizes from 1KB to 1GB.
            Compare results across different machines to see how CPU architecture and RAM speed affect performance.
        </p>

        <h2>How to Run</h2>
        <p>Download the source or pre-built binary, run the benchmark, and upload your results:</p>
        <pre># Option 1: Download and compile from source
tar -xzf memspeed-src.tar.gz
gcc ms.c -o ms

# Option 2: Use pre-built binary (Linux x86_64)
chmod +x ms-linux-x86_64
./ms-linux-x86_64

# Run benchmark and generate results
./ms > all.out
grep -v Reps all.out > data.csv
./export_json.py > result.json</pre>
        <p>Then upload <code>result.json</code> using the form below, or via curl:</p>
        <pre>curl -u ":PASSWORD" -X POST -H "Content-Type: application/json" \\
  -d @result.json https://cv.petergrecian.co.uk/memspeed/upload</pre>
    </div>

    <div class="chart-container">
        <div class="chart-title">Memory Read Speed vs Buffer Size (Log-Log Scale)</div>
        <canvas id="memspeedChart"></canvas>
    </div>

    {downloads_html}

    {results_table if results else '<p class="no-data">No benchmark results yet. Upload your results below.</p>'}

    <div class="upload-section">
        <h2>Upload Results</h2>
        <form class="upload-form" id="uploadForm">
            <input type="file" id="jsonFile" accept=".json" required>
            <button type="submit" id="uploadBtn">Upload Benchmark</button>
            <div id="uploadStatus"></div>
        </form>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 1rem;">
            Generate JSON with: <code style="background: var(--bg); padding: 0.2rem 0.4rem; border-radius: 3px;">./export_json.py &gt; result.json</code>
        </p>
    </div>

    <script>
    const datasets = {json.dumps(datasets_js)};

    if (datasets.length > 0) {{
        new Chart(document.getElementById('memspeedChart'), {{
            type: 'scatter',
            data: {{ datasets: datasets }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                scales: {{
                    x: {{
                        type: 'logarithmic',
                        title: {{ display: true, text: 'Buffer Size (bytes)', color: '#aaa' }},
                        ticks: {{
                            color: '#888',
                            callback: function(value) {{
                                if (value >= 1e9) return (value/1e9) + ' GB';
                                if (value >= 1e6) return (value/1e6) + ' MB';
                                if (value >= 1e3) return (value/1e3) + ' KB';
                                return value + ' B';
                            }}
                        }},
                        grid: {{ color: '#333' }}
                    }},
                    y: {{
                        type: 'logarithmic',
                        title: {{ display: true, text: 'Speed (bytes/sec)', color: '#aaa' }},
                        ticks: {{
                            color: '#888',
                            callback: function(value) {{
                                if (value >= 1e9) return (value/1e9) + ' GB/s';
                                if (value >= 1e6) return (value/1e6) + ' MB/s';
                                if (value >= 1e3) return (value/1e3) + ' KB/s';
                                return value + ' B/s';
                            }}
                        }},
                        grid: {{ color: '#333' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#aaa' }},
                        position: 'top'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const size = context.parsed.x;
                                const speed = context.parsed.y;
                                let sizeStr = size >= 1e6 ? (size/1e6).toFixed(1) + ' MB' : (size/1e3).toFixed(1) + ' KB';
                                let speedStr = (speed/1e9).toFixed(2) + ' GB/s';
                                return context.dataset.label + ': ' + sizeStr + ' @ ' + speedStr;
                            }}
                        }}
                    }}
                }}
            }}
        }});
    }}

    document.getElementById('uploadForm').addEventListener('submit', async function(e) {{
        e.preventDefault();
        const fileInput = document.getElementById('jsonFile');
        const status = document.getElementById('uploadStatus');
        const btn = document.getElementById('uploadBtn');

        if (!fileInput.files[0]) {{
            status.textContent = 'Please select a file';
            status.style.color = '#ef4444';
            return;
        }}

        btn.disabled = true;
        btn.textContent = 'Uploading...';
        status.textContent = '';

        try {{
            const text = await fileInput.files[0].text();
            const data = JSON.parse(text);

            const response = await fetch('memspeed/upload', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});

            const result = await response.json();

            if (response.ok) {{
                status.textContent = result.message || 'Upload successful!';
                status.style.color = '#10b981';
                setTimeout(() => location.reload(), 1500);
            }} else {{
                status.textContent = result.error || 'Upload failed';
                status.style.color = '#ef4444';
            }}
        }} catch (err) {{
            status.textContent = 'Error: ' + err.message;
            status.style.color = '#ef4444';
        }}

        btn.disabled = false;
        btn.textContent = 'Upload Benchmark';
    }});
    </script>
    '''


