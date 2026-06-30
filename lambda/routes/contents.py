"""Contents/navigation page."""

import sys


def render_contents_page(*, theme_css_js):
    """Render the contents/navigation page from DynamoDB mywebsite-contents table."""
    boto3 = sys.modules.get("boto3")
    BOTO3_AVAILABLE = boto3 is not None
    GARDENCAM_REGION = "eu-west-1"
    MYWEBSITE_CONTENTS_TABLE = "mywebsite-contents"

    items = []
    if BOTO3_AVAILABLE:
        try:
            dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
            table = dynamodb.Table(MYWEBSITE_CONTENTS_TABLE)
            response = table.scan()
            items = response.get('Items', [])
        except Exception as e:
            print(f"Error reading {MYWEBSITE_CONTENTS_TABLE}: {e}")

    # Sort by sort_order
    items.sort(key=lambda x: int(x.get('sort_order', 999)))

    # Filter to visible items only
    items = [i for i in items if i.get('visible', True)]

    # Build links HTML
    links_html = ""
    for item in items:
        path = item.get('path', '/')
        external = item.get('external_url')
        href = external if external else ('/' + path.lstrip('/'))
        title = item.get('title', '')
        description = item.get('description', '')
        private_badge = '<sup style="font-size:0.55em; vertical-align:super; color:var(--text-secondary); font-weight:400; letter-spacing:0.05em;">PRIVATE</sup>' if item.get('auth_required') else ''
        links_html += f'''      <a href="{href}" class="link-ellipse">
        {title}{private_badge}
        <span class="description">{description}</span>
      </a>\n'''

    return f'''<html lang="en">
  <head>
    <title>Peter Grecian</title>
    <style>
      body {{ font-family: var(--font); text-align: center; background: var(--bg); min-height: 100vh; margin: 0; padding: 2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text); }}
      h1 {{ color: var(--text); font-size: 2.5rem; margin-bottom: 2rem; }}
      .links-container {{ display: flex; flex-direction: column; gap: 0.75rem; width: 100%; max-width: 500px; }}
      .link-ellipse {{ display: block; padding: 0.9rem 2rem; border-radius: 50px; text-decoration: none; font-size: 1.1rem; font-weight: 500; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); transition: opacity 0.2s; }}
      .link-ellipse:hover {{ opacity: 0.8; }}
      .link-ellipse .description {{ display: block; font-size: 0.8rem; margin-top: 0.2rem; color: var(--text-secondary); font-weight: normal; }}
      .hero-img {{ width: 100%; max-width: 500px; border-radius: 12px; margin-bottom: 1.5rem; object-fit: cover; max-height: 200px; }}
      .identity-footer {{ display: flex; gap: 1.5rem; justify-content: center; margin-top: 2rem; flex-wrap: wrap; }}
      .identity-footer a {{ color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; transition: color 0.2s; }}
      .identity-footer a:hover {{ color: var(--accent); }}
      @media (max-width: 768px) {{ h1 {{ font-size: 2rem; margin-bottom: 1.5rem; }} .link-ellipse {{ padding: 0.8rem 1.5rem; font-size: 1rem; }} }}
    </style>
    {theme_css_js}
  </head>
  <body>
    <img class="hero-img" src="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260113_100124014.jpg" alt="Waterloo station">
    <h1>Peter Grecian</h1>
    <div class="links-container">
{links_html}    </div>
    <div class="identity-footer">
      <a href="https://github.com/PeterGrecian" target="_blank" rel="noopener">GitHub</a>
      <a href="https://www.youtube.com/channel/UCXbk1ItK5B8RAqhUPNTX7zw" target="_blank" rel="noopener">Beautiful Clouds (YouTube)</a>
    </div>
  </body>
</html>'''
