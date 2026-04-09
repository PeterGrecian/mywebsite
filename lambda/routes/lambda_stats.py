"""Lambda stats page renderer."""

import os


def render_lambda_stats_page(*, theme_css_js):
    """Render the Lambda CloudWatch metrics page (static HTML shell that loads data via JS)."""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'lambda_stats.html')
    with open(template_path) as f:
        return f.read().format(theme_css_js=theme_css_js)
