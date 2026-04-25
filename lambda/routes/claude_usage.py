"""AI config page renderers (failover chain, per-app provider/model config, usage meter)."""

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


_STATUS_COLOR = {
    "ok":       ("#34C759", "OK"),
    "degraded": ("#FF9500", "DEGRADED"),
    "failing":  ("#FF3B30", "FAILING"),
    "unknown":  ("#8E8E93", "—"),
}


def _render_failover_chain(chain, providers, health):
    """Render the global failover chain editor with per-provider status pills."""
    provider_by_key = {p["key"]: p for p in providers}

    # Order: chain entries first, then any providers not yet in the chain
    chain_keys = [e["provider"] for e in chain if e.get("provider") in provider_by_key]
    extras = [p["key"] for p in providers if p["key"] not in chain_keys]
    ordered = chain_keys + extras

    rows = ""
    for i, key in enumerate(ordered):
        prov = provider_by_key[key]
        h = health.get(key, {"status": "unknown", "error_msg": None,
                             "recent_n": 0, "recent_failures": 0, "last_error": None})
        color, label = _STATUS_COLOR.get(h["status"], _STATUS_COLOR["unknown"])
        in_chain = key in chain_keys
        position_label = f"#{chain_keys.index(key)+1}" if in_chain else "off"

        recent_summary = ""
        if h["recent_n"]:
            recent_summary = f"{h['recent_n'] - h['recent_failures']}/{h['recent_n']} ok"
        error_excerpt = ""
        if h["error_msg"]:
            err = h["error_msg"][:60]
            error_excerpt = f'<div style="color:var(--error);font-size:0.5rem;margin-top:0.15rem;">{err}</div>'

        # Up/down/toggle buttons
        up_disabled = "disabled" if (not in_chain or chain_keys.index(key) == 0) else ""
        down_disabled = "disabled" if (not in_chain or chain_keys.index(key) == len(chain_keys) - 1) else ""
        toggle_label = "Remove" if in_chain else "Add"

        rows += f'''<tr data-key="{key}" data-in-chain="{'1' if in_chain else '0'}" style="border-top:1px solid var(--divider);">
            <td style="padding:0.4rem;font-size:0.6rem;color:var(--text-secondary);width:2rem;">{position_label}</td>
            <td style="padding:0.4rem;font-size:0.7rem;color:var(--text);font-weight:600;">{prov['name']}</td>
            <td style="padding:0.4rem;">
                <span style="background:{color};color:#fff;padding:0.1rem 0.4rem;border-radius:8px;font-size:0.5rem;font-weight:600;">{label}</span>
                <span style="color:var(--text-secondary);font-size:0.55rem;margin-left:0.4rem;">{recent_summary}</span>
                {error_excerpt}
            </td>
            <td style="padding:0.4rem;text-align:right;white-space:nowrap;">
                <button type="button" onclick="moveChain('{key}',-1)" {up_disabled}
                    style="background:var(--card-bg);color:var(--text);border:1px solid var(--divider);border-radius:4px;padding:0.15rem 0.4rem;font-size:0.6rem;cursor:pointer;margin-right:0.2rem;">▲</button>
                <button type="button" onclick="moveChain('{key}',1)" {down_disabled}
                    style="background:var(--card-bg);color:var(--text);border:1px solid var(--divider);border-radius:4px;padding:0.15rem 0.4rem;font-size:0.6rem;cursor:pointer;margin-right:0.4rem;">▼</button>
                <button type="button" onclick="toggleChain('{key}')"
                    style="background:var(--card-bg);color:var(--text-secondary);border:1px solid var(--divider);border-radius:4px;padding:0.15rem 0.4rem;font-size:0.55rem;cursor:pointer;">{toggle_label}</button>
            </td>
        </tr>'''

    return f'''<hr style="border:none;border-top:1px solid var(--divider);margin:1.2rem 0;">
    <h2 style="font-size:0.8rem;font-weight:600;margin:0 0 0.4rem 0;">Failover chain</h2>
    <div style="font-size:0.55rem;color:var(--text-secondary);margin-bottom:0.6rem;">
        Each app tries its preferred provider first, then walks this chain on failure.
    </div>
    <table id="chain-table" style="width:100%;border-collapse:collapse;">
        <tbody>{rows}</tbody>
    </table>'''


def render_ai_config_page(configs, usage=None, message=None, *, theme_css_js,
                          ai_apps=None, ai_providers=None,
                          chain=None, health=None):
    """Render the AI configuration matrix page with usage meter."""
    apps = ai_apps or _AI_APPS
    providers = ai_providers or _AI_PROVIDERS
    chain = chain or []
    health = health or {}
    msg_html = ""
    if message:
        msg_html = f'<div style="background:var(--card-bg);border:1px solid var(--accent);color:var(--accent);padding:0.5rem;border-radius:6px;margin-bottom:0.8rem;font-size:0.7rem;text-align:center;">{message}</div>'

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

    # Provider column headers (auto-generated from providers list)
    provider_headers = "".join(
        f'<th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">{p["name"]}</th>'
        for p in providers
    )

    # Failover chain section
    chain_html = _render_failover_chain(chain, providers, health)

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
                    {provider_headers}
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {chain_html}
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

function _currentChainKeys() {{
    var rows = document.querySelectorAll('#chain-table tr[data-in-chain="1"]');
    return Array.from(rows).map(function(r) {{ return r.dataset.key; }});
}}

function _allKeysInDomOrder() {{
    var rows = document.querySelectorAll('#chain-table tr[data-key]');
    return Array.from(rows).map(function(r) {{ return r.dataset.key; }});
}}

function _postChain(orderArr) {{
    var data = new URLSearchParams();
    data.set('action', 'reorder');
    data.set('order', orderArr.join(','));
    fetch('/ai-config', {{method: 'POST', body: data}})
        .then(function(r) {{ if (r.ok) window.location.reload(); }})
        .catch(function(err) {{ console.error('chain POST failed:', err); }});
}}

function moveChain(key, delta) {{
    var keys = _currentChainKeys();
    var i = keys.indexOf(key);
    if (i < 0) return;
    var j = i + delta;
    if (j < 0 || j >= keys.length) return;
    var tmp = keys[i]; keys[i] = keys[j]; keys[j] = tmp;
    _postChain(keys);
}}

function toggleChain(key) {{
    var keys = _currentChainKeys();
    var i = keys.indexOf(key);
    if (i >= 0) {{
        keys.splice(i, 1);
    }} else {{
        keys.push(key);
    }}
    _postChain(keys);
}}
</script>
</body>
</html>'''


