"""Pi Fleet dashboard route handler."""

import html as _html
import os

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def _load_template(name):
    with open(os.path.join(_TEMPLATE_DIR, name)) as f:
        return f.read()


def _num(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _fmt_cap_mb(mb, format_to_sigfigs):
    mb = _num(mb, 0)
    if mb <= 0:
        return ""
    if mb < 1024:
        val = format_to_sigfigs(mb, 3)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return f"{val}M"
    val = format_to_sigfigs(mb / 1024, 3)
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    return f"{val}G"


def _fmt_cap_gb(gb, format_to_sigfigs):
    gb = _num(gb, 0)
    if gb <= 0:
        return ""
    if gb < 1:
        val = format_to_sigfigs(gb * 1024, 3)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return f"{val}M"
    val = format_to_sigfigs(gb, 3)
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    return f"{val}G"


def _usage_class(pct):
    p = _num(pct, 0)
    if p >= 85:
        return "metric-crit"
    if p >= 70:
        return "metric-warn"
    return ""


def _net_badge(ip):
    if not ip or ip == "unknown":
        return ""
    if ip.startswith("100."):
        return '<span class="net-badge net-tailnet">tailnet</span>'
    if ip.startswith("10."):
        return '<span class="net-badge net-vcn">vcn</span>'
    return ""


def _short_os(os_ver):
    if not os_ver or os_ver == "Unknown":
        return "Unknown"
    return (
        os_ver.replace("GNU/Linux ", "")
        .replace("Raspbian ", "Debian ")
        .replace(" LTS", "")
    )


def _short_model(model):
    if not model or model == "Unknown":
        return "Unknown"
    return (
        model.replace("Raspberry Pi ", "Pi ")
        .replace(" Model ", " ")
        .replace(" Plus", "+")
        .replace("11th Gen Intel(R) Core(TM) ", "Intel ")
        .replace(" Processor", "")
    )


def _detail_row(label, value, full=False):
    if value is None or value == "" or value == "unknown" or value == "Unknown":
        return ""
    cls = "detail-item detail-span" if full else "detail-item"
    return (
        f'<div class="{cls}">'
        f'<div class="detail-label">{_html.escape(str(label))}</div>'
        f'<div class="detail-value">{_html.escape(str(value))}</div>'
        f'</div>'
    )


def _render_detail_modal_body(
    pi, *, is_online, status_class, status_text, net_badge, app_name,
    uptime, last_seen_str, cpu, mem, disk, mem_display, disk_display,
    cpu_cls, mem_cls, disk_cls, card_id
):
    """Build untruncated HTML for the click-to-expand detail popup card."""
    hostname = _html.escape(str(pi.get('hostname', 'unknown')))
    local_ip = str(pi.get('local_ip', 'unknown'))
    raw_model = pi.get('cpu_model', 'Unknown')
    raw_os = pi.get('os_version', 'Unknown')
    description = pi.get('description', '')
    notes = pi.get('notes', '')

    mem_used_mb = int(round(_num(pi.get('memory_used_mb', 0))))
    mem_total_mb = int(round(_num(pi.get('memory_total_mb', 0))))
    mem_detail = (
        f"{mem}% ({mem_used_mb} / {mem_total_mb} MB)"
        if mem_total_mb > 0 else f"{mem}%"
    )

    disk_used_gb = int(round(_num(pi.get('disk_used_gb', 0))))
    disk_total_gb = int(round(_num(pi.get('disk_total_gb', 0))))
    disk_detail = (
        f"{disk}% ({disk_used_gb} / {disk_total_gb} GB)"
        if disk_total_gb > 0 else f"{disk}%"
    )

    desc_html = (
        f'<div class="detail-desc">{_html.escape(str(description))}</div>'
        if description else ''
    )

    metrics_html = ''
    if is_online:
        metrics_html = f'''
        <div class="detail-metrics">
            <div class="metric">
                <div class="metric-value {cpu_cls}">{cpu}%</div>
                <div class="metric-bar"><div class="metric-fill {cpu_cls}" style="width: {min(cpu, 100)}%;"></div></div>
                <div class="metric-label">CPU</div>
            </div>
            <div class="metric">
                <div class="metric-value {mem_cls}">{mem_detail}</div>
                <div class="metric-bar"><div class="metric-fill {mem_cls}" style="width: {min(mem, 100)}%;"></div></div>
                <div class="metric-label">Memory</div>
            </div>
            <div class="metric">
                <div class="metric-value {disk_cls}">{disk_detail}</div>
                <div class="metric-bar"><div class="metric-fill {disk_cls}" style="width: {min(disk, 100)}%;"></div></div>
                <div class="metric-label">Disk</div>
            </div>
        </div>
        '''

    rows = [
        _detail_row("Local IP", local_ip),
        _detail_row("App", app_name),
        _detail_row("Uptime", uptime),
        _detail_row("Last Seen", f"{last_seen_str} ({pi.get('last_seen', '')})"),
        _detail_row("Model", raw_model, full=True),
        _detail_row("OS", raw_os, full=True),
    ]
    if pi.get('wifi_interface'):
        rows.append(_detail_row("WiFi", pi.get('wifi_interface'), full=True))
    if pi.get('tunnel_active'):
        bastion = pi.get('bastion_host', 'homepi')
        rows.append(_detail_row("SSH Tunnel", f"Active: Port {pi.get('tunnel_port', 0)} via {bastion}", full=True))
    elif pi.get('tunnel_port') and str(pi.get('bastion_host', 'none')) not in ('none', 'unknown', ''):
        rows.append(_detail_row("SSH Tunnel", f"Inactive (port {pi.get('tunnel_port')})", full=False))
    if card_id and card_id != 'unknown' and card_id != pi.get('hostname'):
        rows.append(_detail_row("Card ID", card_id))
    if pi.get('board_revision'):
        rows.append(_detail_row("Board Rev", pi.get('board_revision')))
    if pi.get('hardware_serial'):
        rows.append(_detail_row("HW Serial", pi.get('hardware_serial')))
    if pi.get('sd_cid'):
        rows.append(_detail_row("SD CID", pi.get('sd_cid'), full=True))
    if pi.get('boot_time'):
        rows.append(_detail_row("Boot Time", pi.get('boot_time'), full=True))
    if notes:
        rows.append(_detail_row("Notes", notes, full=True))

    extra_html = ''
    boot_progress = pi.get('boot_progress') or pi.get('stage')
    if boot_progress and str(boot_progress).startswith('boot'):
        message = pi.get('message', 'Provisioning in progress...')
        extra_html += f'''
        <div class="boot-progress">
            <strong>\U0001f504 Boot Progress:</strong> {_html.escape(str(boot_progress))}: {_html.escape(str(message))}
        </div>
        '''
    error = pi.get('error')
    if error:
        extra_html += f'''
        <div class="error-box">
            <strong>\u26a0\ufe0f Error:</strong> {_html.escape(str(error))}
        </div>
        '''

    return f'''
        <div class="detail-header">
            <div class="pi-title-group">
                <div class="detail-hostname">{hostname}</div>
                {net_badge}
                <div class="pi-status {status_class}">{status_text} &bull; {last_seen_str}</div>
            </div>
            <button type="button" class="detail-close" onclick="closePiModal()" aria-label="Close">&times;</button>
        </div>
        {desc_html}
        {metrics_html}
        <div class="detail-grid">
            {''.join(r for r in rows if r)}
        </div>
        {extra_html}
    '''


def _render_card(pi, *, is_online, format_uptime, format_age, format_to_sigfigs):
    """Build compact HTML for a single fleet host card, with click-to-expand detail template."""
    hostname = pi.get('hostname', 'unknown')
    status_class = 'status-online' if is_online else 'status-offline'
    status_text = 'Online' if is_online else 'Offline'

    # Card ID: Use card_id if set, otherwise last 4 digits of SD CID
    card_id = pi.get('card_id', 'unknown')
    if card_id == 'unknown' or not card_id:
        sd_cid = pi.get('sd_cid', '')
        if sd_cid and len(sd_cid) >= 4:
            card_id = sd_cid[-4:]
        else:
            card_id = 'unknown'

    local_ip = str(pi.get('local_ip', 'unknown'))
    expected_app = pi.get('expected_app')
    app_name = pi.get('app_name', 'unknown')
    if expected_app and expected_app != 'unknown':
        app_name = expected_app
    elif app_name == 'unknown' and expected_app:
        app_name = expected_app

    uptime = format_uptime(int(_num(pi.get('uptime_seconds', 0))))

    cpu = int(round(_num(pi.get('cpu_percent', 0))))
    mem = int(round(_num(pi.get('memory_percent', 0))))
    disk = int(round(_num(pi.get('disk_percent', 0))))

    mem_cap = _fmt_cap_mb(pi.get('memory_total_mb', 0), format_to_sigfigs)
    mem_display = f"{mem}% <span class='metric-sub'>of {mem_cap}</span>" if mem_cap else f"{mem}%"

    disk_cap = _fmt_cap_gb(pi.get('disk_total_gb', 0), format_to_sigfigs)
    disk_display = f"{disk}% <span class='metric-sub'>of {disk_cap}</span>" if disk_cap else f"{disk}%"

    last_seen_str = format_age(pi.get('last_seen', 'Never'))
    net_badge = _net_badge(local_ip)

    raw_model = pi.get('cpu_model', 'Unknown')
    short_model = _short_model(raw_model)
    raw_os = pi.get('os_version', 'Unknown')
    short_os = _short_os(raw_os)

    cpu_cls = _usage_class(cpu)
    mem_cls = _usage_class(mem)
    disk_cls = _usage_class(disk)

    card_offline_cls = '' if is_online else ' pi-card-offline'
    safe_host_attr = _html.escape(str(hostname), quote=True)

    html = f'''
    <div class="pi-card{card_offline_cls}" data-hostname="{safe_host_attr}" tabindex="0" role="button" aria-label="View details for {safe_host_attr}" onclick="openPiModal(this)" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();openPiModal(this);}}">
        <div class="pi-header">
            <div class="pi-title-group">
                <div class="pi-hostname">{hostname}</div>
                {net_badge}
            </div>
            <div class="pi-status {status_class}" title="Last seen {last_seen_str}">{status_text} &bull; {last_seen_str}</div>
        </div>
    '''

    if is_online:
        html += f'''
        <div class="metrics">
            <div class="metric">
                <div class="metric-value {cpu_cls}">{cpu}%</div>
                <div class="metric-bar"><div class="metric-fill {cpu_cls}" style="width: {min(cpu, 100)}%;"></div></div>
                <div class="metric-label">CPU</div>
            </div>
            <div class="metric">
                <div class="metric-value {mem_cls}">{mem_display}</div>
                <div class="metric-bar"><div class="metric-fill {mem_cls}" style="width: {min(mem, 100)}%;"></div></div>
                <div class="metric-label">Memory</div>
            </div>
            <div class="metric">
                <div class="metric-value {disk_cls}">{disk_display}</div>
                <div class="metric-bar"><div class="metric-fill {disk_cls}" style="width: {min(disk, 100)}%;"></div></div>
                <div class="metric-label">Disk</div>
            </div>
        </div>
        '''

    # Keep "Local IP" followed by the value on the next line for resolve-host's _pifleet parser
    html += f'''
        <div class="pi-info">
            <div class="info-item">
                <div class="info-label">Local IP</div>
                <div class="info-value">{local_ip}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Uptime</div>
                <div class="info-value">{uptime}</div>
            </div>
            <div class="info-item">
                <div class="info-label">App</div>
                <div class="info-value" title="{app_name}">{app_name}</div>
            </div>
            <div class="info-item">
                <div class="info-label">OS</div>
                <div class="info-value" title="{raw_os}">{short_os}</div>
            </div>
            <div class="info-item info-span-row">
                <div class="info-label">Model</div>
                <div class="info-value" title="{raw_model}">{short_model}</div>
            </div>
    '''

    if card_id and card_id != 'unknown' and card_id != hostname:
        html += f'''
            <div class="info-item">
                <div class="info-label">Card</div>
                <div class="info-value">{card_id}</div>
            </div>
        '''

    if pi.get('wifi_interface'):
        wifi = pi.get('wifi_interface')
        html += f'''
            <div class="info-item">
                <div class="info-label">WiFi</div>
                <div class="info-value" title="{wifi}">{wifi}</div>
            </div>
        '''

    tunnel_active = pi.get('tunnel_active', False)
    if tunnel_active:
        bastion = pi.get('bastion_host', 'homepi')
        html += f'''
            <div class="info-item info-span-row">
                <div class="info-label">SSH Tunnel</div>
                <div class="info-value">Port {pi.get('tunnel_port', 0)} ({bastion})</div>
            </div>
        '''

    html += '</div>'

    boot_progress = pi.get('boot_progress') or pi.get('stage')
    if boot_progress and boot_progress.startswith('boot'):
        message = pi.get('message', 'Provisioning in progress...')
        html += f'''
        <div class="boot-progress">
            <strong>\U0001f504 Boot Progress:</strong> {boot_progress}: {message}
        </div>
        '''

    error = pi.get('error')
    if error:
        html += f'''
        <div class="error-box">
            <strong>\u26a0\ufe0f Error:</strong> {error[:200]}{'...' if len(error) > 200 else ''}
        </div>
        '''

    detail_body = _render_detail_modal_body(
        pi,
        is_online=is_online,
        status_class=status_class,
        status_text=status_text,
        net_badge=net_badge,
        app_name=app_name,
        uptime=uptime,
        last_seen_str=last_seen_str,
        cpu=cpu,
        mem=mem,
        disk=disk,
        mem_display=mem_display,
        disk_display=disk_display,
        cpu_cls=cpu_cls,
        mem_cls=mem_cls,
        disk_cls=disk_cls,
        card_id=card_id,
    )
    html += f'<template class="pi-detail-tpl">{detail_body}</template>'
    html += '</div>'
    return html


def _compute_fleet_stats(pis, *, is_pi_online, format_uptime):
    """Aggregate fleet-wide metrics for the summary pane."""
    online_pis = [p for p in pis if is_pi_online(p.get('last_seen'))]
    active = online_pis if online_pis else pis

    if not active:
        return {
            "avg_cpu": "0%",
            "cpu_sub": "no hosts",
            "mem_summary": "0%",
            "mem_sub": "0 / 0 GB",
            "disk_summary": "0%",
            "disk_sub": "0 / 0 GB",
            "uptime_summary": "–",
            "uptime_sub": "no hosts",
            "topology_sub": "0 LAN · 0 cloud",
        }

    # CPU stats
    cpus = [(int(round(_num(p.get('cpu_percent', 0)))), p.get('hostname', '?')) for p in active]
    avg_cpu = int(round(sum(c for c, _ in cpus) / len(cpus)))
    max_cpu, max_cpu_host = max(cpus, key=lambda x: x[0])
    cpu_sub = f"max {max_cpu}% ({max_cpu_host})"

    # Memory stats (aggregate across fleet)
    mem_total_mb = sum(_num(p.get('memory_total_mb', 0)) for p in active)
    mem_used_mb = sum(
        _num(p.get('memory_used_mb'), _num(p.get('memory_total_mb', 0)) * _num(p.get('memory_percent', 0)) / 100.0)
        for p in active
    )
    mem_pcts = [(int(round(_num(p.get('memory_percent', 0)))), p.get('hostname', '?')) for p in active]
    max_mem, max_mem_host = max(mem_pcts, key=lambda x: x[0])
    if mem_total_mb > 0:
        fleet_mem_pct = int(round(100.0 * mem_used_mb / mem_total_mb))
        mem_summary = f"{fleet_mem_pct}%"
        mem_sub = f"{mem_used_mb / 1024:.1f}/{mem_total_mb / 1024:.1f}G · max {max_mem}% ({max_mem_host})"
    else:
        avg_mem = int(round(sum(m for m, _ in mem_pcts) / len(mem_pcts)))
        mem_summary = f"{avg_mem}%"
        mem_sub = f"max {max_mem}% ({max_mem_host})"

    # Disk stats (aggregate across fleet)
    disk_total_gb = sum(_num(p.get('disk_total_gb', 0)) for p in active)
    disk_used_gb = sum(
        _num(p.get('disk_used_gb'), _num(p.get('disk_total_gb', 0)) * _num(p.get('disk_percent', 0)) / 100.0)
        for p in active
    )
    disk_pcts = [(int(round(_num(p.get('disk_percent', 0)))), p.get('hostname', '?')) for p in active]
    max_disk, max_disk_host = max(disk_pcts, key=lambda x: x[0])
    if disk_total_gb > 0:
        fleet_disk_pct = int(round(100.0 * disk_used_gb / disk_total_gb))
        disk_summary = f"{fleet_disk_pct}%"
        disk_sub = f"{int(round(disk_used_gb))}/{int(round(disk_total_gb))}G · max {max_disk}% ({max_disk_host})"
    else:
        avg_disk = int(round(sum(d for d, _ in disk_pcts) / len(disk_pcts)))
        disk_summary = f"{avg_disk}%"
        disk_sub = f"max {max_disk}% ({max_disk_host})"

    # Uptime stats (shortest = most recent boot, longest = most stable)
    uptimes = [
        (int(_num(p.get('uptime_seconds', 0))), p.get('hostname', '?'))
        for p in active
        if _num(p.get('uptime_seconds', 0)) > 0
    ]
    if uptimes:
        min_up, min_up_host = min(uptimes, key=lambda x: x[0])
        max_up, max_up_host = max(uptimes, key=lambda x: x[0])
        uptime_summary = format_uptime(min_up)
        uptime_sub = f"newest: {min_up_host} · max {format_uptime(max_up)} ({max_up_host})"
    else:
        uptime_summary = "–"
        uptime_sub = "unknown"

    # Topology & tunnels
    cloud_count = sum(
        1 for p in pis
        if str(p.get('local_ip', '')).startswith(('100.', '10.'))
    )
    lan_count = len(pis) - cloud_count
    tunnels = sum(1 for p in active if p.get('tunnel_active'))
    topology_sub = f"{lan_count} LAN · {cloud_count} cloud · {tunnels} tun"

    return {
        "avg_cpu": f"{avg_cpu}%",
        "cpu_sub": cpu_sub,
        "mem_summary": mem_summary,
        "mem_sub": mem_sub,
        "disk_summary": disk_summary,
        "disk_sub": disk_sub,
        "uptime_summary": uptime_summary,
        "uptime_sub": uptime_sub,
        "topology_sub": topology_sub,
    }


def render_pi_fleet_page(pis, *, is_pi_online, format_uptime, format_age,
                         format_to_sigfigs, theme_css_js):
    """Render the Pi Fleet dashboard HTML."""
    online_count = sum(1 for pi in pis if is_pi_online(pi.get('last_seen')))
    offline_count = len(pis) - online_count
    stats = _compute_fleet_stats(
        pis, is_pi_online=is_pi_online, format_uptime=format_uptime
    )

    if not pis:
        cards_html = '''
        <div class="empty-state">
            <h2>No Devices Found</h2>
            <p>No Raspberry Pis have reported their status yet.</p>
            <p>Make sure the pi-fleet-reporter service is running on your devices.</p>
        </div>
        '''
    else:
        cards = []
        for pi in pis:
            online = is_pi_online(pi.get('last_seen'))
            cards.append(_render_card(
                pi, is_online=online,
                format_uptime=format_uptime,
                format_age=format_age,
                format_to_sigfigs=format_to_sigfigs,
            ))
        cards_html = '<div class="pi-grid">' + ''.join(cards) + '</div>'

    template = _load_template("pi_fleet.html")
    return template.format(
        theme_css_js=theme_css_js,
        online_count=online_count,
        offline_count=offline_count,
        total_count=len(pis),
        cards_html=cards_html,
        **stats,
    )
