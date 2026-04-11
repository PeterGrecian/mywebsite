"""Claude usage and AI config page renderers."""

import json
import sys

# These are set by the first call from mywebsite.py stubs
_AI_APPS = None
_AI_PROVIDERS = None
_MODEL_PRICING = None


def _init_config(ai_apps, ai_providers, model_pricing=None):
    global _AI_APPS, _AI_PROVIDERS, _MODEL_PRICING
    _AI_APPS = ai_apps
    _AI_PROVIDERS = ai_providers
    if model_pricing:
        _MODEL_PRICING = model_pricing


def _render_usage_bar(label, sublabel, value, limit, color="var(--accent)"):
    """Render a Claude-style usage bar with label, progress bar, and percentage."""
    pct = min(100, int(value / limit * 100)) if limit > 0 else 0
    return f'''<div style="margin-bottom:0.8rem;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.2rem;">
            <div>
                <span style="font-size:0.7rem;font-weight:600;color:var(--text);">{label}</span>
                <div style="font-size:0.55rem;color:var(--text-secondary);">{sublabel}</div>
            </div>
            <span style="font-size:0.6rem;color:var(--text-secondary);">{pct}% used</span>
        </div>
        <div style="height:6px;background:var(--divider);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:{pct}%;background:{color};border-radius:3px;transition:width 0.3s;"></div>
        </div>
    </div>'''


def _render_usage_meter(usage):
    """Render the AI usage meter section with token counts and cost."""
    if not usage:
        return ""

    total_in = usage.get("input_tokens_today", 0)
    total_out = usage.get("output_tokens_today", 0)
    cost = usage.get("cost_today_usd", 0.0)

    bars = _render_usage_bar("Input tokens today", f"{total_in:,} tokens", total_in, max(total_in, 100_000))
    bars += _render_usage_bar("Output tokens today", f"{total_out:,} tokens", total_out, max(total_out, 10_000))
    bars += _render_usage_bar("Estimated cost today", f"${cost:.4f}", cost * 100, max(cost * 100, 1.0), color="var(--warning)")

    # Per-provider table
    by_provider = usage.get("by_provider", {})
    grid_rows = ""
    for prov in _AI_PROVIDERS:
        pk = prov["key"]
        pd = by_provider.get(pk, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        grid_rows += f'''<tr>
            <td style="padding:0.3rem 0.4rem;font-size:0.65rem;color:var(--text);font-weight:500;">{prov['name']}</td>
            <td style="padding:0.3rem;text-align:right;font-size:0.65rem;color:var(--accent);">{pd['calls']}</td>
            <td style="padding:0.3rem;text-align:right;font-size:0.65rem;">{pd['input_tokens']:,}</td>
            <td style="padding:0.3rem;text-align:right;font-size:0.65rem;">{pd['output_tokens']:,}</td>
            <td style="padding:0.3rem;text-align:right;font-size:0.65rem;color:var(--text-secondary);">${pd['cost_usd']:.4f}</td>
        </tr>'''

    grid = f'''<table style="width:100%;border-collapse:collapse;margin-top:0.5rem;">
        <thead><tr>
            <th style="text-align:left;padding:0.3rem 0.4rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Provider</th>
            <th style="text-align:right;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Calls</th>
            <th style="text-align:right;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">In tok</th>
            <th style="text-align:right;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Out tok</th>
            <th style="text-align:right;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Cost</th>
        </tr></thead>
        <tbody>{grid_rows}</tbody>
    </table>'''

    # Recent calls — times in Europe/London (BST/GMT)
    import zoneinfo
    london = zoneinfo.ZoneInfo("Europe/London")
    recent_rows = ""
    for c in usage["recent"]:
        local_ts = c["ts"].astimezone(london)
        tz_name = local_ts.strftime("%Z")  # "BST" or "GMT"
        time_str = local_ts.strftime("%H:%M:%S")
        status = f'<span style="color:var(--error);">{c["error"][:30]}</span>' if c.get("error") else f'{c["duration_ms"]}ms'
        model_short = c["model"].split("/")[-1].replace("anthropic.", "")
        if len(model_short) > 20:
            model_short = model_short[:18] + ".."
        in_tok = c.get("input_tokens", 0)
        out_tok = c.get("output_tokens", 0)
        tok_str = f'{in_tok:,}↑ {out_tok:,}↓' if (in_tok or out_tok) else "—"
        recent_rows += f'''<tr style="border-top:1px solid var(--divider);">
            <td style="padding:0.3rem;font-size:0.55rem;color:var(--text-secondary);">{time_str}</td>
            <td style="padding:0.3rem;font-size:0.55rem;">{c["app"]}</td>
            <td style="padding:0.3rem;font-size:0.55rem;color:var(--text-secondary);">{model_short}</td>
            <td style="padding:0.3rem;font-size:0.55rem;color:var(--text-secondary);">{tok_str}</td>
            <td style="padding:0.3rem;font-size:0.55rem;text-align:right;">{status}</td>
        </tr>'''

    recent_html = ""
    if recent_rows:
        recent_html = f'''<div style="margin-top:1rem;">
            <table style="width:100%;border-collapse:collapse;">
                <thead><tr>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Time ({tz_name})</th>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">App</th>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Model</th>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Tokens</th>
                    <th style="text-align:right;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Duration</th>
                </tr></thead>
                <tbody>{recent_rows}</tbody>
            </table>
        </div>'''

    recent_heading = f'<hr style="border:none;border-top:1px solid var(--divider);margin:1.2rem 0 0.8rem 0;"><h3 style="font-size:0.75rem;font-weight:600;margin:0 0 0.3rem 0;">Recent calls</h3>' if recent_html else ""
    return f'''
        <h2 style="font-size:0.9rem;font-weight:600;margin:1.5rem 0 0.8rem 0;">AI Usage</h2>
        {bars}
        {grid}
        {recent_heading}
        {recent_html}'''


def fetch_claude_quota():
    """Fetch Claude Pro quota from Anthropic OAuth endpoint.

    Token is stored in SSM as /berrylands/claude-oauth (JSON with accessToken,
    refreshToken, expiresAt). Refreshes automatically when expired.
    Returns the parsed JSON dict from the API, or None on failure.
    """
    import time
    import urllib.request
    import urllib.error

    OAUTH_PARAM = '/berrylands/claude-oauth'
    USAGE_URL = 'https://api.anthropic.com/api/oauth/usage'
    USAGE_BETA = 'oauth-2025-04-20'
    TOKEN_URL = 'https://claude.ai/oauth/token'

    boto3 = sys.modules.get("boto3")
    if not boto3:
        print("WARNING: boto3 not available for fetch_claude_quota")
        return None
    ssm = boto3.client('ssm', region_name='eu-west-1')

    def load_token():
        try:
            resp = ssm.get_parameter(Name=OAUTH_PARAM, WithDecryption=True)
            return json.loads(resp['Parameter']['Value'])
        except Exception as e:
            print(f"claude_quota: SSM load failed: {e}")
            return None

    def save_token(tok):
        try:
            ssm.put_parameter(Name=OAUTH_PARAM, Value=json.dumps(tok),
                              Type='SecureString', Overwrite=True)
        except Exception as e:
            print(f"claude_quota: SSM save failed: {e}")

    def refresh_token(refresh_tok):
        try:
            body = json.dumps({'grant_type': 'refresh_token', 'refresh_token': refresh_tok}).encode()
            req = urllib.request.Request(TOKEN_URL, data=body,
                                         headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            return {
                'accessToken': data['access_token'],
                'refreshToken': data.get('refresh_token', refresh_tok),
                'expiresAt': int(time.time() * 1000) + data.get('expires_in', 3600) * 1000,
            }
        except Exception as e:
            print(f"claude_quota: token refresh failed: {e}")
            return None

    def call_api(access_token):
        req = urllib.request.Request(USAGE_URL, headers={
            'Authorization': f'Bearer {access_token}',
            'anthropic-beta': USAGE_BETA,
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    tok = load_token()
    if not tok:
        return None

    now_ms = int(time.time() * 1000)
    if tok.get('expiresAt', 0) < now_ms + 60_000:
        print("claude_quota: token expired, refreshing")
        new_tok = refresh_token(tok['refreshToken'])
        if new_tok:
            save_token(new_tok)
            tok = new_tok
        else:
            return None

    try:
        return call_api(tok['accessToken'])
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("claude_quota: 401 on API call, attempting refresh")
            new_tok = refresh_token(tok['refreshToken'])
            if new_tok:
                save_token(new_tok)
                try:
                    return call_api(new_tok['accessToken'])
                except Exception as e2:
                    print(f"claude_quota: retry failed: {e2}")
        else:
            print(f"claude_quota: HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"claude_quota: API call failed: {e}")
    return None


def render_claude_usage_page(quota, *, theme_css_js):
    """Render the Claude Pro usage page showing 5h and 7d quota buckets."""
    from datetime import datetime, timezone, timedelta
    import zoneinfo
    _london = zoneinfo.ZoneInfo("Europe/London")

    def bucket_html(label, data, window_hours=None):
        if not data or data.get('utilization') is None:
            return ''
        pct = data['utilization']
        reset_dt = datetime.fromisoformat(data['resets_at']).astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)

        if window_hours:
            window_start = reset_dt - timedelta(hours=window_hours)
            elapsed_h = (now_utc - window_start).total_seconds() / 3600
            remaining_h = (reset_dt - now_utc).total_seconds() / 3600
            elapsed_frac = elapsed_h / window_hours
            if elapsed_h > 0 and remaining_h > 0:
                current_rate = pct / elapsed_h
                required_rate = (100 - pct) / remaining_h
                projected = pct + current_rate * remaining_h
            else:
                current_rate = required_rate = projected = 0
            rate_unit = '/hr'
            elapsed_str = f'{elapsed_h:.1f}h / {window_hours}h ({elapsed_frac*100:.0f}%)'
            reset_str = reset_dt.astimezone(_london).strftime('%H:%M %a')
        else:
            week_start = reset_dt - timedelta(weeks=1)
            elapsed_d = (now_utc - week_start).total_seconds() / 86400
            remaining_d = (reset_dt - now_utc).total_seconds() / 86400
            elapsed_frac = elapsed_d / 7
            if elapsed_d > 0 and remaining_d > 0:
                current_rate = pct / elapsed_d
                required_rate = (100 - pct) / remaining_d
                projected = pct + current_rate * remaining_d
            else:
                current_rate = required_rate = projected = 0
            rate_unit = '/day'
            elapsed_str = f'{elapsed_d:.1f}d / 7d ({elapsed_frac*100:.0f}%)'
            reset_str = reset_dt.astimezone(_london).strftime('%a %d %b %H:%M')

        bar_color = 'var(--error)' if pct > 80 else 'var(--warning)' if pct > 60 else 'var(--accent)'
        proj_color = 'var(--error)' if projected > 100 else 'var(--warning)' if projected > 80 else 'var(--text-secondary)'

        # If quota will be exhausted before reset, calculate when and the gap
        exhaust_html = ''
        if projected > 100 and current_rate > 0:
            time_to_exhaust = (100 - pct) / current_rate  # hours or days (negative if already past)
            exhaust_dt = now_utc + timedelta(hours=time_to_exhaust if window_hours else time_to_exhaust * 24)
            gap = (reset_dt - now_utc).total_seconds()
            already_exhausted = time_to_exhaust <= 0
            if window_hours:
                exhaust_local = exhaust_dt.astimezone(_london)
                exhaust_str = exhaust_local.strftime('%H:%M')
                if already_exhausted:
                    in_str = 'already exhausted'
                elif time_to_exhaust < 1:
                    in_str = f'in {time_to_exhaust*60:.0f}m'
                else:
                    in_str = f'in {time_to_exhaust:.1f}h'
                gap_str = f'{gap/3600:.1f}h until reset'
            else:
                exhaust_local = exhaust_dt.astimezone(_london)
                exhaust_str = exhaust_local.strftime('%a %d %b %H:%M')
                in_str = 'already exhausted' if already_exhausted else f'in {time_to_exhaust:.1f}d'
                gap_str = f'{gap/3600:.0f}h until reset' if gap < 86400 else f'{gap/86400:.1f}d until reset'
            if already_exhausted:
                exhaust_html = f'''<div style="background:var(--bg);border-radius:8px;padding:0.5rem;grid-column:1/-1;border:1px solid var(--error);">
                    <div style="font-size:0.55rem;color:var(--error);margin-bottom:0.2rem;">Quota {in_str}</div>
                    <div style="font-size:0.8rem;font-weight:600;color:var(--error);">{gap_str}</div>
                </div>'''
            else:
                exhaust_html = f'''<div style="background:var(--bg);border-radius:8px;padding:0.5rem;grid-column:1/-1;border:1px solid var(--error);">
                    <div style="font-size:0.55rem;color:var(--error);margin-bottom:0.2rem;">Quota exhausted {in_str} at {exhaust_str}</div>
                    <div style="font-size:0.8rem;font-weight:600;color:var(--error);">{gap_str}</div>
                </div>'''

        return f'''<div style="background:var(--card-bg);border-radius:12px;padding:1rem;margin-bottom:0.75rem;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.5rem;">
                <span style="font-size:0.85rem;font-weight:600;color:var(--text);">{label}</span>
                <span style="font-size:0.75rem;color:var(--text-secondary);">resets {reset_str}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.3rem;">
                <span style="font-size:0.65rem;color:var(--text-secondary);">{elapsed_str}</span>
                <span style="font-size:1rem;font-weight:700;color:var(--text);">{pct:.0f}%</span>
            </div>
            <div style="height:8px;background:var(--divider);border-radius:4px;overflow:hidden;margin-bottom:0.75rem;">
                <div style="height:100%;width:{min(pct,100):.0f}%;background:{bar_color};border-radius:4px;transition:width 0.3s;"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;">
                <div style="background:var(--bg);border-radius:8px;padding:0.5rem;">
                    <div style="font-size:0.55rem;color:var(--text-secondary);margin-bottom:0.2rem;">Current rate</div>
                    <div style="font-size:0.8rem;font-weight:600;color:var(--text);">{current_rate:.1f}%{rate_unit}</div>
                </div>
                <div style="background:var(--bg);border-radius:8px;padding:0.5rem;">
                    <div style="font-size:0.55rem;color:var(--text-secondary);margin-bottom:0.2rem;">Rate to reach 100%</div>
                    <div style="font-size:0.8rem;font-weight:600;color:var(--text);">{required_rate:.1f}%{rate_unit}</div>
                </div>
                <div style="background:var(--bg);border-radius:8px;padding:0.5rem;grid-column:1/-1;">
                    <div style="font-size:0.55rem;color:var(--text-secondary);margin-bottom:0.2rem;">Projected at reset</div>
                    <div style="font-size:0.8rem;font-weight:600;color:{proj_color};">{projected:.0f}%</div>
                </div>
                {exhaust_html}
            </div>
        </div>'''

    if quota:
        five_h = bucket_html('5-hour window', quota.get('five_hour'), window_hours=5)
        seven_d = bucket_html('7-day window', quota.get('seven_day'))
        content = five_h + seven_d
    else:
        content = '<div style="font-size:0.8rem;text-align:center;padding:2rem;"><a href="https://claude.ai" style="color:var(--accent);">Could not fetch quota data — open Claude.ai to refresh session</a></div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Usage</title>
    {theme_css_js}
<style>
.cu-wrap{{max-width:500px;margin:0 auto;}}
@media(min-width:768px){{
  .cu-wrap{{max-width:800px;zoom:1.6;}}
}}
body.desktop-override .cu-wrap{{max-width:800px;zoom:1.6;}}
body.phone-override .cu-wrap{{max-width:500px;zoom:1;}}
#home-btn{{position:fixed;top:0.8rem;left:0.8rem;color:var(--text-secondary);font-size:0.65rem;text-decoration:none;z-index:10000;opacity:0.5;font-family:var(--font);}}
#home-btn:hover{{opacity:1;}}
</style>
</head>
<body style="margin:0;padding:1rem;background:var(--bg);color:var(--text);font-family:var(--font);">
    <a id="home-btn" href="contents">Home</a>
    <div class="cu-wrap">
        <h1 style="font-size:1rem;font-weight:600;margin:0 0 1rem 0;text-align:center;">Claude Usage</h1>
        {content}
    </div>
<script>
document.addEventListener('DOMContentLoaded',function(){{
  var body=document.body;
  var stored=localStorage.getItem('cu-view');
  if(stored==='desktop')body.classList.add('desktop-override');
  else if(stored==='phone')body.classList.add('phone-override');

  if(!window._settingsMenu)return;
  var item=document.createElement('div');
  item.className='settings-item';
  var label=document.createElement('span');
  var check=document.createElement('span');
  check.className='check';
  function update(){{
    var v=localStorage.getItem('cu-view')||'auto';
    label.textContent=v==='desktop'?'Phone view':v==='phone'?'Auto view':'Desktop view';
    check.textContent='';
  }}
  update();
  item.appendChild(label);
  item.appendChild(check);
  item.onclick=function(e){{
    e.stopPropagation();
    var v=localStorage.getItem('cu-view')||'auto';
    var n=v==='auto'?'desktop':v==='desktop'?'phone':'auto';
    localStorage.setItem('cu-view',n);
    body.classList.remove('desktop-override','phone-override');
    if(n==='desktop')body.classList.add('desktop-override');
    else if(n==='phone')body.classList.add('phone-override');
    update();
  }};
  window._settingsMenu.appendChild(item);
}});
</script>
</body>
</html>'''


def render_ai_config_page(configs, usage=None, message=None, *, theme_css_js, ai_apps=None, ai_providers=None):
    """Render the AI configuration matrix page with usage meter."""
    apps = ai_apps or _AI_APPS
    providers = ai_providers or _AI_PROVIDERS
    msg_html = ""

    # Build the matrix rows
    rows = ""
    for app in apps:
        cfg = configs.get(app["key"], {})
        active_provider = cfg.get("provider", "")
        active_model = cfg.get("model", "")

        cells = ""
        for prov in providers:
            is_active = prov["key"] == active_provider
            bg = "var(--accent)" if is_active else "var(--card-bg)"
            color = "#fff" if is_active else "var(--text-secondary)"
            border = "none" if is_active else "1px solid var(--divider)"

            # Model selector — always shown, pre-selects active model if this is the active provider
            model_opts = ""
            for m in prov["models"]:
                sel = " selected" if (is_active and m == active_model) else ""
                short = m.split("/")[-1].replace("anthropic.", "")
                price = _MODEL_PRICING.get(m)
                price_str = f" ${price[0]}/${price[1]}" if price else ""
                model_opts += f'<option value="{m}"{sel}>{short}{price_str}</option>'

            model_select = f'''<select name="model" form="form-{app['key']}-{prov['key']}"
                style="margin-top:0.3rem;width:100%;background:var(--bg);color:var(--text);border:1px solid var(--divider);border-radius:6px;padding:0.15rem;font-size:0.5rem;font-family:var(--font);"
                onchange="submitAiConfig(this.form, this)">{model_opts}</select>'''

            cells += f'''<td style="padding:0.4rem;text-align:center;vertical-align:top;">
                <form id="form-{app['key']}-{prov['key']}" method="POST" action="ai-config">
                    <input type="hidden" name="app" value="{app['key']}">
                    <input type="hidden" name="provider" value="{prov['key']}">
                    <input type="hidden" name="model" value="{prov['models'][0]}">
                    <button type="submit" onclick="handleProviderClick(event, this)"
                        style="background:{bg};color:{color};border:{border};border-radius:6px;padding:0.3rem 0.5rem;font-size:0.6rem;cursor:pointer;font-family:var(--font);width:100%;min-width:3.5rem;"
                        data-active="{'true' if is_active else 'false'}">{prov['name']}</button>
                </form>
                {model_select}
            </td>'''

        rows += f'''<tr>
            <td style="padding:0.4rem;font-size:0.7rem;white-space:nowrap;">
                <div style="color:var(--text);font-weight:600;">{app['name']}</div>
                <div style="color:var(--text-secondary);font-size:0.55rem;">{app['desc']}</div>
            </td>
            {cells}
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Configuration</title>
    {theme_css_js}
<style>
.ai-wrap{{max-width:600px;margin:0 auto;}}
@media(min-width:768px){{
  .ai-wrap{{max-width:860px;zoom:1.6;}}
}}
</style>
</head>
<body style="margin:0;padding:1rem;background:var(--bg);color:var(--text);font-family:var(--font);">
    <div class="ai-wrap">
        <div style="text-align:center;margin-bottom:1rem;">
            <a href="contents" style="color:var(--accent);text-decoration:none;font-size:0.75rem;">Home</a>
        </div>
        <h1 style="font-size:1rem;font-weight:600;margin:0 0 0.8rem 0;text-align:center;">AI Configuration</h1>
        {msg_html}
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">App</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Gemini</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">OpenAI</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Bedrock</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <hr style="border:none;border-top:1px solid var(--divider);margin:1.2rem 0;">
        {_render_usage_meter(usage)}
    </div>
<script>
function handleProviderClick(e, btn) {{
    e.preventDefault();
    btn.style.background = '#34C759';
    btn.style.color = '#fff';
    btn.style.border = 'none';
    var form = btn.closest('form');
    submitAiConfig(form, null);
}}

function submitAiConfig(form, select) {{
    var data = new FormData(form);
    if (select) {{
        data.set('model', select.value);
        var btn = form.querySelector('button');
        if (btn) {{
            btn.style.background = '#34C759';
            btn.style.color = '#fff';
            btn.style.border = 'none';
        }}
    }}
    fetch('/ai-config', {{method: 'POST', body: new URLSearchParams(data)}})
        .then(function(r) {{ if (r.ok) window.location.reload(); }})
        .catch(function(err) {{ console.error('ai-config POST failed:', err); }});
}}
</script>
</body>
</html>'''


