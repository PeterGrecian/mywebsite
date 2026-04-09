"""Pi Fleet dashboard route handler."""

import os

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def _load_template(name):
    with open(os.path.join(_TEMPLATE_DIR, name)) as f:
        return f.read()


def _render_card(pi, *, is_online, format_uptime, format_age, format_to_sigfigs):
    """Build HTML for a single Pi card."""
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

    local_ip = pi.get('local_ip', 'unknown')
    app_name = pi.get('app_name', 'unknown')
    if app_name == 'unknown':
        app_name = pi.get('expected_app', 'unknown')
    uptime = format_uptime(pi.get('uptime_seconds', 0))

    cpu = pi.get('cpu_percent', 0)
    mem = pi.get('memory_percent', 0)
    disk = pi.get('disk_percent', 0)

    # Format memory with total
    mem_total_mb = pi.get('memory_total_mb', 0)
    if mem_total_mb > 0:
        if mem_total_mb < 1024:
            val = format_to_sigfigs(mem_total_mb, 3)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            mem_display = f"{mem}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {val}M</span>"
        else:
            val = format_to_sigfigs(mem_total_mb / 1024, 3)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            mem_display = f"{mem}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {val}G</span>"
    else:
        mem_display = f"{mem}%"

    # Format disk with total
    disk_total_gb = pi.get('disk_total_gb', 0)
    if disk_total_gb > 0:
        if disk_total_gb < 1:
            val = format_to_sigfigs(disk_total_gb * 1024, 3)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            disk_display = f"{disk}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {val}M</span>"
        else:
            val = format_to_sigfigs(disk_total_gb, 3)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            disk_display = f"{disk}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {val}G</span>"
    else:
        disk_display = f"{disk}%"

    last_seen_str = format_age(pi.get('last_seen', 'Never'))

    html = f'''
    <div class="pi-card">
        <div class="pi-header">
            <div class="pi-hostname">{hostname}</div>
            <div class="pi-status {status_class}">{status_text}</div>
        </div>

        <div class="pi-info">
            <div class="info-item">
                <div class="info-label">Model</div>
                <div class="info-value" style="font-size: 0.75em;">{pi.get('cpu_model', 'Unknown')}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Card ID</div>
                <div class="info-value">{card_id}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Local IP</div>
                <div class="info-value">{local_ip}</div>
            </div>
            <div class="info-item">
                <div class="info-label">App</div>
                <div class="info-value">{app_name}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Uptime</div>
                <div class="info-value">{uptime}</div>
            </div>
            <div class="info-item" style="grid-column: 1 / -1;">
                <div class="info-label">OS</div>
                <div class="info-value" style="font-size: 0.75em;">{pi.get('os_version', 'Unknown')}</div>
            </div>
    '''

    if pi.get('wifi_interface'):
        html += f'''
            <div class="info-item" style="grid-column: 1 / -1;">
                <div class="info-label">WiFi</div>
                <div class="info-value" style="font-size: 0.75em;">{pi.get('wifi_interface')}</div>
            </div>
        '''

    tunnel_active = pi.get('tunnel_active', False)
    if tunnel_active:
        html += f'''
            <div class="info-item">
                <div class="info-label">SSH Tunnel</div>
                <div class="info-value">Port {pi.get('tunnel_port', 0)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Bastion</div>
                <div class="info-value">{pi.get('bastion_host', 'unknown')}</div>
            </div>
        '''

    html += f'''
            <div class="info-item" style="grid-column: 1 / -1;">
                <div class="info-label">Last Seen</div>
                <div class="info-value">{last_seen_str}</div>
            </div>
        </div>
    '''

    if is_online:
        html += f'''
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{cpu}%</div>
                <div class="metric-label">CPU</div>
            </div>
            <div class="metric">
                <div class="metric-value">{mem_display}</div>
                <div class="metric-label">Memory</div>
            </div>
            <div class="metric">
                <div class="metric-value">{disk_display}</div>
                <div class="metric-label">Disk</div>
            </div>
        </div>
        '''

    boot_progress = pi.get('boot_progress') or pi.get('stage')
    if boot_progress and boot_progress.startswith('boot'):
        message = pi.get('message', 'Provisioning in progress...')
        html += f'''
        <div class="boot-progress">
            <strong>\U0001f504 Boot Progress:</strong> {boot_progress}<br>
            {message}
        </div>
        '''

    error = pi.get('error')
    if error:
        html += f'''
        <div class="error-box">
            <strong>\u26a0\ufe0f Error:</strong><br>
            {error[:200]}{'...' if len(error) > 200 else ''}
        </div>
        '''

    html += '</div>'
    return html


def render_pi_fleet_page(pis, *, is_pi_online, format_uptime, format_age,
                         format_to_sigfigs, theme_css_js):
    """Render the Pi Fleet dashboard HTML."""
    online_count = sum(1 for pi in pis if is_pi_online(pi.get('last_seen')))
    offline_count = len(pis) - online_count

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
    )
