"""/groceries: the household Sainsbury's shop, private.

Renders groceries/latest.json (written by ~/groceries/bin/publish, the
groceries strand's pipeline) from the gardencam bucket. All the arithmetic
happens there; this page only lays it out.
"""

from datetime import date
from html import escape


def _d(iso):
    return date.fromisoformat(iso).strftime("%a %-d %b")


def _left(days):
    return "out" if days <= 0 else f"{days}d left"


def _on(p):
    return f" · {p['on_order']:g} on order" if p.get("on_order") else ""


def _gbp(x):
    return f"£{x:,.2f}"


def _short(name, n=60):
    name = name.replace("Sainsbury's ", "")
    return escape(name if len(name) <= n else name[: n - 1] + "…")


def render_groceries_page(data, *, theme_css_js):
    if not data:
        body = "<p class='muted'>No data published yet.</p>"
        return _page(body, theme_css_js)

    orders = data["orders"]
    recent = [o for o in orders if o["date"] >= "2026-01-01"]
    last = orders[-1]

    # --- buy now ---------------------------------------------------------
    preds = data["predictions"]
    slot = data.get("slot") or {}
    due = [p for p in preds if p.get("buy")]
    if due:
        chips = "".join(
            f"<div class='chip ok'><b>{escape(p['group'])}</b>"
            f"<span>{p['on_order']:g} on order · {p.get('suggest', '')} needed</span></div>"
            if p.get("covered") else
            f"<div class='chip due'><b>{escape(p['group'])}</b>"
            f"<span>{p.get('suggest', '')} {p['unit']} · {_left(p['days_left'])}"
            f"{_on(p)}</span></div>"
            for p in due)
    else:
        chips = "<div class='chip'>Nothing watched is due</div>"
    if slot.get("date"):
        due_title = f"For the {_d(slot['date'])} delivery, {escape(slot.get('window', ''))}"
        if slot.get("reserved_until") and data["generated"] == date.today().isoformat():
            due_title += (f" <span class='warn small'>reserved only: check out before "
                          f"{escape(slot['reserved_until'])}</span>")
    else:
        due_title = "Due this week <span class='muted small'>(no slot booked)</span>"

    # --- placed, not yet delivered --------------------------------------
    pend_html = ""
    for o in data.get("pending", []):
        rows = "".join(
            f"<tr><td>{_short(i['name'])}</td><td class='num'>{i['qty']}</td>"
            f"<td class='num'>{_gbp(i['price'])}</td></tr>" for i in o["items"])
        short = o.get("short_of_free_delivery") or 0
        warn = (f"<p class='warn'>Delivery charged {_gbp(o['delivery'])}: the trolley is "
                f"{_gbp(short)} short of the £50 Delivery Pass minimum. Adding {_gbp(short)} or more "
                f"before {escape(o['amend_until'] or 'the amend cut-off')} makes delivery free.</p>"
                if short and o.get("delivery") else "")
        pend_html += f"""
<h2>On order: {_d(o['date'])}, {escape(o['window'])}</h2>
<div class='card'>{warn}
<div class='tiles'>
<div class='tile'><div class='label'>Trolley</div><div class='big'>{_gbp(o['trolley'])}</div>
<div class='muted small'>{len(o['items'])} lines, saved {_gbp(o['saved'] or 0)}</div></div>
<div class='tile'><div class='label'>Delivery</div><div class='big {'warn' if o['delivery'] else ''}'>{_gbp(o['delivery'] or 0)}</div>
<div class='muted small'>free from £50 on the pass</div></div>
<div class='tile'><div class='label'>Estimated total</div><div class='big'>{_gbp(o['estimated_total'])}</div>
<div class='muted small'>paid on delivery day</div></div>
<div class='tile'><div class='label'>Amend or cancel until</div><div class='big small2'>{escape(o['amend_until'] or '?')}</div>
<div class='muted small'>order {escape(o['order'])}</div></div>
</div>
<details><summary class='muted'>Basket</summary><table>
<tr><th>Item</th><th class='num'>Qty</th><th class='num'>Price</th></tr>{rows}</table></details>
</div>"""

    # --- predictions -----------------------------------------------------
    prow = []
    for p in preds:
        prods = ", ".join(_short(n, 38) for n, _ in p["products"][:2])
        if "runout" not in p:
            prow.append(f"<tr><td>{escape(p['group'])}</td><td colspan=4 class='muted'>"
                        f"too few purchases ({len(p['purchases'])})</td><td></td><td class='muted small'>{prods}</td></tr>")
            continue
        cls = "warn" if p["buy"] else ""
        low = " <span class='muted small'>(low confidence)</span>" if p["confidence"] == "low" else ""
        onord = f"{p['on_order']:g}" if p.get("on_order") else ""
        prow.append(
            f"<tr class='{cls}'><td>{escape(p['group'])}{low}</td>"
            f"<td class='num'>{p['per_week']:.1f} {p['unit']}</td>"
            f"<td class='num'>{p['stock_now']:g}</td>"
            f"<td class='num'>{_d(p['runout'])}</td>"
            f"<td class='num'>{p['days_left']:+d}d</td>"
            f"<td class='num'>{onord}</td>"
            f"<td class='muted small'>{prods}</td></tr>")

    # --- money -----------------------------------------------------------
    sub = sum(o["subtotal"] for o in recent)
    saved = sum(o["saved"] for o in recent)
    coupons = sum(o["coupons"] for o in recent)
    paid = sum(o["paid"] for o in recent)
    deliv = sum(o["delivery"] for o in recent)
    pts = last["points_balance"] or 0
    tiles = [
        ("Spent 2026", _gbp(paid), f"{len(recent)} orders"),
        ("Saved on offers", _gbp(saved), f"{saved / sub:.1%} of shelf price" if sub else ""),
        ("Coupons used", _gbp(coupons), "e-vouchers at checkout"),
        ("Delivery paid", _gbp(deliv), ""),
        ("Nectar balance", f"{pts:,} pts", f"≈ {_gbp(pts / 200)} unspent"),
    ]
    tiles_html = "".join(f"<div class='tile'><div class='label'>{a}</div><div class='big'>{b}</div>"
                         f"<div class='muted small'>{c}</div></div>" for a, b, c in tiles)

    # --- orders ----------------------------------------------------------
    orow = "".join(
        f"<tr><td>{_d(o['date'])}</td><td class='num'>{o['lines']}</td>"
        f"<td class='num'>{_gbp(o['paid'])}</td><td class='num'>{_gbp(o['saved'])}</td>"
        f"<td class='num'>{_gbp(o['coupons']) if o['coupons'] else ''}</td>"
        f"<td class='num'>{o['subs'] or ''}</td><td class='num'>{o['unavailable'] or ''}</td></tr>"
        for o in reversed(orders))

    # --- substitutions ---------------------------------------------------
    srow = []
    for s in data["substitutions"][:20]:
        got = s.get("got") or {}
        diff = (got.get("price", 0) - s["ordered"]["price"]) if got else 0
        srow.append(f"<tr><td>{_d(s['date'])}</td><td>{_short(s['ordered']['name'], 45)}</td>"
                    f"<td>{_short(got.get('name', '?'), 45)}</td>"
                    f"<td class='num {'warn' if diff > 0 else ''}'>{'+' if diff > 0 else ''}{_gbp(diff) if diff else ''}</td></tr>")

    # --- staples ---------------------------------------------------------
    strow = "".join(
        f"<tr><td>{_short(r['name'])}</td><td class='num'>{r['share']:.0%}</td>"
        f"<td class='num'>{_gbp(r['spend'])}</td><td class='num'>{_d(r['last'])}</td></tr>"
        for r in data["staples"][:30])

    body = f"""
<h1>Groceries</h1>
<p class='muted'>Sainsbury's, KT5. Last delivery {_d(last['date'])}; built {_d(data['generated'])}.</p>

{pend_html}
<h2>{due_title}</h2>
<div class='chips'>{chips}</div>

<h2>Watched items</h2>
<div class='card'><table>
<tr><th>Group</th><th class='num'>Use / week</th><th class='num'>Stock now</th><th class='num'>Runs out</th><th class='num'></th><th class='num'>On order</th><th>Usually</th></tr>
{''.join(prow)}
</table>
<p class='muted small'>Rate = what was bought before the latest purchase, over the days it lasted. Online orders only.</p></div>

<h2>Money</h2>
<div class='tiles'>{tiles_html}</div>

<h2>Orders</h2>
<div class='card'><table>
<tr><th>Delivered</th><th class='num'>Lines</th><th class='num'>Paid</th><th class='num'>Saved</th><th class='num'>Coupons</th><th class='num'>Subs</th><th class='num'>Unavail.</th></tr>
{orow}</table></div>

<h2>Substitutions</h2>
<div class='card'><table>
<tr><th>Date</th><th>Ordered</th><th>Got</th><th class='num'>Voucher due</th></tr>
{''.join(srow)}</table>
<p class='muted small'>A dearer substitute earns a Substitute Promise voucher for the difference.</p></div>

<h2>Staples</h2>
<div class='card'><table>
<tr><th>Item</th><th class='num'>In orders</th><th class='num'>Spent</th><th class='num'>Last</th></tr>
{strow}</table>
<p class='muted small'>Bought in at least a quarter of orders since May. Personal-care items excluded.</p></div>
"""
    return _page(body, theme_css_js)


def _page(body, theme_css_js):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Groceries</title>
{theme_css_js}
<style>
body{{background:#000;color:#E0E0E0;font-family:-apple-system,'SF Pro Display','Inter','Roboto',sans-serif;
  margin:0 auto;max-width:980px;padding:16px}}
h1{{margin:8px 0 4px}} h2{{margin:28px 0 10px;font-size:1.1rem}}
.muted{{color:#8E8E93}} .small{{font-size:.82rem}}
.card{{background:#161616;border-radius:12px;padding:12px 14px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th{{color:#8E8E93;font-weight:500;text-align:left;border-bottom:1px solid #2C2C2E;padding:6px 8px}}
td{{border-bottom:1px solid #2C2C2E;padding:6px 8px;vertical-align:top}}
.num{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
tr.warn td:first-child,.warn{{color:#FF9500}}
.chips{{display:flex;flex-wrap:wrap;gap:8px}}
.chip{{background:#161616;border-radius:12px;padding:10px 14px;display:flex;gap:12px;align-items:center}}
.chip.due{{border:1px solid #FF9500}} .chip.due span{{color:#FF9500}}
.chip.ok{{border:1px solid #34C759}} .chip.ok span{{color:#34C759}}
.big.small2{{font-size:1rem}} details{{margin-top:10px}} summary{{cursor:pointer}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}
.tile{{background:#161616;border-radius:12px;padding:12px 14px}}
.tile .label{{color:#8E8E93;font-size:.82rem}} .tile .big{{font-size:1.4rem;margin:4px 0}}
</style></head><body>{body}</body></html>"""
