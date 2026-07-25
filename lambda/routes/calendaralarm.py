"""calendaralarm — webapp + JSON API for standing-alarm rules.

Source of truth for the recurring meeting rules (successor to the pip-local
rules.yaml). The pip poller (alarm.py) reads GET /calendaralarm/api/rules to
fetch the live rule set; the HTML page is a Basic-Auth-gated CRUD UI.

The whole /calendaralarm route is guarded by Basic Auth in mywebsite.py
(check_basic_auth against the /calendaralarm/page-password SSM param) — this
module assumes the caller is already authorised.

Rule item shape (DynamoDB table `calendaralarm-rules`, hash key `id`):
    id             uuid string (primary key)
    name           label shown in the page (and the poller's de-dupe key)
    days           "Mon-Fri" | "Mon,Wed,Fri" | "Sat-Sun" | "daily"
    at             local (Europe/London) "HH:MM"
    lead_minutes   int — page this many minutes before `at`
    severity       "info" | "xinfo" | "warn" | "critical"  (default critical)
    skip_holidays  bool — skip england-and-wales bank holidays
    enabled        bool — soft on/off without deleting
    updated_at     ISO8601 UTC of last write

The API returns *enabled* rules only from GET /api/rules (what the poller
consumes); the HTML page shows all rules incl. disabled ones.
"""

import datetime
import json
import uuid

import boto3

REGION = "eu-west-1"
TABLE_NAME = "calendaralarm-rules"

# 'calendar' is calendaralarm's own tier: xMatters MEDIUM with a distinct,
# app-configurable phone sound (see alerting/lambda/handler.py _PRESETS). It's
# the sensible default for a calendar alarm — audible but not the HIGH klaxon.
VALID_SEVERITIES = ("calendar", "info", "xinfo", "warn", "critical")
VALID_DAYS = ("Mon-Fri", "Mon,Wed,Fri", "Sat-Sun", "daily")


def _table():
    return boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _json(status, payload):
    return {
        "statusCode": status,
        "body": json.dumps(payload, default=str),
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
    }


def _validate(data):
    """Coerce + validate an incoming rule dict. Returns (clean, error)."""
    name = str(data.get("name", "")).strip()
    if not name:
        return None, "name is required"

    days = str(data.get("days", "Mon-Fri")).strip()
    if days not in VALID_DAYS:
        return None, f"days must be one of {VALID_DAYS}"

    at = str(data.get("at", "")).strip()
    try:
        hh, mm = at.split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        at = f"{h:02d}:{m:02d}"
    except (ValueError, AttributeError):
        return None, "at must be HH:MM (24h)"

    try:
        lead = int(data.get("lead_minutes", 2))
        if lead < 0:
            raise ValueError
    except (ValueError, TypeError):
        return None, "lead_minutes must be a non-negative integer"

    severity = str(data.get("severity", "calendar")).strip().lower()
    if severity not in VALID_SEVERITIES:
        return None, f"severity must be one of {VALID_SEVERITIES}"

    clean = {
        "name": name,
        "days": days,
        "at": at,
        "lead_minutes": lead,
        "severity": severity,
        "skip_holidays": bool(data.get("skip_holidays", True)),
        "enabled": bool(data.get("enabled", True)),
    }
    return clean, None


# ── API handlers ───────────────────────────────────────────────────────────

def api_list(enabled_only=False):
    """All rules (page) or enabled rules only (poller feed)."""
    items = _table().scan().get("Items", [])
    if enabled_only:
        items = [r for r in items if r.get("enabled", True)]
    # DynamoDB numbers come back as Decimal — normalise for JSON + the poller.
    for r in items:
        if "lead_minutes" in r:
            r["lead_minutes"] = int(r["lead_minutes"])
    items.sort(key=lambda r: (r.get("at", ""), r.get("name", "")))
    return _json(200, {"rules": items})


def api_create(body):
    try:
        data = json.loads(body or "{}")
    except json.JSONDecodeError:
        return _json(400, {"error": "invalid JSON"})
    clean, err = _validate(data)
    if err:
        return _json(400, {"error": err})
    clean["id"] = str(uuid.uuid4())
    clean["updated_at"] = _now_iso()
    _table().put_item(Item=clean)
    return _json(201, {"rule": clean})


def api_update(rule_id, body):
    try:
        data = json.loads(body or "{}")
    except json.JSONDecodeError:
        return _json(400, {"error": "invalid JSON"})
    existing = _table().get_item(Key={"id": rule_id}).get("Item")
    if not existing:
        return _json(404, {"error": "no such rule"})
    clean, err = _validate(data)
    if err:
        return _json(400, {"error": err})
    clean["id"] = rule_id
    clean["updated_at"] = _now_iso()
    _table().put_item(Item=clean)
    return _json(200, {"rule": clean})


def api_delete(rule_id):
    existing = _table().get_item(Key={"id": rule_id}).get("Item")
    if not existing:
        return _json(404, {"error": "no such rule"})
    _table().delete_item(Key={"id": rule_id})
    return _json(200, {"deleted": rule_id})


def handle_api(method, subpath, body):
    """Dispatch /calendaralarm/api/* . subpath is everything after /api.

      GET    /rules            -> enabled rules (poller feed)
      GET    /rules?all=1      -> handled by the page via all_rules param
      POST   /rules            -> create
      PUT    /rules/<id>       -> replace
      DELETE /rules/<id>       -> delete
    """
    parts = [p for p in subpath.split("/") if p]  # e.g. ['rules', '<id>']
    if not parts or parts[0] != "rules":
        return _json(404, {"error": "unknown endpoint"})
    rule_id = parts[1] if len(parts) > 1 else None

    if method == "GET" and rule_id is None:
        return api_list(enabled_only=True)
    if method == "POST" and rule_id is None:
        return api_create(body)
    if method == "PUT" and rule_id:
        return api_update(rule_id, body)
    if method == "DELETE" and rule_id:
        return api_delete(rule_id)
    return _json(405, {"error": f"{method} not allowed on {subpath}"})


# ── HTML page ──────────────────────────────────────────────────────────────

def render_page():
    """The CRUD UI. Reads/writes via the JSON API with fetch()."""
    return {
        "statusCode": 200,
        "body": _PAGE_HTML,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
    }


_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>calendaralarm</title>
<style>
  :root {
    --bg:#000; --card:#161616; --text:#E0E0E0; --label:#8E8E93;
    --accent:#007AFF; --error:#FF3B30; --warn:#FF9500; --divider:#2C2C2E;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,'SF Pro Display','Inter','Roboto',sans-serif;
    padding:16px; max-width:760px; margin-inline:auto;
  }
  h1 { font-size:1.4rem; font-weight:600; margin:8px 0 4px; }
  .sub { color:var(--label); font-size:.85rem; margin-bottom:20px; }
  .card {
    background:var(--card); border-radius:12px; padding:16px; margin-bottom:12px;
    display:flex; justify-content:space-between; align-items:center; gap:12px;
  }
  .card.off { opacity:.5; }
  .rule-main { min-width:0; }
  .rule-name { font-weight:600; font-size:1.05rem; }
  .rule-meta { color:var(--label); font-size:.85rem; margin-top:3px; }
  .sev { font-size:.72rem; padding:2px 8px; border-radius:8px; margin-left:6px; vertical-align:middle; }
  .sev.calendar { background:rgba(0,122,255,.18); color:var(--accent); }
  .sev.critical { background:rgba(255,59,48,.18); color:var(--error); }
  .sev.warn { background:rgba(255,149,0,.18); color:var(--warn); }
  .sev.xinfo, .sev.info { background:rgba(142,142,147,.2); color:var(--label); }
  .actions { display:flex; gap:8px; flex-shrink:0; }
  button {
    font-family:inherit; font-size:.85rem; border:none; border-radius:8px;
    padding:8px 12px; cursor:pointer; background:var(--divider); color:var(--text);
  }
  button.primary { background:var(--accent); color:#fff; }
  button.danger { background:transparent; color:var(--error); }
  button:disabled { opacity:.4; cursor:default; }
  #addBtn { width:100%; margin:4px 0 24px; padding:12px; font-size:1rem; }
  dialog {
    background:var(--card); color:var(--text); border:1px solid var(--divider);
    border-radius:14px; padding:20px; width:min(92vw,420px);
  }
  dialog::backdrop { background:rgba(0,0,0,.6); }
  label.field { display:block; margin:12px 0 4px; color:var(--label); font-size:.8rem; }
  input, select {
    width:100%; padding:10px; border-radius:8px; border:1px solid var(--divider);
    background:#0d0d0d; color:var(--text); font-family:inherit; font-size:1rem;
  }
  .row { display:flex; gap:10px; }
  .row > div { flex:1; }
  .checkline { display:flex; align-items:center; gap:8px; margin-top:14px; }
  .checkline input { width:auto; }
  .dlg-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:22px; }
  .empty { color:var(--label); text-align:center; padding:40px 0; }
  #err { color:var(--error); font-size:.85rem; min-height:1.2em; margin-top:8px; }
</style>
</head>
<body>
  <h1>calendaralarm</h1>
  <div class="sub">Standing alarm rules. The pip poller reads these every 5&nbsp;min and pages via xMatters. Default sound is <b>calendar</b> (xMatters MEDIUM — set its tone in the xMatters phone app); <b>critical</b> is the loud HIGH klaxon reserved for real incidents.</div>

  <div id="list"><div class="empty">Loading…</div></div>
  <button id="addBtn" class="primary">+ New alarm</button>

  <dialog id="dlg">
    <form method="dialog" id="form">
      <h2 id="dlgTitle" style="font-size:1.1rem;margin:0 0 4px;">New alarm</h2>
      <label class="field">Name</label>
      <input name="name" required placeholder="Dentist / Running club / Wakeup">
      <div class="row">
        <div>
          <label class="field">Days</label>
          <select name="days">
            <option>Mon-Fri</option>
            <option>Mon,Wed,Fri</option>
            <option>Sat-Sun</option>
            <option value="daily">daily</option>
          </select>
        </div>
        <div>
          <label class="field">Time (HH:MM)</label>
          <input name="at" required placeholder="15:45" pattern="[0-9]{1,2}:[0-9]{2}">
        </div>
      </div>
      <div class="row">
        <div>
          <label class="field">Lead (min before)</label>
          <input name="lead_minutes" type="number" min="0" value="2">
        </div>
        <div>
          <label class="field">Sound / severity</label>
          <select name="severity">
            <option value="calendar">calendar (own sound)</option>
            <option value="critical">critical (HIGH klaxon)</option>
            <option value="warn">warn (MEDIUM)</option>
            <option value="xinfo">xinfo (LOW)</option>
            <option value="info">info (Slack only)</option>
          </select>
        </div>
      </div>
      <div class="checkline">
        <input type="checkbox" name="skip_holidays" id="skip_holidays" checked>
        <label for="skip_holidays" style="color:var(--text);">Skip UK bank holidays</label>
      </div>
      <div class="checkline">
        <input type="checkbox" name="enabled" id="enabled" checked>
        <label for="enabled" style="color:var(--text);">Enabled</label>
      </div>
      <div id="err"></div>
      <div class="dlg-actions">
        <button type="button" id="cancelBtn">Cancel</button>
        <button type="submit" class="primary" id="saveBtn">Save</button>
      </div>
    </form>
  </dialog>

<script>
const API = 'api/rules';           // relative to /calendaralarm/
const listEl = document.getElementById('list');
const dlg = document.getElementById('dlg');
const form = document.getElementById('form');
const errEl = document.getElementById('err');
let editingId = null;

function esc(s){ return String(s??'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

async function load(){
  // ?all=1 so the page shows disabled rules too (poller uses the plain feed).
  const r = await fetch(API + '?all=1');
  if(!r.ok){ listEl.innerHTML = '<div class="empty">Failed to load ('+r.status+')</div>'; return; }
  const {rules} = await r.json();
  if(!rules.length){ listEl.innerHTML = '<div class="empty">No alarms yet. Add one below.</div>'; return; }
  listEl.innerHTML = rules.map(rule => `
    <div class="card ${rule.enabled ? '' : 'off'}">
      <div class="rule-main">
        <div class="rule-name">${esc(rule.name)}<span class="sev ${esc(rule.severity)}">${esc(rule.severity)}</span></div>
        <div class="rule-meta">${esc(rule.days)} · ${esc(rule.at)} · lead ${esc(rule.lead_minutes)}m${rule.skip_holidays ? ' · skips holidays' : ''}${rule.enabled ? '' : ' · disabled'}</div>
      </div>
      <div class="actions">
        <button data-edit="${esc(rule.id)}">Edit</button>
        <button class="danger" data-del="${esc(rule.id)}">Delete</button>
      </div>
    </div>`).join('');
  window._rules = rules;
}

function openDialog(rule){
  editingId = rule ? rule.id : null;
  document.getElementById('dlgTitle').textContent = rule ? 'Edit alarm' : 'New alarm';
  errEl.textContent = '';
  form.name.value = rule ? rule.name : '';
  form.days.value = rule ? rule.days : 'Mon-Fri';
  form.at.value = rule ? rule.at : '';
  form.lead_minutes.value = rule ? rule.lead_minutes : 2;
  form.severity.value = rule ? rule.severity : 'calendar';
  form.skip_holidays.checked = rule ? !!rule.skip_holidays : true;
  form.enabled.checked = rule ? !!rule.enabled : true;
  dlg.showModal();
}

document.getElementById('addBtn').onclick = () => openDialog(null);
document.getElementById('cancelBtn').onclick = () => dlg.close();

listEl.onclick = (e) => {
  const ed = e.target.dataset.edit, del = e.target.dataset.del;
  if(ed){ openDialog((window._rules||[]).find(r=>r.id===ed)); }
  if(del){ doDelete(del); }
};

async function doDelete(id){
  const rule = (window._rules||[]).find(r=>r.id===id);
  if(!confirm('Delete "'+(rule?rule.name:id)+'"?')) return;
  const r = await fetch(API + '/' + id, {method:'DELETE'});
  if(r.ok) load(); else alert('Delete failed ('+r.status+')');
}

form.onsubmit = async (e) => {
  e.preventDefault();
  errEl.textContent = '';
  const payload = {
    name: form.name.value,
    days: form.days.value,
    at: form.at.value,
    lead_minutes: parseInt(form.lead_minutes.value || '0', 10),
    severity: form.severity.value,
    skip_holidays: form.skip_holidays.checked,
    enabled: form.enabled.checked,
  };
  const method = editingId ? 'PUT' : 'POST';
  const url = editingId ? (API + '/' + editingId) : API;
  const r = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  if(r.ok){ dlg.close(); load(); }
  else {
    let msg = 'Save failed ('+r.status+')';
    try { const j = await r.json(); if(j.error) msg = j.error; } catch(_){}
    errEl.textContent = msg;
  }
};

load();
</script>
</body>
</html>
"""
