"""Extracted from mywebsite.py."""

def render_srfcplus_page():
    """Render the SRFC Plus companion page, styled to match the real ManageOurClub portal."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Bookings — Surbiton Racket &amp; Fitness Club</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: "Quicksand", "Open Sans", Verdana, Arial, sans-serif; font-size: 13px; background: #f5f7fa; color: #333; min-height: 100vh; }

    /* ── Navbar ── */
    .navbar { background: #23408f; min-height: 60px; display: flex; align-items: center; padding: 0 20px; border-bottom: 1px solid #1a3070; }
    .navbar-logo { display: flex; align-items: center; }
    .navbar-logo img { max-height: 40px; }
    .navbar-right { margin-left: auto; display: flex; align-items: center; gap: 16px; }
    .navbar-right a { color: #ddd; text-decoration: none; font-size: 12px; font-weight: 600; }
    .navbar-right a:hover { color: #fff; }
    .navbar-right .btn-signout { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 5px 12px; border-radius: 3px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 600; }
    .navbar-right .btn-signout:hover { background: rgba(255,255,255,0.25); }

    /* ── Sub-nav tabs ── */
    .subnav { background: #fff; border-bottom: 1px solid #ddd; padding: 0 20px; display: flex; gap: 0; }
    .subnav a { display: inline-block; padding: 12px 16px; font-size: 12px; font-weight: 600; color: #555; text-decoration: none; border-bottom: 3px solid transparent; }
    .subnav a:hover { color: #23408f; border-bottom-color: #619fe0; }
    .subnav a.active { color: #23408f; border-bottom-color: #23408f; }

    /* ── Page container ── */
    .container { max-width: 960px; margin: 24px auto; padding: 0 20px; }

    /* ── Page title ── */
    .page-title { font-size: 22px; font-weight: 700; color: #23408f; margin-bottom: 4px; }
    .page-subtitle { color: #888; font-size: 12px; margin-bottom: 20px; }

    /* ── Bookings table ── */
    .panel { background: #fff; border: 1px solid #e5e5e5; border-radius: 4px; margin-bottom: 20px; }
    .panel-heading { background: #f5f5f5; border-bottom: 1px solid #e5e5e5; padding: 10px 16px; font-weight: 700; font-size: 13px; color: #333; border-radius: 4px 4px 0 0; display: flex; justify-content: space-between; align-items: center; }
    .panel-body { padding: 0; }
    table.bookings { width: 100%; border-collapse: collapse; font-size: 12px; }
    table.bookings th { background: #f9f9f9; color: #555; font-weight: 700; text-align: left; padding: 9px 14px; border-bottom: 1px solid #e5e5e5; white-space: nowrap; }
    table.bookings td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
    table.bookings tr:last-child td { border-bottom: none; }
    table.bookings tr:hover td { background: #fafbff; }
    .badge-confirmed { display: inline-block; background: #65b589; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .badge-pending { display: inline-block; background: #f0ad4e; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700; text-transform: uppercase; }

    /* ── Status messages ── */
    .status-msg { padding: 20px; text-align: center; color: #888; font-size: 13px; }
    .status-msg.error { color: #c60f13; }
    .loading-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #ddd; border-top-color: #23408f; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Cookie config panel ── */
    .config-toggle { font-size: 11px; color: #2ba6cb; cursor: pointer; text-decoration: underline; background: none; border: none; font-family: inherit; padding: 0; }
    .config-panel { display: none; padding: 14px 16px; background: #fffef0; border-top: 1px solid #e5e5e5; }
    .config-panel.open { display: block; }
    .config-panel label { display: block; font-weight: 700; font-size: 11px; color: #555; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.04em; }
    .config-panel textarea { width: 100%; font-family: monospace; font-size: 11px; border: 1px solid #ddd; border-radius: 3px; padding: 7px; resize: vertical; min-height: 60px; color: #333; }
    .config-panel .hint { font-size: 11px; color: #888; margin-top: 5px; line-height: 1.5; }
    .config-panel .btn-row { display: flex; gap: 8px; margin-top: 10px; }
    .btn-primary { background: #2ba6cb; color: #fff; border: 1px solid #2285a2; padding: 7px 16px; border-radius: 3px; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
    .btn-primary:hover { background: #2285a2; }
    .btn-secondary { background: #e9e9e9; color: #333; border: 1px solid #bababa; padding: 7px 16px; border-radius: 3px; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
    .btn-secondary:hover { background: #bababa; }

    /* ── Footer ── */
    .footer { text-align: center; padding: 20px; color: #aaa; font-size: 11px; border-top: 1px solid #e5e5e5; margin-top: 20px; }
    .footer a { color: #2ba6cb; text-decoration: none; }

    @media (max-width: 600px) {
      .subnav { overflow-x: auto; }
      table.bookings th, table.bookings td { padding: 8px 10px; }
      .container { padding: 0 10px; }
    }
  </style>
</head>
<body>

  <!-- Navbar -->
  <nav class="navbar">
    <div class="navbar-logo">
      <img src="https://backoffice.mysurbitonracketfitness.com/imageorganisation/pageheaderlogo/moc_surbiton_live_orgbannerlogo.png" alt="Surbiton Racket &amp; Fitness Club">
    </div>
    <div class="navbar-right">
      <a href="https://www.mysurbitonracketfitness.com/pages/homepage.aspx" target="_blank">Full Portal ↗</a>
      <a href="/contents">petergrecian.co.uk</a>
    </div>
  </nav>

  <!-- Sub-nav -->
  <div class="subnav">
    <a href="#" class="active">My Bookings</a>
    <a href="https://www.mysurbitonracketfitness.com/pages/user/detailsummary.aspx" target="_blank">My Details</a>
    <a href="https://www.mysurbitonracketfitness.com/pages/checkout/cartdetails.aspx" target="_blank">Shopping Cart</a>
  </div>

  <div class="container">
    <div class="page-title">My Padel Bookings</div>
    <div class="page-subtitle">Padel court reservations — loaded directly from the portal</div>

    <div class="panel">
      <div class="panel-heading">
        <span>Bookings</span>
        <button class="config-toggle" onclick="toggleConfig()">⚙ Cookie settings</button>
      </div>

      <!-- Cookie config (hidden by default) -->
      <div class="config-panel" id="configPanel">
        <label>ASP.NET_SessionId cookie</label>
        <textarea id="cookieInput" placeholder="Paste your full cookie string here&#10;e.g. ASP.NET_SessionId=abc123xyz..."></textarea>
        <p class="hint">Log into <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>, then open DevTools (F12) → Application → Storage → Cookies → <strong>www.mysurbitonracketfitness.com</strong>. Copy the <strong>ASP.NET_SessionId</strong> value (and <strong>.ASPXAUTH</strong> if present) and paste in the format:<br><code>ASP.NET_SessionId=abc123; .ASPXAUTH=xyz...</code><br>Stored only in your browser, never sent to this server except to proxy the request.</p>
        <div class="btn-row">
          <button class="btn-primary" onclick="saveCookie()">Save &amp; Reload</button>
          <button class="btn-secondary" onclick="clearCookie()">Clear</button>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-msg" id="statusMsg">
          <span class="loading-spinner"></span> Loading bookings…
        </div>
        <table class="bookings" id="bookingsTable" style="display:none">
          <thead id="bookingsHead"></thead>
          <tbody id="bookingsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="footer">
    SRFC Plus — faster view of <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>
  </div>

  <script>
    const COOKIE_KEY = 'srfcplus_cookie';
    const escHtml = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    function toggleConfig() {
      const p = document.getElementById('configPanel');
      p.classList.toggle('open');
      if (p.classList.contains('open')) {
        const saved = localStorage.getItem(COOKIE_KEY);
        if (saved) document.getElementById('cookieInput').value = saved;
      }
    }

    function saveCookie() {
      const val = document.getElementById('cookieInput').value.trim();
      if (!val) { alert('Please paste your cookie first.'); return; }
      localStorage.setItem(COOKIE_KEY, val);
      document.getElementById('configPanel').classList.remove('open');
      loadBookings(val);
    }

    function clearCookie() {
      localStorage.removeItem(COOKIE_KEY);
      document.getElementById('cookieInput').value = '';
      showStatus('Cookie cleared. Paste a new cookie to load bookings.');
    }

    function showStatus(msg, isError) {
      const el = document.getElementById('statusMsg');
      el.innerHTML = msg;
      el.className = 'status-msg' + (isError ? ' error' : '');
      el.style.display = '';
      document.getElementById('bookingsTable').style.display = 'none';
    }

    function loadBookings(cookie) {
      showStatus('<span class="loading-spinner"></span> Loading bookings…');

      fetch('/srfcplus/bookings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({cookie: cookie})
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) { showStatus('⚠ ' + escHtml(data.error), true); return; }

          const bookings = data.bookings || [];
          if (!bookings.length) {
            showStatus(escHtml(data.note || 'No upcoming bookings found.'));
            return;
          }

          const thead = document.getElementById('bookingsHead');
          const tbody = document.getElementById('bookingsBody');
          thead.innerHTML = '<tr><th>Court / Event</th><th>Date</th><th>Time</th></tr>';
          tbody.innerHTML = '';

          bookings.forEach(b => {
            const tr = document.createElement('tr');
            const title = b.court || b.label || b.description || '';
            const when  = b.event_date || b.date || '';
            const time  = (b.start && b.end) ? b.start + '\u2013' + b.end : '';
            tr.innerHTML =
              '<td><strong>' + escHtml(title) + '</strong></td>' +
              '<td>' + escHtml(when) + '</td>' +
              '<td>' + escHtml(time) + '</td>';
            tbody.appendChild(tr);
          });

          document.getElementById('statusMsg').style.display = 'none';
          document.getElementById('bookingsTable').style.display = '';
        })
        .catch(e => showStatus('⚠ Request failed: ' + escHtml(e.message), true));
    }

    window.addEventListener('DOMContentLoaded', () => {
      const saved = localStorage.getItem(COOKIE_KEY);
      if (saved) {
        loadBookings(saved);
      } else {
        showStatus('No cookie saved yet — click <strong>⚙ Cookie settings</strong> above to get started.');
        document.getElementById('configPanel').classList.add('open');
      }
    });
  </script>
</body>
</html>'''


