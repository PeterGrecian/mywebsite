"""Contents/navigation page."""

import sys


def render_contents_page(*, theme_css_js, private=False):
    """Render the contents/navigation page from DynamoDB mywebsite-contents table.

    Two audiences, one table, two independent flags:

      visible=False       retired or broken — off BOTH pages.
      auth_required=True  private — shown only on /my-contents, never on the
                          public /contents.

    `auth_required` used to only add a PRIVATE badge, which left the public
    page advertising exactly what it was withholding. It now filters as well,
    and the badge survives on the private page where it is useful: it marks
    which links will ask for a password.
    """
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

    # visible=False is retirement — off both pages.
    items = [i for i in items if i.get('visible', True)]
    # auth_required is privacy — private page only.
    if not private:
        items = [i for i in items if not i.get('auth_required')]

    # header_link entries are not projects, so they are not cards: they are
    # links under the name. Biography is the case that prompted it — a card
    # in a list of things I built reads as another project.
    header_items = [i for i in items if i.get('header_link')]
    items = [i for i in items if not i.get('header_link')]
    header_html = ""
    if header_items:
        links = "".join(
            f'<a href="/{i.get("path", "").lstrip("/")}">{i.get("title", "")}</a>'
            for i in header_items)
        header_html = f'    <div class="header-nav">{links}</div>\n'

    # Build the cards.
    #
    # A card is a <div>, not an <a>, because some entries carry a second,
    # independent link (Sky Camera points at the YouTube channel as well as
    # at the page) and nested anchors are invalid HTML. The whole card is
    # still clickable: .card-title::after stretches over the card, and
    # .card-extra sits above it on z-index so the second link still wins its
    # own clicks.
    #
    # image_url is optional and a card works with or without one. The ones
    # that have it point at s3://www.petergrecian.co.uk/assets/cards/<name>.jpg,
    # served straight from the S3 hostname with a 7-day Cache-Control. That
    # hostname is not in the Cloudflare zone, so replacing an image in place
    # does not purge anyone's browser cache: change the bytes and returning
    # visitors keep the old picture for up to a week. Give it a new filename
    # instead when that matters.
    links_html = ""
    for item in items:
        path = item.get('path', '/')
        external = item.get('external_url')
        href = external if external else ('/' + path.lstrip('/'))
        title = item.get('title', '')
        description = item.get('description', '')
        image_url = item.get('image_url')
        extra_url = item.get('extra_url')
        extra_label = item.get('extra_label', '')
        private_badge = ('<sup class="badge">PRIVATE</sup>'
                         if item.get('auth_required') else '')
        img = (f'        <img class="card-img" src="{image_url}" alt="">\n'
               if image_url else '')
        extra = (f'        <a class="card-extra" href="{extra_url}" '
                 f'target="_blank" rel="noopener">{extra_label}</a>\n'
                 if extra_url else '')
        links_html += f'''      <div class="card">
{img}        <div class="card-body">
          <a class="card-title" href="{href}">{title}{private_badge}</a>
          <span class="description">{description}</span>
{extra}        </div>
      </div>\n'''

    # noindex on the private page: it is behind Basic Auth, so a crawler
    # cannot read it, but there is no reason for the URL itself to be indexed.
    page_title = "Peter Grecian — private" if private else "Peter Grecian"
    robots_meta = ('\n    <meta name="robots" content="noindex,nofollow">'
                   if private else "")

    return f'''<html lang="en">
  <head>
    <title>{page_title}</title>{robots_meta}
    <style>
      body {{ font-family: var(--font); text-align: center; background: var(--bg); min-height: 100vh; margin: 0; padding: 2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text); }}
      h1 {{ color: var(--text); font-size: 2.5rem; margin-bottom: 2rem; }}
      .links-container {{ display: flex; flex-direction: column; gap: 1.5rem; width: 100%; max-width: 560px; }}
      /* Cards, not pills. A pill has to stay short, which forced every
         description into a cramped second line; a card gives the text room
         and leaves space for an image. */
      .card {{ position: relative; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 12px; overflow: hidden; text-align: left; transition: opacity 0.2s; }}
      .card:hover {{ opacity: 0.85; }}
      .card-img {{ display: block; width: 100%; height: 140px; object-fit: cover; background: var(--divider); }}
      .card-body {{ padding: 0.9rem 1.1rem; }}
      .card-title {{ display: block; color: var(--accent); text-decoration: none; font-size: 1.1rem; font-weight: 500; }}
      /* Stretches the title's hit area over the whole card, so the card is
         clickable without nesting anchors. */
      .card-title::after {{ content: ""; position: absolute; inset: 0; }}
      .card .description {{ display: block; font-size: 0.85rem; margin-top: 0.25rem; color: var(--text-secondary); line-height: 1.45; }}
      /* Above the stretched title, so a second link keeps its own clicks. */
      .card-extra {{ position: relative; z-index: 1; display: inline-block; margin-top: 0.6rem; font-size: 0.8rem; color: var(--accent); text-decoration: none; border: 1px solid var(--divider); border-radius: 20px; padding: 0.3rem 0.8rem; }}
      .card-extra:hover {{ background: var(--divider); }}
      .badge {{ font-size: 0.55em; vertical-align: super; color: var(--text-secondary); font-weight: 400; letter-spacing: 0.05em; }}
      .tagline {{ color: var(--text-secondary); font-size: 1rem; line-height: 1.5; max-width: 560px; margin: -1.4rem 0 1.5rem; }}
      .tagline a {{ color: var(--accent); text-decoration: none; }}
      .tagline a:hover {{ opacity: 0.8; }}
      .header-nav {{ display: flex; gap: 0.8rem; justify-content: center; margin-bottom: 1.5rem; flex-wrap: wrap; }}
      .header-nav a {{ color: var(--accent); text-decoration: none; font-size: 1rem; border-bottom: 1px solid var(--divider); padding-bottom: 0.15rem; }}
      .header-nav a:hover {{ opacity: 0.8; }}
      .footer-nav {{ display: flex; gap: 1rem; justify-content: center; margin-top: 2rem; flex-wrap: wrap; }}
      .footer-nav a {{ display: inline-block; padding: 0.5rem 1.25rem; border-radius: 50px; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); text-decoration: none; font-size: 0.85rem; word-break: break-all; max-width: 100%; transition: opacity 0.2s; }}
      .footer-nav a:hover {{ opacity: 0.8; }}
      .colophon {{ margin-top: 2.5rem; color: var(--text-secondary); font-size: 0.8rem; max-width: 500px; line-height: 1.5; }}
      @media (max-width: 768px) {{ h1 {{ font-size: 2rem; margin-bottom: 1.5rem; }} .card-body {{ padding: 0.8rem 0.9rem; }} .card-title {{ font-size: 1rem; }} .card-img {{ height: 110px; }} }}
    </style>
    {theme_css_js}
  </head>
  <body>
    <h1>Peter Grecian</h1>
    <p class="tagline">Cloud and DevOps engineer. I build and share the strands
      method for working effectively with AI.
      <a href="https://www.linkedin.com/in/peter-grecian-1700a317/"
         target="_blank" rel="noopener">LinkedIn</a></p>
{header_html}    <div class="links-container">
{links_html}    </div>
    <div class="footer-nav">
      <a href="https://github.com/PeterGrecian" target="_blank" rel="noopener">https://github.com/PeterGrecian</a>
    </div>
    <p class="colophon">This website is powered by API Gateway, Python
      Lambda, DynamoDB and Cloudflare.</p>
  </body>
</html>'''
