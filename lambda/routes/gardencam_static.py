"""Static gardencam pages with no dynamic data."""


def render_timelapse_schedule():
    """Render the timelapse schedule page (purely static content)."""
    return '''
        <meta charset="UTF-8">
        <title>Timelapse Schedule - Garden Camera</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
            .nav { text-align: center; margin-bottom: 1.5rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }
            .nav a:hover { background: #3a3a3a; }
            h1 { text-align: center; margin-bottom: 2rem; }
            .container { max-width: 1200px; margin: 0 auto; }
            .schedule-section { background: #2a2a2a; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }
            .schedule-section h2 { margin-top: 0; color: #4a9eff; }
            .schedule-item { background: #1a1a1a; padding: 1rem; margin: 1rem 0; border-radius: 6px; border-left: 4px solid #4a9eff; }
            .schedule-item h3 { margin: 0 0 0.5rem 0; color: #fff; }
            .schedule-item p { margin: 0.25rem 0; color: #aaa; }
            .status { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.85rem; margin-left: 0.5rem; }
            .status.active { background: #10b981; color: #fff; }
            .status.dryrun { background: #f59e0b; color: #000; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #3a3a3a; }
            th { color: #4a9eff; background: #1a1a1a; }
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="timelapse">Timelapse Index</a>
            <a href="timelapse/videos">All Videos</a>
        </div>
        <div class="container">
            <h1>Timelapse Automation Schedule</h1>

            <div class="schedule-section">
                <h2>Video Generation</h2>
                <div class="schedule-item">
                    <h3>Weekly Timelapse Creation <span class="status active">ACTIVE</span></h3>
                    <p><strong>Schedule:</strong> Every Sunday at 2:00 AM UTC</p>
                    <p><strong>Duration:</strong> 20 seconds per video (480 frames at 24fps)</p>
                    <p><strong>Output:</strong> videos/timelapse_YYYYMMDD-YYYYMMDD.mp4</p>
                    <p><strong>Lambda:</strong> gardencam-timelapse-generator (3GB memory, 15 min timeout)</p>
                    <p><strong>Next Run:</strong> Next Sunday 02:00 UTC</p>
                </div>
            </div>

            <div class="schedule-section">
                <h2>Image Culling</h2>
                <div class="schedule-item">
                    <h3>Daily Cleanup Check <span class="status dryrun">DRY-RUN</span></h3>
                    <p><strong>Schedule:</strong> Every day at 12:00 PM UTC</p>
                    <p><strong>Mode:</strong> Dry-run (no actual deletion yet)</p>
                    <p><strong>Protection:</strong> ALL night images preserved forever</p>
                    <p><strong>Retention:</strong> Latest 14 days always kept</p>
                    <p><strong>Lambda:</strong> gardencam-image-culling (512MB memory, 5 min timeout)</p>
                </div>

                <h3 style="margin-top: 2rem;">Retention Policy</h3>
                <table>
                    <tr>
                        <th>Age</th>
                        <th>Day Images</th>
                        <th>Night Images</th>
                    </tr>
                    <tr>
                        <td>0-14 days</td>
                        <td>Keep all</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>15-30 days</td>
                        <td>Keep 1 per day</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>31-90 days</td>
                        <td>Keep 1 per week</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>90+ days</td>
                        <td>Keep 1 per month</td>
                        <td>Keep all</td>
                    </tr>
                </table>
            </div>

            <div class="schedule-section">
                <h2>Storage Summary</h2>
                <div class="schedule-item">
                    <h3>Hourly Storage Stats Update <span class="status active">ACTIVE</span></h3>
                    <p><strong>Schedule:</strong> Every hour</p>
                    <p><strong>Function:</strong> Calculate S3 storage statistics</p>
                    <p><strong>Lambda:</strong> gardencam-storage-summary</p>
                </div>
            </div>

            <div class="schedule-section">
                <h2>System Information</h2>
                <p><strong>Region:</strong> eu-west-1 (Ireland)</p>
                <p><strong>S3 Bucket:</strong> gardencam-berrylands-eu-west-1</p>
                <p><strong>Video Format:</strong> MP4 (H.264, 1920x1080, 24fps)</p>
                <p><strong>Frame Selection:</strong> Evenly distributed from all images in date range</p>
            </div>
        </div>
        '''
