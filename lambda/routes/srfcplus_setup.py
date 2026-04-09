"""Extracted from mywebsite.py."""

def render_srfcplus_setup_page(message=None, success=False):
    """Render the SRFC Plus cookie setup/update page in SRFC portal style."""
    msg_html = ''
    if message and not success:
        msg_html = f'<div class="alert alert-danger" style="margin-bottom:1rem;">{message}</div>'
    if success:
        msg_html = '<div class="alert alert-success" style="margin-bottom:1rem;">Cookie saved. <a href="/srfcplus">Go to SRFC Plus →</a></div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SRFC Plus — Setup</title>
  <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: "Quicksand","Open Sans",Verdana,Arial,sans-serif; font-size:13px; background:#f5f7fa; color:#333; margin:0; }}
    .navbar {{ background:#23408f; min-height:60px; display:flex; align-items:center; padding:0 20px; }}
    .navbar img {{ max-height:40px; }}
    .navbar a {{ color:#ddd; margin-left:auto; font-size:12px; font-weight:600; text-decoration:none; }}
    .container {{ max-width:560px; margin:40px auto; padding:0 20px; }}
    .panel {{ background:#fff; border:1px solid #e5e5e5; border-radius:4px; }}
    .panel-heading {{ background:#f5f5f5; border-bottom:1px solid #e5e5e5; padding:10px 16px; font-weight:700; font-size:13px; }}
    .panel-body {{ padding:20px; }}
    label {{ display:block; font-weight:700; font-size:11px; color:#555; margin-bottom:6px; text-transform:uppercase; letter-spacing:.04em; }}
    textarea {{ width:100%; box-sizing:border-box; font-family:monospace; font-size:11px; border:1px solid #ddd; border-radius:3px; padding:8px; resize:vertical; min-height:70px; }}
    .hint {{ font-size:11px; color:#888; margin-top:6px; line-height:1.5; }}
    .hint code {{ background:#f5f5f5; padding:1px 4px; border-radius:2px; font-size:10px; }}
    .btn {{ background:#2ba6cb; color:#fff; border:1px solid #2285a2; padding:8px 20px; border-radius:3px; font-family:inherit; font-size:13px; font-weight:700; cursor:pointer; margin-top:12px; }}
    .btn:hover {{ background:#2285a2; }}
    .alert-danger {{ background:#fdf2f2; border:1px solid #f5c6cb; color:#721c24; padding:10px 14px; border-radius:3px; font-size:12px; }}
    .alert-success {{ background:#f2fdf5; border:1px solid #c3e6cb; color:#155724; padding:10px 14px; border-radius:3px; font-size:12px; }}
    .alert-success a {{ color:#155724; }}
  </style>
</head>
<body>
  <nav class="navbar">
    <img src="https://backoffice.mysurbitonracketfitness.com/imageorganisation/pageheaderlogo/moc_surbiton_live_orgbannerlogo.png" alt="SRFC">
    <a href="/contents">petergrecian.co.uk</a>
  </nav>
  <div class="container">
    <h2 style="color:#23408f;margin-bottom:1.5rem;">SRFC Plus — Session Setup</h2>
    {msg_html}
    <div class="panel">
      <div class="panel-heading">Portal Session Cookie</div>
      <div class="panel-body">
        <form method="POST" action="/srfcplus/update-cookie">
          <label>Cookie string</label>
          <textarea name="cookie" placeholder="ASP.NET_SessionId=abc123; .ASPXAUTH=xyz..."></textarea>
          <p class="hint">
            Log in at <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>,
            then open DevTools (F12) → Application → Storage → Cookies →
            <strong>www.mysurbitonracketfitness.com</strong>.<br>
            Copy <code>ASP.NET_SessionId</code> and <code>.ASPXAUTH</code> and paste as:<br>
            <code>ASP.NET_SessionId=abc123; .ASPXAUTH=xyz...</code><br>
            Saved securely in AWS SSM — works from all devices.
          </p>
          <button type="submit" class="btn">Save Cookie</button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>'''


