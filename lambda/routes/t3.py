"""Extracted from mywebsite.py."""


def t3_format_html(arrivals, *, theme_css_js, t3_seconds_to_quarter_minutes):
    """Format Parklands arrivals as HTML."""
    inbound = arrivals.get('inbound', [])
    outbound = arrivals.get('outbound', [])

    def format_times(times):
        if not times:
            return '<span class="time-box" style="color:#666">--</span>'
        boxes = []
        for i, secs in enumerate(times):
            cls = 'time-box next' if i == 0 else 'time-box'
            display = t3_seconds_to_quarter_minutes(secs)
            boxes.append(f'<span class="{cls}">{display}</span>')
        return ' '.join(boxes)

    return f"""{theme_css_js}
<title>K2 Parklands</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html {{ font-size: 16px; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text); padding: 1rem; margin: 0; text-align: center; }}
.nav {{ position: absolute; top: 1rem; left: 1rem; }}
.nav a {{ color: var(--accent); text-decoration: none; font-size: 0.9rem; }}
h1 {{ font-size: 1.2rem; margin-top: 1rem; margin-bottom: 6rem; }}
.direction {{ margin: 3rem 0; }}
.times {{ font-family: monospace; }}
.time-box {{ display: inline-block; font-size: 6rem; color: var(--accent); border: 2px solid var(--accent); border-radius: 12px; padding: 0.3rem 0.8rem; margin: 0 0.5rem; }}
.time-box.next {{ color: var(--text); font-weight: bold; border-color: var(--text); }}
.dest {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 1rem; }}
.refresh {{ font-size: 0.8rem; color: var(--text-secondary); margin-top: 3rem; }}
</style>
<div class="nav"><a href="contents">Home</a></div>
<h1>K2 @ Parklands</h1>
<div class="direction">
  <div class="times">{format_times(inbound)}</div>
  <div class="dest">towards Kingston</div>
</div>
<div class="direction">
  <div class="times">{format_times(outbound)}</div>
  <div class="dest">towards Hook</div>
</div>
<div class="refresh">refresh in <span id="countdown">60</span>s</div>
<script>
let t = 60;
const el = document.getElementById('countdown');
setInterval(() => {{
  t--;
  if (t <= 0) location.reload();
  el.textContent = t;
}}, 1000);
</script>
"""
