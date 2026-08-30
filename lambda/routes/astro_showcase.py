"""Astro Photos Showcase — high-resolution curated astrophotography gallery.

Text and metadata live in Git (Markdown cards with YAML frontmatter).
High-resolution images and thumbnails live in S3 (s3://.../showcase/).
"""

from __future__ import annotations
import html

SHOWCASE_CATEGORIES = {
    "deep-sky": "Deep Sky",
    "milky-way": "Milky Way",
    "star-trails": "Star Trails",
    "derotated": "Polar Derotation",
    "widefield": "Widefield",
    "meteors": "Meteors & Fireballs",
    "solar-system": "Solar System",
    "lunar": "Moon & Planets",
    "other": "Other",
}


def showcase_category_counts(items):
    """(slug, label, count) tuples in stable canonical order."""
    counts = {}
    for it in items:
        cat = it.get("category") or "other"
        counts[cat] = counts.get(cat, 0) + 1

    result = []
    seen = set()
    for slug, label in SHOWCASE_CATEGORIES.items():
        if slug in counts:
            result.append((slug, label, counts[slug]))
            seen.add(slug)

    for cat, n in sorted(counts.items()):
        if cat not in seen:
            label = cat.replace("-", " ").replace("_", " ").title()
            result.append((cat, label, n))
    return result


def _escape(text):
    return html.escape(str(text or ""))


def _format_exposure_summary(exposure):
    if not exposure:
        return ""
    bits = []
    subs = exposure.get("subs")
    sub_time = exposure.get("sub_time")
    total = exposure.get("total_integration")
    if subs and sub_time:
        bits.append(f"{subs} &times; {sub_time}")
    elif total:
        bits.append(str(total))
    iso = exposure.get("iso_gain")
    if iso:
        bits.append(str(iso))
    return " &middot; ".join(bits)


GALLERY_CSS = """
:root {
  --astro-bg: #07080c;
  --astro-card: #11131c;
  --astro-border: #232738;
  --astro-accent: #38bdf8;
  --astro-nebula: #a855f7;
  --astro-text: #f1f5f9;
  --astro-text-muted: #94a3b8;
  --astro-gold: #fbbf24;
}
body {
  font-family: var(--font, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  background: var(--bg, var(--astro-bg));
  color: var(--text, var(--astro-text));
  margin: 0;
  padding: 1.2rem 1rem 3rem;
  line-height: 1.5;
}
.container { max-width: 1200px; margin: 0 auto; }
header.site-header { text-align: center; margin: 1rem 0 1.8rem; }
.header-badge {
  display: inline-block;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--astro-accent);
  background: rgba(56, 189, 248, 0.12);
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  margin-bottom: 0.5rem;
  border: 1px solid rgba(56, 189, 248, 0.25);
}
h1 {
  font-size: 2.1rem;
  margin: 0.2rem 0 0.4rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text, var(--astro-text));
}
.subtitle {
  color: var(--text-secondary, var(--astro-text-muted));
  font-size: 0.95rem;
  max-width: 680px;
  margin: 0 auto 1.5rem;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin: 1.5rem 0 2rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  color: var(--text-secondary, var(--astro-text-muted));
  text-decoration: none;
  font-size: 0.82rem;
  transition: all 0.2s ease;
}
.chip:hover {
  color: var(--astro-text);
  border-color: var(--astro-accent);
  transform: translateY(-1px);
}
.chip.on {
  background: rgba(56, 189, 248, 0.15);
  border-color: var(--astro-accent);
  color: var(--astro-accent);
  font-weight: 600;
}
.chip .n {
  opacity: 0.65;
  font-size: 0.75rem;
  margin-left: 0.35rem;
  background: rgba(255,255,255,0.08);
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
}
.hero-card {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 1.5rem;
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 2.5rem;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
}
@media (max-width: 840px) {
  .hero-card { grid-template-columns: 1fr; gap: 0; }
}
.hero-media { position: relative; background: #000; min-height: 280px; }
.hero-media img { width: 100%; height: 100%; object-fit: cover; display: block; }
.hero-badge {
  position: absolute;
  top: 1rem;
  left: 1rem;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  color: var(--astro-gold);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  border: 1px solid rgba(251, 191, 36, 0.3);
}
.hero-content {
  padding: 2rem 1.8rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.hero-meta { display: flex; gap: 0.6rem; font-size: 0.78rem; margin-bottom: 0.6rem; }
.hero-cat { color: var(--astro-accent); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.hero-target { color: var(--text-secondary, var(--astro-text-muted)); }
.hero-title { font-size: 1.55rem; margin: 0 0 0.8rem; font-weight: 700; line-height: 1.3; }
.hero-title a { color: inherit; text-decoration: none; }
.hero-title a:hover { color: var(--astro-accent); }
.hero-cap { color: var(--text-secondary, var(--astro-text-muted)); font-size: 0.92rem; line-height: 1.6; margin: 0 0 1.2rem; }
.hero-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.hero-exp { font-size: 0.82rem; color: var(--text-secondary, var(--astro-text-muted)); font-family: monospace; }
.hero-btn {
  display: inline-block;
  background: var(--astro-accent);
  color: #07080c;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 0.5rem 1.1rem;
  border-radius: 8px;
  text-decoration: none;
}
.hero-btn:hover { opacity: 0.9; }
.p-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.4rem;
}
.p-card {
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease;
}
.p-card:hover { transform: translateY(-3px); }
.p-shot { display: block; position: relative; background: #000; aspect-ratio: 16 / 10; overflow: hidden; }
.p-shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.p-overlay {
  position: absolute;
  inset: 0;
  background: rgba(7, 8, 12, 0.4);
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s ease;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
}
.p-card:hover .p-overlay { opacity: 1; }
.p-body { padding: 1.1rem; display: flex; flex-direction: column; flex: 1; }
.p-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.5rem; }
.card-tag {
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary, var(--astro-text-muted));
}
.card-tag.cat { color: var(--astro-accent); background: rgba(56, 189, 248, 0.1); }
.card-tag.target { color: var(--astro-nebula); background: rgba(168, 85, 247, 0.1); }
.p-title { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.4rem; line-height: 1.35; }
.p-title a { color: inherit; text-decoration: none; }
.p-title a:hover { color: var(--astro-accent); }
.p-meta { font-size: 0.78rem; color: var(--text-secondary, var(--astro-text-muted)); margin-bottom: 0.5rem; }
.p-eq { font-size: 0.78rem; color: var(--text-secondary, var(--astro-text-muted)); margin-top: auto; padding-top: 0.4rem; border-top: 1px solid rgba(255,255,255,0.05); }
.p-exp { font-size: 0.75rem; color: var(--astro-accent); font-family: monospace; margin-top: 0.2rem; }
.empty-state { text-align: center; padding: 3rem 1rem; color: var(--text-secondary, var(--astro-text-muted)); }
.empty-state a { color: var(--astro-accent); text-decoration: none; }
footer.site-footer {
  text-align: center;
  color: var(--text-secondary, var(--astro-text-muted));
  font-size: 0.85rem;
  margin: 3.5rem 0 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--divider, var(--astro-border));
}
footer.site-footer a { color: var(--astro-accent); text-decoration: none; }
"""

DETAIL_CSS = """
:root {
  --astro-bg: #07080c;
  --astro-card: #11131c;
  --astro-border: #232738;
  --astro-accent: #38bdf8;
  --astro-nebula: #a855f7;
  --astro-text: #f1f5f9;
  --astro-text-muted: #94a3b8;
  --astro-gold: #fbbf24;
}
body {
  font-family: var(--font, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  background: var(--bg, var(--astro-bg));
  color: var(--text, var(--astro-text));
  margin: 0;
  padding: 1rem 1rem 4rem;
  line-height: 1.6;
}
.container { max-width: 1100px; margin: 0 auto; }
.breadcrumbs {
  font-size: 0.82rem;
  color: var(--text-secondary, var(--astro-text-muted));
  margin: 0.5rem 0 1.2rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.breadcrumbs a { color: var(--astro-accent); text-decoration: none; }
.breadcrumbs .sep { opacity: 0.4; }
.photo-header { margin-bottom: 1.5rem; }
.photo-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.6rem; }
.tag-badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-weight: 500;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary, var(--astro-text-muted));
}
.tag-badge.accent { color: var(--astro-accent); background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.25); }
.tag-badge.target { color: var(--astro-nebula); background: rgba(168, 85, 247, 0.12); border: 1px solid rgba(168, 85, 247, 0.25); }
h1 { font-size: 2.2rem; margin: 0.2rem 0 0.5rem; line-height: 1.25; font-weight: 700; }
.photo-sub { color: var(--text-secondary, var(--astro-text-muted)); font-size: 0.9rem; }
.viewer-frame {
  position: relative;
  background: #000;
  border-radius: 14px;
  border: 1px solid var(--divider, var(--astro-border));
  overflow: hidden;
  margin-bottom: 2rem;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}
.viewer-media { cursor: zoom-in; display: block; }
.viewer-media img { width: 100%; height: auto; max-height: 80vh; object-fit: contain; display: block; margin: 0 auto; }
.viewer-hint {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  color: var(--astro-accent);
  font-size: 0.75rem;
  padding: 0.35rem 0.8rem;
  border-radius: 6px;
  pointer-events: none;
  border: 1px solid rgba(56, 189, 248, 0.3);
}
.zoom-modal {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(4, 5, 8, 0.96);
  z-index: 100000;
  overflow: auto;
  backdrop-filter: blur(12px);
  align-items: center;
  justify-content: center;
}
.zoom-modal.open { display: flex; }
.zoom-modal img {
  max-width: 95vw;
  max-height: 95vh;
  object-fit: contain;
  cursor: zoom-out;
  border-radius: 6px;
  box-shadow: 0 0 50px rgba(0,0,0,0.8);
}
.modal-close {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.25);
  color: #fff;
  font-size: 1.4rem;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
}
.hud-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  border-radius: 14px;
  padding: 1.5rem;
  margin-bottom: 2.2rem;
}
.hud-section h3 {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--astro-accent);
  margin: 0 0 0.8rem;
  font-weight: 600;
}
.hud-list { list-style: none; padding: 0; margin: 0; font-size: 0.85rem; }
.hud-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.hud-label { color: var(--text-secondary, var(--astro-text-muted)); }
.hud-val { font-weight: 500; color: var(--text, var(--astro-text)); text-align: right; }
.hud-link { display: inline-block; margin-top: 0.8rem; color: var(--astro-accent); font-size: 0.85rem; text-decoration: none; }
.hud-link:hover { text-decoration: underline; }
.prose-section { display: flex; flex-direction: column; gap: 1.8rem; margin-bottom: 3rem; }
.prose-block {
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  border-radius: 14px;
  padding: 1.6rem 1.8rem;
}
.prose-block h2 { font-size: 1.15rem; margin: 0 0 0.8rem; font-weight: 600; color: var(--astro-accent); }
.prose-block p { margin: 0 0 0.8rem; color: var(--text, var(--astro-text)); font-size: 0.95rem; line-height: 1.65; }
.prose-block p:last-child { margin-bottom: 0; }
.highlights-list { margin: 0; padding-left: 1.2rem; color: var(--text, var(--astro-text)); font-size: 0.92rem; line-height: 1.6; }
.highlights-list li { margin-bottom: 0.5rem; }
.nav-bar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin: 2.5rem 0 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--divider, var(--astro-border));
}
.nav-btn {
  display: inline-block;
  padding: 0.6rem 1.2rem;
  background: var(--card-bg, var(--astro-card));
  border: 1px solid var(--divider, var(--astro-border));
  border-radius: 8px;
  color: var(--astro-accent);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
}
footer.site-footer { text-align: center; color: var(--text-secondary, var(--astro-text-muted)); font-size: 0.85rem; margin-top: 2rem; }
footer.site-footer a { color: var(--astro-accent); text-decoration: none; }
"""

DETAIL_JS = """
(function(){
  var trigger = document.getElementById('media-zoom-trigger');
  var modal = document.getElementById('zoom-modal');
  var closeBtn = document.getElementById('modal-close');
  var zoomImg = document.getElementById('zoom-img');

  if (!trigger || !modal) return;

  function openModal() {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }

  trigger.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', function(e) {
    if (e.target === modal || e.target === zoomImg) {
      closeModal();
    }
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('open')) {
      closeModal();
    }
  });
})();
"""


def render_astro_showcase_gallery(*, theme_css_js, items, counts, selected=None):
    """Render the main Showcase gallery overview page."""
    total = sum(c for _s, _l, c in counts)
    chips = [
        f'<a class="chip{"" if selected else " on"}" href="/astro/photos">'
        f'All <span class="n">{total}</span></a>'
    ]
    for slug, label, n in counts:
        on = " on" if slug == selected else ""
        chips.append(f'<a class="chip{on}" href="/astro/photos/{slug}">'
                     f'{label} <span class="n">{n}</span></a>')
    chips_html = f'<div class="chips">{"".join(chips)}</div>'

    featured_item = next((e for e in items if e.get("featured")), items[0] if items else None)

    hero_html = ""
    if featured_item and not selected:
        feat_thumb = featured_item.get("thumb_url") or featured_item.get("image_url") or ""
        feat_title = _escape(featured_item.get("title", ""))
        feat_target = _escape(featured_item.get("target", ""))
        feat_cat = SHOWCASE_CATEGORIES.get(featured_item.get("category", ""), "Astro Photo")
        feat_slug = _escape(featured_item.get("id", ""))
        feat_exp = _format_exposure_summary(featured_item.get("exposure"))
        feat_cap = _escape(featured_item.get("caption", ""))

        target_span = f'<span class="hero-target">{feat_target}</span>' if feat_target else ''
        cap_p = f'<p class="hero-cap">{feat_cap}</p>' if feat_cap else ''
        exp_span = f'<span class="hero-exp">{feat_exp}</span>' if feat_exp else ''

        hero_html = f"""
        <section class="hero-card" id="featured-showcase">
          <div class="hero-media">
            <a href="/astro/photos/{feat_slug}">
              <img src="{feat_thumb}" alt="{feat_title}" fetchpriority="high" />
            </a>
            <span class="hero-badge">&starf; Featured Capture</span>
          </div>
          <div class="hero-content">
            <div class="hero-meta">
              <span class="hero-cat">{feat_cat}</span>
              {target_span}
            </div>
            <h2 class="hero-title"><a href="/astro/photos/{feat_slug}">{feat_title}</a></h2>
            {cap_p}
            <div class="hero-footer">
              {exp_span}
              <a class="hero-btn" href="/astro/photos/{feat_slug}">View Full Resolution &amp; Recipe &rarr;</a>
            </div>
          </div>
        </section>
        """

    if not items:
        cards_html = ('<div class="empty-state"><p>No photos in this category yet.</p>'
                      '<p><a href="/astro/photos">&larr; Back to all photos</a></p></div>'
                      if selected else
                      '<div class="empty-state"><p>The showcase collection is empty &mdash; '
                      'publish photos with <code>astro/bin/add-showcase</code>.</p></div>')
    else:
        cards = []
        for e in items:
            item_id = _escape(e.get("id", ""))
            thumb = e.get("thumb_url") or e.get("image_url") or ""
            title = _escape(e.get("title", ""))
            target = _escape(e.get("target", ""))
            cat = SHOWCASE_CATEGORIES.get(e.get("category", ""), e.get("category", "Photo").title())
            date_str = _escape(e.get("date", ""))
            cam_str = _escape(e.get("camera", ""))
            eq = e.get("equipment") or {}
            optics = _escape(eq.get("optics") or "")
            sensor = _escape(eq.get("sensor") or "")
            exp_str = _format_exposure_summary(e.get("exposure"))

            meta_chips = []
            if target:
                meta_chips.append(f'<span class="card-tag target">{target}</span>')
            meta_chips.append(f'<span class="card-tag cat">{cat}</span>')

            sub_meta = []
            if date_str:
                sub_meta.append(date_str)
            if cam_str:
                sub_meta.append(cam_str)
            sub_meta_html = " &middot; ".join(sub_meta)

            eq_line = optics or sensor or ""
            eq_html = f'<div class="p-eq">{eq_line}</div>' if eq_line else ''
            exp_html = f'<div class="p-exp">{exp_str}</div>' if exp_str else ''

            cards.append(f"""
            <article class="p-card">
              <a class="p-shot" href="/astro/photos/{item_id}">
                <img src="{thumb}" alt="{title}" loading="lazy" />
                <div class="p-overlay">
                  <span>View Details &rarr;</span>
                </div>
              </a>
              <div class="p-body">
                <div class="p-tags">{"".join(meta_chips)}</div>
                <h3 class="p-title"><a href="/astro/photos/{item_id}">{title}</a></h3>
                <div class="p-meta">{sub_meta_html}</div>
                {eq_html}
                {exp_html}
              </div>
            </article>
            """)
        cards_html = f'<div class="p-grid">{"".join(cards)}</div>'

    heading = ("Astrophotography Showcase" if not selected
               else f"Astrophotography &mdash; {SHOWCASE_CATEGORIES.get(selected, selected.title())}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{heading} | Peter Grecian</title>
  <meta name="description" content="Curated astrophotography captures, deep-sky stacks, widefield Milky Way, and polar derotations with exposure and equipment notes." />
  {theme_css_js}
  <style>
  {GALLERY_CSS}
  </style>
</head>
<body>
  <div class="container">
    <header class="site-header">
      <span class="header-badge">Observational Astronomy</span>
      <h1>{heading}</h1>
      <p class="subtitle">Deep-sky stacks, widefield Milky Way, polar derotations, and star trails &mdash; calibrated visual captures with complete equipment and exposure metadata.</p>
    </header>

    {chips_html}
    {hero_html}
    {cards_html}

    <footer class="site-footer">
      <a href="/astro">&larr; Astro Hub</a> &middot;
      <a href="/astro/transients">Transients Gallery</a> &middot;
      <a href="/contents">Home</a>
    </footer>
  </div>
</body>
</html>"""


def render_astro_showcase_detail(*, theme_css_js, item, prev_item=None, next_item=None):
    """Render the dedicated full-resolution detail page for a single photo."""
    item_id = _escape(item.get("id", ""))
    title = _escape(item.get("title", "Astro Photo"))
    target = _escape(item.get("target", ""))
    constellation = _escape(item.get("constellation", ""))
    category = item.get("category", "deep-sky")
    cat_label = SHOWCASE_CATEGORIES.get(category, category.title())
    date_str = _escape(item.get("date", ""))
    time_str = _escape(item.get("time", ""))
    camera = _escape(item.get("camera", ""))
    night = _escape(item.get("night", ""))

    full_url = item.get("image_url") or item.get("thumb_url") or ""

    eq = item.get("equipment") or {}
    optics = _escape(eq.get("optics") or "Standard Optical Assembly")
    focal_length = _escape(eq.get("focal_length") or "")
    f_ratio = _escape(eq.get("f_ratio") or "")
    sensor = _escape(eq.get("sensor") or "CMOS Sensor")
    mount = _escape(eq.get("mount") or "Fixed Mount")
    filter_val = _escape(eq.get("filter") or "None")

    exp = item.get("exposure") or {}
    subs = exp.get("subs")
    sub_time = _escape(exp.get("sub_time") or "")
    total_int = _escape(exp.get("total_integration") or "")
    iso_gain = _escape(exp.get("iso_gain") or "")
    bortle = _escape(exp.get("bortle") or "Suburban Sky")

    caption = _escape(item.get("caption") or "")
    processing = _escape(item.get("processing") or "")
    highlights = item.get("highlights") or []

    night_link = ""
    if night and camera in ("canon", "astrocam", "eclipticam"):
        night_link = f'<a class="hud-link" href="/astro/{camera}/night/{night}">View Full Observing Night ({night}) &rarr;</a>'

    prev_link = ""
    if prev_item:
        p_id = _escape(prev_item.get("id", ""))
        p_title = _escape(prev_item.get("title", "Previous"))
        prev_link = f'<a class="nav-btn prev" href="/astro/photos/{p_id}">&larr; {p_title}</a>'

    next_link = ""
    if next_item:
        n_id = _escape(next_item.get("id", ""))
        n_title = _escape(next_item.get("title", "Next"))
        next_link = f'<a class="nav-btn next" href="/astro/photos/{n_id}">{n_title} &rarr;</a>'

    highlights_html = ""
    if highlights:
        li_items = "".join(f"<li>{_escape(h)}</li>" for h in highlights)
        highlights_html = f"""
        <div class="prose-block">
          <h2>Technical Highlights &amp; Reduction</h2>
          <ul class="highlights-list">{li_items}</ul>
        </div>
        """

    target_badge = f'<span class="tag-badge target">{target}</span>' if target else ''
    const_badge = f'<span class="tag-badge">{constellation}</span>' if constellation else ''
    fl_li = f'<li><span class="hud-label">Focal Length</span><span class="hud-val">{focal_length}</span></li>' if focal_length else ''
    fr_li = f'<li><span class="hud-label">F-Ratio</span><span class="hud-val">{f_ratio}</span></li>' if f_ratio else ''
    cam_li = f'<li><span class="hud-label">System</span><span class="hud-val">{camera}</span></li>' if camera else ''
    iso_li = f'<li><span class="hud-label">Gain / ISO</span><span class="hud-val">{iso_gain}</span></li>' if iso_gain else ''
    bortle_li = f'<li><span class="hud-label">Sky Quality</span><span class="hud-val">{bortle}</span></li>' if bortle else ''
    subs_li = f'<li><span class="hud-label">Sub-Exposures</span><span class="hud-val">{subs} frames</span></li>' if subs else ''
    sub_time_li = f'<li><span class="hud-label">Sub Exposure</span><span class="hud-val">{sub_time}</span></li>' if sub_time else ''
    total_int_li = f'<li><span class="hud-label">Total Integration</span><span class="hud-val">{total_int}</span></li>' if total_int else ''

    cap_block = f'<div class="prose-block"><h2>Observational Overview</h2><p>{caption}</p></div>' if caption else ''
    proc_block = f'<div class="prose-block"><h2>Calibration &amp; Processing Recipe</h2><p>{processing}</p></div>' if processing else ''

    time_sub = f' &middot; {time_str}' if time_str else ''
    cam_sub = f' &middot; Camera: {camera}' if camera else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | Astrophotography Showcase</title>
  <meta name="description" content="{caption[:160] if caption else title}" />
  {theme_css_js}
  <style>
  {DETAIL_CSS}
  </style>
</head>
<body>
  <div class="container">
    <nav class="breadcrumbs" aria-label="Breadcrumbs">
      <a href="/astro">Astro</a>
      <span class="sep">/</span>
      <a href="/astro/photos">Photo Showcase</a>
      <span class="sep">/</span>
      <span>{title}</span>
    </nav>

    <header class="photo-header">
      <div class="photo-tags">
        <span class="tag-badge accent">{cat_label}</span>
        {target_badge}
        {const_badge}
      </div>
      <h1>{title}</h1>
      <div class="photo-sub">
        {date_str}{time_sub}{cam_sub}
      </div>
    </header>

    <main>
      <div class="viewer-frame">
        <div class="viewer-media" id="media-zoom-trigger" title="Click for high-resolution deep zoom">
          <img src="{full_url}" alt="{title}" fetchpriority="high" />
        </div>
        <div class="viewer-hint">&x1F50D; Click to zoom &amp; inspect</div>
      </div>

      <div class="zoom-modal" id="zoom-modal" role="dialog" aria-modal="true">
        <button class="modal-close" id="modal-close" aria-label="Close zoom modal">&times;</button>
        <img id="zoom-img" src="{full_url}" alt="{title}" />
      </div>

      <section class="hud-grid" aria-label="Equipment and Acquisition Metadata">
        <div class="hud-section">
          <h3>Optics &amp; Guiding</h3>
          <ul class="hud-list">
            <li><span class="hud-label">Optics</span><span class="hud-val">{optics}</span></li>
            {fl_li}
            {fr_li}
            <li><span class="hud-label">Mount</span><span class="hud-val">{mount}</span></li>
            <li><span class="hud-label">Filter</span><span class="hud-val">{filter_val}</span></li>
          </ul>
        </div>

        <div class="hud-section">
          <h3>Sensor &amp; Camera</h3>
          <ul class="hud-list">
            <li><span class="hud-label">Camera</span><span class="hud-val">{sensor}</span></li>
            {cam_li}
            {iso_li}
            {bortle_li}
          </ul>
        </div>

        <div class="hud-section">
          <h3>Exposure &amp; Integration</h3>
          <ul class="hud-list">
            {subs_li}
            {sub_time_li}
            {total_int_li}
            <li><span class="hud-label">Acquisition Date</span><span class="hud-val">{date_str}</span></li>
          </ul>
          {night_link}
        </div>
      </section>

      <section class="prose-section">
        {cap_block}
        {proc_block}
        {highlights_html}
      </section>

      <nav class="nav-bar">
        <div>{prev_link}</div>
        <div>{next_link}</div>
      </nav>
    </main>

    <footer class="site-footer">
      <a href="/astro/photos">&larr; Back to Photo Showcase</a> &middot;
      <a href="/astro">Astro Hub</a> &middot;
      <a href="/contents">Home</a>
    </footer>
  </div>

  <script>
  {DETAIL_JS}
  </script>
</body>
</html>"""
