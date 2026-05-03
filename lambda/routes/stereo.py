"""Stereo photography — gallery and WebXR viewer."""

import json
import boto3

S3_BUCKET = "petergrecian.co.uk"
S3_PREFIX = "stereo"
S3_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/"
S3_VIDEO_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/video/"

# Manually curated video list — add entries here after uploading to S3
STEREO_VIDEOS = [
    {"file": "may1-105049-mb4.mp4", "label": "Railway 25s — motion blur 4×", "note": "2K · dormouse · optical-flow blur"},
    {"file": "may1-105132-mb4.mp4", "label": "Railway 64s — motion blur 4×", "note": "2K · ferret · optical-flow blur"},
    {"file": "may1-lift-mb4.mp4", "label": "LIFT TEST — motion blur 4×", "note": "Barbican view, rotated 90°, optical-flow blur"},
    {"file": "may1-105249-2k.mp4", "label": "Arrival at Waterloo (4 min)", "note": "2K · 3840×1080 · 1-frame baseline · NO blur"},
    {"file": "may1-105132-2k.mp4", "label": "Railway 64s — May 2026", "note": "2K · 3840×1080 · squirrel · NO blur"},
    {"file": "may1-105049-2k.mp4", "label": "Railway 25s — May 2026", "note": "2K · 3840×1080 · magpie · NO blur"},
]


def _list_shots():
    """List all shot metadata from S3, sorted by inliers descending."""
    s3 = boto3.client("s3", region_name="eu-west-1")
    paginator = s3.get_paginator("list_objects_v2")
    shots = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX + "/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                try:
                    resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    meta = json.loads(resp["Body"].read())
                    shots.append(meta)
                except Exception:
                    pass
    shots.sort(key=lambda x: x.get("inliers", 0), reverse=True)
    return shots


def render_gallery_page(*, theme_css_js):
    shots = _list_shots()

    cards = ""
    for s in shots:
        slug = s.get("slug", "")
        pair_id = s.get("pair_id", "")
        title = s.get("title", slug)
        inliers = s.get("inliers", "?")
        ts = s.get("timestamp", "")
        time_str = ts[11:16] if ts else ""
        date_str = ts[:10] if ts else ""
        img_param = f"{slug}/{slug}.{pair_id}"
        cards += f'''
    <a href="/stereo?img={img_param}" class="shot-card">
      <div class="shot-title">{title}</div>
      <div class="shot-meta">
        <span class="quality">{inliers} inliers</span>
        <span class="timestamp">{date_str} {time_str}</span>
      </div>
    </a>'''

    if not cards:
        cards = '<p class="empty">No stereo images yet.</p>'

    video_cards = ""
    for v in STEREO_VIDEOS:
        video_cards += f'''
    <div class="shot-card">
      <div class="shot-title">{v["label"]}</div>
      <div class="shot-meta" style="margin-bottom:0.5rem;">
        <span class="quality">{v["note"]}</span>
        <span class="timestamp">SBS MP4</span>
      </div>
      <div style="display:flex;gap:8px;">
        <a href="/stereo?svideo={v["file"]}" style="flex:1;text-align:center;background:var(--accent);color:#fff;border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Sphere VR</a>
        <a href="/stereo?video={v["file"]}" style="flex:1;text-align:center;background:var(--card-bg);color:var(--accent);border:1px solid var(--divider);border-radius:8px;padding:6px 0;font-size:0.85rem;text-decoration:none;">Flat VR</a>
      </div>
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stereo Photography</title>
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 600px; margin: 0 auto; }}
    h1 {{ font-size: 1.4rem; margin: 1rem 0 0.3rem; text-align: center; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    .shot-card {{
      display: block; text-decoration: none;
      background: var(--card-bg); border-radius: 12px;
      padding: 1rem 1.2rem; margin-bottom: 0.75rem;
      border: 1px solid var(--divider);
    }}
    .shot-card:hover {{ opacity: 0.8; }}
    .shot-title {{ font-size: 1.05rem; font-weight: 600; color: var(--accent); margin-bottom: 0.3rem; }}
    .shot-meta {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); }}
    .empty {{ text-align: center; color: var(--text-secondary); margin-top: 2rem; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Stereo Photography</h1>
    <div class="subtitle">Quest 2 VR — sorted by rectification quality</div>
    {cards}
    <h2 style="font-size:1.1rem;margin:1.5rem 0 0.5rem;">Stereo Videos</h2>
    <div class="subtitle" style="margin-bottom:0.75rem;">Tap to open in WebXR VR viewer</div>
    {video_cards}
    <div class="footer"><a href="/contents">Home</a></div>
  </div>
</body>
</html>'''


def get_neighbours(img_param):
    """Return {prev, next, current} for an img_param, in gallery sort order."""
    try:
        shots = _list_shots()
        params = [f"{s.get('slug','')}/{s.get('slug','')}.{s.get('pair_id','')}" for s in shots]
        if img_param in params:
            i = params.index(img_param)
            return {
                "prev": params[i - 1] if i > 0 else "",
                "next": params[i + 1] if i < len(params) - 1 else "",
                "current": img_param,
            }
    except Exception:
        pass
    return {"prev": "", "next": "", "current": img_param}


def render_viewer_page(*, theme_css_js, img_param):
    """img_param is e.g. 'barbican/barbican.12'"""
    jps_url = S3_BASE + img_param + ".jps"

    # Fetch eye_order from metadata so viewer defaults to correct orientation
    eye_order = "A"
    try:
        s3 = boto3.client("s3", region_name="eu-west-1")
        resp = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{img_param}.json")
        meta = json.loads(resp["Body"].read())
        eye_order = meta.get("eye_order", "A")
    except Exception:
        pass

    swapped_js = "true" if eye_order == "B" else "false"

    # Find previous and next shots in gallery order (same sort as gallery_page)
    prev_param = next_param = ""
    try:
        shots = _list_shots()
        params = [f"{s.get('slug','')}/{s.get('slug','')}.{s.get('pair_id','')}" for s in shots]
        if img_param in params:
            i = params.index(img_param)
            if i > 0:
                prev_param = params[i - 1]
            if i < len(params) - 1:
                next_param = params[i + 1]
    except Exception:
        pass

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stereo Viewer</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font); }}
    #ui {{
      padding: 20px; display: flex; flex-direction: column;
      align-items: center; gap: 16px;
    }}
    h1 {{ font-size: 1.2rem; color: var(--text); }}
    #preview {{ width: 100%; max-width: 600px; border-radius: 12px; display: none; }}
    #controls {{ display: none; flex-direction: column; gap: 12px; width: 100%; max-width: 600px; }}
    .control-row {{
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); border-radius: 12px; padding: 12px 16px;
    }}
    .control-row label {{ color: var(--text-secondary); font-size: 0.9rem; }}
    .control-row input[type=range] {{ width: 55%; accent-color: var(--accent); }}
    .control-row span {{ color: var(--text); font-size: 0.9rem; min-width: 40px; text-align: right; }}
    .btn-row {{ display: flex; gap: 12px; width: 100%; max-width: 600px; }}
    button {{
      background: var(--accent); color: #fff; border: none;
      border-radius: 12px; padding: 14px 0; font-size: 1rem;
      cursor: pointer; flex: 1;
    }}
    button:disabled {{ background: var(--divider); color: var(--text-secondary); cursor: default; }}
    button.secondary {{ background: var(--card-bg); color: var(--accent); border: 1px solid var(--divider); }}
    #status {{ color: var(--text-secondary); font-size: 0.85rem; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 1rem 0; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="ui">
    <h1>Stereo Viewer</h1>
    <img id="preview" alt="Preview">
    <div id="controls">
      <div class="control-row">
        <label>Convergence</label>
        <input type="range" id="convergence" min="-30" max="30" value="0" step="0.1">
        <span id="convergence-val">0.0°</span>
      </div>
      <div class="control-row">
        <label>Eye separation</label>
        <input type="range" id="separation" min="0.3" max="1.0" value="0.5" step="0.01">
        <span id="separation-val">0.50</span>
      </div>
    </div>
    <div class="btn-row">
      <button id="vr-btn" disabled>Enter VR</button>
      <button id="swap-btn" class="secondary" disabled>Order {eye_order}</button>
    </div>
    <div class="btn-row">
      <button id="prev-btn" class="secondary" {('disabled' if not prev_param else '')}>&#8592; Prev</button>
      <button id="next-btn" class="secondary" {('disabled' if not next_param else '')}>Next &#8594;</button>
    </div>
    <div id="status">Loading...</div>
    <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  </div>
  <canvas id="xr-canvas"></canvas>
  <script>
    const JPS_URL = '{jps_url}';

    const preview = document.getElementById('preview');
    const controls = document.getElementById('controls');
    const vrBtn = document.getElementById('vr-btn');
    const swapBtn = document.getElementById('swap-btn');
    const status = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    const convergenceSlider = document.getElementById('convergence');
    const separationSlider = document.getElementById('separation');
    const convergenceVal = document.getElementById('convergence-val');
    const separationVal = document.getElementById('separation-val');

    let swapped = {swapped_js};
    let zoom = 1.0;  // >1 = zoomed out (image smaller), <1 = zoomed in
    let eyeShiftX = 0;  // normalized: per-eye X offset within its half (signed)
    let eyeShiftY = 0;  // normalized: per-eye Y offset (signed, mirrored between eyes)
    let xrSession = null;
    let gl = null;
    let prog = null;
    let tex = null;

    preview.crossOrigin = 'anonymous';
    preview.src = JPS_URL;
    preview.onload = () => {{
      preview.style.display = 'block';
      controls.style.display = 'flex';
      vrBtn.disabled = false;
      swapBtn.disabled = false;
      status.textContent = 'Ready';
    }};
    preview.onerror = () => {{ status.textContent = 'Failed to load image'; }};

    convergenceSlider.addEventListener('input', () => {{
      convergenceVal.textContent = parseFloat(convergenceSlider.value).toFixed(1) + '°';
    }});
    separationSlider.addEventListener('input', () => {{
      separationVal.textContent = parseFloat(separationSlider.value).toFixed(2);
    }});

    swapBtn.addEventListener('click', () => {{
      swapped = !swapped;
      swapBtn.textContent = swapped ? 'Order B' : 'Order A';
    }});

    // Prev/next navigation — keeps the WebXR session alive by swapping the texture in-place.
    // Falls back to URL navigation when not in VR.
    let neighbours = {{ prev: '{prev_param}', next: '{next_param}', current: {json.dumps(img_param)} }};

    async function loadNeighbours(forParam) {{
      // Refresh prev/next pointers from a small JSON endpoint after switching image
      try {{
        const r = await fetch('/stereo-nav?img=' + encodeURIComponent(forParam));
        if (r.ok) neighbours = await r.json();
      }} catch(e) {{}}
    }}

    async function swapImage(target) {{
      if (!target) return;
      const newUrl = 'https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/' + target + '.jps';
      const newImg = new Image();
      newImg.crossOrigin = 'anonymous';
      newImg.src = newUrl;
      await new Promise((res, rej) => {{ newImg.onload = res; newImg.onerror = rej; }});

      // Update preview <img> for the 2D view
      preview.src = newUrl;

      // Reset per-image overrides
      eyeShiftX = 0;
      eyeShiftY = 0;

      // If in VR, swap the GL texture in-place
      if (xrSession && gl && tex) {{
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, newImg);
      }}
      // Update URL bar without navigating, so reloads restore current image
      history.replaceState(null, '', '/stereo?img=' + encodeURIComponent(target));
      neighbours.current = target;
      loadNeighbours(target);
    }}

    function go(target) {{ swapImage(target); }}

    document.getElementById('prev-btn').addEventListener('click', () => go(neighbours.prev));
    document.getElementById('next-btn').addEventListener('click', () => go(neighbours.next));
    document.addEventListener('keydown', e => {{
      if (e.key === 'ArrowLeft' || e.key === 'PageUp')   {{ e.preventDefault(); go(neighbours.prev); }}
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{ e.preventDefault(); go(neighbours.next); }}
    }});

    vrBtn.addEventListener('click', async () => {{
      if (xrSession) {{ await xrSession.end(); return; }}
      if (!navigator.xr) {{ status.textContent = 'WebXR not available'; return; }}
      const supported = await navigator.xr.isSessionSupported('immersive-vr');
      if (!supported) {{ status.textContent = 'Immersive VR not supported'; return; }}
      try {{
        xrSession = await navigator.xr.requestSession('immersive-vr', {{
          requiredFeatures: ['local']
        }});
        await startXR(xrSession);
      }} catch (e) {{
        status.textContent = 'VR error: ' + e.message;
      }}
    }});

    async function startXR(session) {{
      vrBtn.textContent = 'Exit VR';
      canvas.style.display = 'block';
      gl = canvas.getContext('webgl2', {{ xrCompatible: true }});
      await gl.makeXRCompatible();
      const refSpace = await session.requestReferenceSpace('local');
      const layer = new XRWebGLLayer(session, gl);
      session.updateRenderState({{ baseLayer: layer }});

      const img = preview;
      if (!img.complete) await new Promise(r => img.onload = r);

      tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

      const sphere = buildSphereRenderer(gl);

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};

      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);

        for (const src of session.inputSources) {{
          const gp = src.gamepad;
          if (!gp) continue;
          const id = src.handedness;
          if (!wasPressed[id]) wasPressed[id] = {{}};

          // A/X button (index 4) → swap eyes
          const aBtn = gp.buttons[4];
          if (aBtn?.pressed && !wasPressed[id][4]) {{
            swapped = !swapped;
            swapBtn.textContent = swapped ? 'Order B' : 'Order A';
          }}
          wasPressed[id][4] = aBtn?.pressed;

          // Right trigger (button 0) → next image; Left trigger → prev
          const trig = gp.buttons[0];
          if (trig?.pressed && !wasPressed[id][0]) {{
            if (src.handedness === 'right') go(NEXT);
            else if (src.handedness === 'left') go(PREV);
          }}
          wasPressed[id][0] = trig?.pressed;

          // Right thumbstick X (axes[2]) → convergence; Y (axes[3]) → zoom
          if (src.handedness === 'right') {{
            const stickX = gp.axes[2] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              const val = Math.max(-30, Math.min(30,
                parseFloat(convergenceSlider.value) + stickX * 0.3));
              convergenceSlider.value = val;
              convergenceVal.textContent = val.toFixed(1) + '°';
            }}
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickY) > 0.15) {{
              zoom = Math.max(0.5, Math.min(3.0, zoom + stickY * 0.02));
            }}
          }}

          // Left thumbstick X/Y → pan (per-eye texture offset, opposite directions)
          if (src.handedness === 'left') {{
            const stickX = gp.axes[2] ?? 0;
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              eyeShiftX = Math.max(-0.25, Math.min(0.25, eyeShiftX + stickX * 0.003));
            }}
            if (Math.abs(stickY) > 0.15) {{
              eyeShiftY = Math.max(-0.25, Math.min(0.25, eyeShiftY + stickY * 0.003));
            }}
          }}
        }}

        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const yawDeg = parseFloat(convergenceSlider.value);
        const separation = parseFloat(separationSlider.value);
        for (const view of pose.views) {{
          const vp = layer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          const uOffset = eyeIsLeft ? 0.0 : 0.5;
          renderEyeSphere(gl, sphere, tex, uOffset, separation,
            view.projectionMatrix, view.transform.inverse.matrix, yawDeg, eyeIsLeft, zoom,
            img.naturalWidth, img.naturalHeight, eyeShiftX, eyeShiftY);
        }}
      }});
    }}

    // Build inside-out sphere mesh: stacks×slices quads, normals pointing inward.
    // Returns {{ prog, vao, indexCount, uProj, uView, uYaw, uOffsetX, uSeparation, uTex }}
    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS; // 0 (top) → π (bottom)
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(
            Math.sin(phi) * Math.cos(theta),  // x
            Math.cos(phi),                     // y
            Math.sin(phi) * Math.sin(theta)    // z
          );
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s * (SLICES + 1) + sl;
          const b = a + SLICES + 1;
          indices.push(a, b, a+1, b, b+1, a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; in vec2 aUV;
        uniform mat4 uProj, uView, uYawMat;
        out vec3 vDir;
        void main() {{
          // Pass world-space direction to fragment shader for angular mapping
          vDir = (uYawMat * vec4(aPos, 0.0)).xyz;
          vec4 worldPos = uYawMat * vec4(aPos * 100.0, 1.0);
          gl_Position = uProj * uView * worldPos;
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir;
        uniform sampler2D uTex;
        uniform float uOffsetX;    // 0.0=left eye half, 0.5=right eye half of SBS
        uniform float uHalfFovH;   // horizontal half-FOV of photo in radians
        uniform float uAspect;     // photo aspect ratio (width/height of one eye)
        uniform float uScale;      // zoom: >1 = wider FOV (zoom out)
        uniform float uShiftU;     // signed UV shift in x for this eye
        uniform float uShiftV;     // signed UV shift in y for this eye
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float azimuth   = atan(d.x, -d.z);
          float elevation = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float vFov = hFov / uAspect;
          float u01 = azimuth   / (2.0 * hFov) + 0.5 + uShiftU;
          float v01 = elevation / (2.0 * vFov) + 0.5 + uShiftV;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
            return;
          }}
          float u = uOffsetX + u01 * 0.5;
          fragColor = texture(uTex, vec2(u, 1.0 - v01));
        }}`;

      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const prog = gl.createProgram();
      gl.attachShader(prog, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(prog, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(prog, 'uProj'),
        uView:     gl.getUniformLocation(prog, 'uView'),
        uYawMat:   gl.getUniformLocation(prog, 'uYawMat'),
        uTex:      gl.getUniformLocation(prog, 'uTex'),
        uOffsetX:  gl.getUniformLocation(prog, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(prog, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(prog, 'uAspect'),
        uScale:    gl.getUniformLocation(prog, 'uScale'),
        uShiftU:   gl.getUniformLocation(prog, 'uShiftU'),
        uShiftV:   gl.getUniformLocation(prog, 'uShiftV'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, separation, projMat, viewMat, yawDeg, eyeIsLeft, zoom, imgW, imgH, shiftU, shiftV) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);

      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);

      // Toe-in convergence: rotate sphere by yawDeg per eye
      const dir = eyeIsLeft ? 1.0 : -1.0;
      const rad = yawDeg * Math.PI / 180.0 * dir;
      const c = Math.cos(rad), s = Math.sin(rad);
      const yaw = new Float32Array([
         c, 0, s, 0,
         0, 1, 0, 0,
        -s, 0, c, 0,
         0, 0, 0, 1
      ]);
      gl.uniformMatrix4fv(sphere.uYawMat, false, yaw);

      // Phone horizontal FOV ≈ 65°; each SBS eye is half the full width
      const halfFovH = (65.0 / 2.0) * Math.PI / 180.0;
      // Aspect ratio of one eye (half of SBS width : full height)
      const aspect = (imgW / 2) / imgH;

      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, halfFovH);
      gl.uniform1f(sphere.uAspect, aspect);
      gl.uniform1f(sphere.uScale, zoom);
      // Per-eye opposite shifts so eyes converge on the panned region
      gl.uniform1f(sphere.uShiftU, shiftU * (eyeIsLeft ? 1.0 : -1.0));
      gl.uniform1f(sphere.uShiftV, shiftV);

      // Disable depth test — sphere is the only object; back-face culling must be off
      // so the inside of the sphere is visible.
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''



def render_video_sphere_page(*, theme_css_js, video_file):
    """Player 3 — sphere renderer (same as stills player) with per-frame video texture."""
    video_url = S3_VIDEO_BASE + video_file
    label = next((v["label"] for v in STEREO_VIDEOS if v["file"] == video_file), video_file)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{label}</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font); }}
    #ui {{ padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 16px; }}
    h1 {{ font-size: 1.2rem; color: var(--text); }}
    #preview {{ width: 100%; max-width: 600px; border-radius: 12px; }}
    #controls {{ display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 600px; }}
    .control-row {{
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); border-radius: 12px; padding: 12px 16px;
    }}
    .control-row label {{ color: var(--text-secondary); font-size: 0.9rem; }}
    .control-row input[type=range] {{ width: 55%; accent-color: var(--accent); }}
    .control-row span {{ color: var(--text); font-size: 0.9rem; min-width: 40px; text-align: right; }}
    .btn-row {{ display: flex; gap: 12px; width: 100%; max-width: 600px; }}
    button {{
      background: var(--accent); color: #fff; border: none;
      border-radius: 12px; padding: 14px 0; font-size: 1rem;
      cursor: pointer; flex: 1;
    }}
    button.secondary {{ background: var(--card-bg); color: var(--accent); border: 1px solid var(--divider); }}
    #status {{ color: var(--text-secondary); font-size: 0.85rem; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 1rem 0; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="ui">
    <h1>{label}</h1>
    <video id="preview" src="{video_url}" controls playsinline loop crossorigin="anonymous"></video>
    <div id="controls">
      <div class="control-row">
        <label>Convergence</label>
        <input type="range" id="convergence" min="-30" max="30" value="0" step="0.1">
        <span id="convergence-val">0.0°</span>
      </div>
    </div>
    <div class="btn-row">
      <button id="vr-btn">Enter VR</button>
      <button id="swap-btn" class="secondary">Order A</button>
    </div>
    <div id="status"></div>
    <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  </div>
  <canvas id="xr-canvas"></canvas>
  <script>
    const vid = document.getElementById('preview');
    const vrBtn = document.getElementById('vr-btn');
    const swapBtn = document.getElementById('swap-btn');
    const status = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    const convergenceSlider = document.getElementById('convergence');
    const convergenceVal = document.getElementById('convergence-val');

    let swapped = false;
    let zoom = 1.0;
    let xrSession = null, gl = null;

    convergenceSlider.addEventListener('input', () => {{
      convergenceVal.textContent = parseFloat(convergenceSlider.value).toFixed(1) + '°';
    }});
    swapBtn.addEventListener('click', () => {{
      swapped = !swapped;
      swapBtn.textContent = swapped ? 'Order B' : 'Order A';
    }});

    vrBtn.addEventListener('click', async () => {{
      if (xrSession) {{ await xrSession.end(); return; }}
      if (!navigator.xr) {{ status.textContent = 'WebXR not available'; return; }}
      const supported = await navigator.xr.isSessionSupported('immersive-vr');
      if (!supported) {{ status.textContent = 'Immersive VR not supported'; return; }}
      try {{
        xrSession = await navigator.xr.requestSession('immersive-vr', {{ requiredFeatures: ['local'] }});
        await startXR(xrSession);
      }} catch (e) {{ status.textContent = 'VR error: ' + e.message; }}
    }});

    async function startXR(session) {{
      vrBtn.textContent = 'Exit VR';
      canvas.style.display = 'block';
      gl = canvas.getContext('webgl2', {{ xrCompatible: true }});
      await gl.makeXRCompatible();
      const refSpace = await session.requestReferenceSpace('local');
      const layer = new XRWebGLLayer(session, gl);
      session.updateRenderState({{ baseLayer: layer }});

      const sphere = buildSphereRenderer(gl);

      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, vid.videoWidth || 1024, vid.videoHeight || 288, 0, gl.RGB, gl.UNSIGNED_BYTE, null);

      vid.play();

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};

      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);

        if (vid.readyState >= vid.HAVE_CURRENT_DATA) {{
          gl.bindTexture(gl.TEXTURE_2D, tex);
          gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGB, gl.UNSIGNED_BYTE, vid);
        }}

        for (const src of session.inputSources) {{
          const gp = src.gamepad; if (!gp) continue;
          const id = src.handedness;
          if (!wasPressed[id]) wasPressed[id] = {{}};

          const aBtn = gp.buttons[4];
          if (aBtn?.pressed && !wasPressed[id][4]) {{
            swapped = !swapped;
            swapBtn.textContent = swapped ? 'Order B' : 'Order A';
          }}
          wasPressed[id][4] = aBtn?.pressed;

          if (src.handedness === 'right') {{
            const trig = gp.buttons[0];
            if (trig?.pressed && !wasPressed[id][0]) vid.paused ? vid.play() : vid.pause();
            wasPressed[id][0] = trig?.pressed;

            const stickX = gp.axes[2] ?? 0;
            if (Math.abs(stickX) > 0.15) {{
              const val = Math.max(-30, Math.min(30, parseFloat(convergenceSlider.value) + stickX * 0.3));
              convergenceSlider.value = val;
              convergenceVal.textContent = val.toFixed(1) + '°';
            }}
            const stickY = gp.axes[3] ?? 0;
            if (Math.abs(stickY) > 0.15) zoom = Math.max(0.5, Math.min(3.0, zoom + stickY * 0.02));
          }}
          if (src.handedness === 'left') {{
            const trig = gp.buttons[0];
            if (trig?.pressed && !wasPressed[id][0]) session.end();
            wasPressed[id][0] = trig?.pressed;
          }}
        }}

        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const yawDeg = parseFloat(convergenceSlider.value);
        const vw = vid.videoWidth || 1024, vh = vid.videoHeight || 288;
        for (const view of pose.views) {{
          const vp = layer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          renderEyeSphere(gl, sphere, tex, eyeIsLeft ? 0.0 : 0.5, 1.0,
            view.projectionMatrix, view.transform.inverse.matrix, yawDeg, eyeIsLeft, zoom, vw, vh);
        }}
      }});
    }}

    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS;
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(Math.sin(phi)*Math.cos(theta), Math.cos(phi), Math.sin(phi)*Math.sin(theta));
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s*(SLICES+1)+sl, b = a+SLICES+1;
          indices.push(a, b, a+1, b, b+1, a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; uniform mat4 uProj, uView, uYawMat; out vec3 vDir;
        void main() {{
          vDir = (uYawMat * vec4(aPos, 0.0)).xyz;
          gl_Position = uProj * uView * uYawMat * vec4(aPos * 100.0, 1.0);
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir; uniform sampler2D uTex;
        uniform float uOffsetX, uHalfFovH, uAspect, uScale;
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float az = atan(d.x, -d.z);
          float el = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float vFov = hFov / uAspect;
          float u01 = az / (2.0 * hFov) + 0.5;
          float v01 = el / (2.0 * vFov) + 0.5;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0); return;
          }}
          fragColor = texture(uTex, vec2(uOffsetX + u01 * 0.5, 1.0 - v01));
        }}`;
      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const p = gl.createProgram();
      gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog: p, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(p, 'uProj'),
        uView:     gl.getUniformLocation(p, 'uView'),
        uYawMat:   gl.getUniformLocation(p, 'uYawMat'),
        uTex:      gl.getUniformLocation(p, 'uTex'),
        uOffsetX:  gl.getUniformLocation(p, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(p, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(p, 'uAspect'),
        uScale:    gl.getUniformLocation(p, 'uScale'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, separation, projMat, viewMat, yawDeg, eyeIsLeft, zoom, vidW, vidH) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);
      const dir = eyeIsLeft ? 1.0 : -1.0;
      const rad = yawDeg * Math.PI / 180.0 * dir;
      const c = Math.cos(rad), s = Math.sin(rad);
      gl.uniformMatrix4fv(sphere.uYawMat, false, new Float32Array([
        c,0,s,0, 0,1,0,0, -s,0,c,0, 0,0,0,1
      ]));
      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, (65.0 / 2.0) * Math.PI / 180.0);
      gl.uniform1f(sphere.uAspect, (vidW / 2) / vidH);
      gl.uniform1f(sphere.uScale, zoom);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''


def render_video_viewer_page(*, theme_css_js, video_file):
    """SBS video viewer — slate visible on load, fullscreen + WebXR options."""
    import random as _r
    video_url = S3_VIDEO_BASE + video_file
    label = next((v["label"] for v in STEREO_VIDEOS if v["file"] == video_file), video_file)
    # Build pet — random per cold-start of the Lambda. Stable within a Lambda
    # container (free CloudFront cache hits), changes after deploy/cold-start.
    if not hasattr(render_video_viewer_page, "_pet"):
        pets = ["badger","otter","heron","fox","squirrel","wren","hare","stoat",
                "puffin","mole","newt","kestrel","owl","crow","robin","sparrow",
                "weasel","ferret","dormouse","raven","magpie","starling","linnet"]
        render_video_viewer_page._pet = _r.choice(pets)
    page_pet = render_video_viewer_page._pet

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{label}</title>
  {theme_css_js}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #000; color: var(--text); font-family: var(--font); display: flex; flex-direction: column; align-items: center; min-height: 100vh; }}
    #video-wrap {{ width: 100%; max-width: 900px; padding: 1rem; }}
    video {{ width: 100%; border-radius: 8px; display: block; }}
    .hint {{ text-align: center; color: #8E8E93; font-size: 0.85rem; margin: 0.75rem 1rem; line-height: 1.6; max-width: 600px; }}
    .hint strong {{ color: #E0E0E0; }}
    .btn-row {{ display: flex; gap: 10px; justify-content: center; margin: 0.75rem; flex-wrap: wrap; }}
    button {{
      background: #007AFF; color: #fff; border: none;
      border-radius: 12px; padding: 12px 24px; font-size: 0.95rem; cursor: pointer;
    }}
    button.secondary {{ background: #161616; color: #007AFF; border: 1px solid #2C2C2E; }}
    button:disabled {{ background: #2C2C2E; color: #8E8E93; cursor: default; }}
    .footer {{ text-align: center; color: #8E8E93; font-size: 0.75rem; margin: 1rem; }}
    .footer a {{ color: #007AFF; text-decoration: none; }}
    #status {{
      min-height: 1.5em;
      padding: 8px 16px;
      margin: 0.5rem auto;
      max-width: 600px;
      background: #161616;
      color: #FF9500;
      font-family: monospace;
      font-size: 0.85rem;
      border-radius: 8px;
      text-align: center;
      border: 1px solid #2C2C2E;
    }}
    #xr-canvas {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; }}
  </style>
</head>
<body>
  <div id="video-wrap">
    <!-- preload=auto loads enough to show the slate frame; no autoplay so slate stays visible -->
    <video id="vid" src="{video_url}" controls playsinline loop preload="auto"></video>
  </div>
  <div class="hint">
    <strong>Quest: </strong>tap <strong>Play</strong> then <strong>Fullscreen</strong> — press <strong>O</strong> to push to background for stereo.<br>
    Or tap <strong>Enter VR</strong> for WebXR mode.
  </div>
  <div class="btn-row">
    <button id="fs-btn">Fullscreen</button>
    <button id="vr-btn">Enter VR</button>
    <button class="secondary" onclick="history.back()">&#8592; Back</button>
  </div>
  <div id="status"></div>
  <div style="text-align:center;color:#8E8E93;font-size:0.7rem;margin:0.5rem;">page: {page_pet}</div>
  <div class="footer"><a href="/stereo">&#8592; Gallery</a></div>
  <canvas id="xr-canvas"></canvas>

  <script>
    const vid = document.getElementById('vid');
    const vrBtn = document.getElementById('vr-btn');
    const statusEl = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    let xrSession = null, gl = null, prog = null, tex = null;

    statusEl.textContent = 'status will appear here';

    // Force seek to frame 0 so the slate is visible before the user presses play
    vid.addEventListener('loadedmetadata', () => {{ vid.currentTime = 0; }});
    vid.addEventListener('canplay', () => {{
      if (vid.paused) vid.currentTime = 0;
    }});

    // Fullscreen: try every API the Quest browser supports
    document.getElementById('fs-btn').addEventListener('click', () => {{
      vid.muted = false;
      vid.play();
      // Try fullscreen on the video element itself first (works on Quest)
      if (vid.webkitEnterFullscreen)       vid.webkitEnterFullscreen();
      else if (vid.requestFullscreen)      vid.requestFullscreen();
      else {{
        const el = document.getElementById('video-wrap');
        if (el.requestFullscreen)            el.requestFullscreen();
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
      }}
    }});

    // WebXR via XRMediaBinding — follows W3C media-layer-sample.html pattern.
    // Use a separate, NEVER-DOM-attached <video> for the layer source.
    let xrVideo = null;
    function makeXrVideo() {{
      const v = document.createElement('video');
      v.crossOrigin = 'anonymous';
      v.preload = 'auto';
      v.loop = true;
      v.muted = true;
      v.playsInline = true;
      v.setAttribute('playsinline', '');
      v.setAttribute('webkit-playsinline', '');
      v.src = vid.src;
      return v;
    }}

    // On page load, check decode capability for our video config.
    // Reports whether the codec/resolution will use hardware decode (powerEfficient).
    (async () => {{
      if (!navigator.mediaCapabilities) return;
      try {{
        const info = await navigator.mediaCapabilities.decodingInfo({{
          type: 'file',
          video: {{
            contentType: 'video/mp4; codecs="avc1.640028"',
            width: 1280, height: 360, bitrate: 5000000, framerate: 30,
          }},
        }});
        statusEl.textContent =
          `decode: smooth=${{info.smooth}} hw=${{info.powerEfficient}} sup=${{info.supported}}`;
      }} catch(e) {{ statusEl.textContent = 'mediaCapabilities error: ' + e.message; }}
    }})();

    vrBtn.addEventListener('click', async () => {{
      if (xrSession) {{ await xrSession.end(); return; }}
      if (!navigator.xr) {{ statusEl.textContent = 'WebXR not available'; return; }}
      const ok = await navigator.xr.isSessionSupported('immersive-vr');
      if (!ok) {{ statusEl.textContent = 'Immersive VR not supported'; return; }}

      // Create a fresh video element NOT attached to the DOM, per W3C reference.
      // Start playing in the same user gesture so autoplay policies are satisfied.
      xrVideo = makeXrVideo();
      try {{ await xrVideo.play(); }} catch(e) {{}}

      try {{
        statusEl.textContent = 'Requesting session...';
        xrSession = await navigator.xr.requestSession('immersive-vr', {{
          requiredFeatures: ['layers'],
        }});
        statusEl.textContent = 'Session granted, setting up layer...';
        onSessionStarted(xrSession);
      }} catch(e) {{
        statusEl.textContent = 'Session failed: ' + e.message;
      }}
    }});

    function onSessionStarted(session) {{
      vrBtn.textContent = 'Exit VR';
      session.addEventListener('end', onSessionEnded);

      const mediaFactory = new XRMediaBinding(session);

      session.requestReferenceSpace('local').then((refSpace) => {{
        const layer = mediaFactory.createQuadLayer(xrVideo, {{
          space: refSpace,
          layout: 'stereo-left-right',
          transform: new XRRigidTransform(
            {{x: 0, y: 0, z: -2}},
            {{x: 0, y: 0, z: 0, w: 1}}
          ),
          width: 2.0,
        }});
        session.updateRenderState({{ layers: [layer] }});
        statusEl.textContent = 'Playing';

        // Sample decode quality every second so we can see actual decode rate
        let lastFrames = 0, lastDropped = 0;
        const qInterval = setInterval(() => {{
          if (!xrVideo.getVideoPlaybackQuality) return;
          const q = xrVideo.getVideoPlaybackQuality();
          const decoded = q.totalVideoFrames - lastFrames;
          const dropped = q.droppedVideoFrames - lastDropped;
          lastFrames = q.totalVideoFrames;
          lastDropped = q.droppedVideoFrames;
          statusEl.textContent = `decoded ${{decoded}}/s  dropped ${{dropped}}/s`;
        }}, 1000);
        session.addEventListener('end', () => clearInterval(qInterval));

        const wasPressed = {{}};
        const ctrlInterval = setInterval(() => {{
          for (const src of session.inputSources) {{
            const gp = src.gamepad; if (!gp) continue;
            const id = src.handedness;
            if (!wasPressed[id]) wasPressed[id] = {{}};
            if (src.handedness === 'right') {{
              const trig = gp.buttons[0];
              if (trig?.pressed && !wasPressed[id][0]) {{
                xrVideo.paused ? xrVideo.play() : xrVideo.pause();
              }}
              wasPressed[id][0] = trig?.pressed;
            }}
            if (src.handedness === 'left') {{
              const trig = gp.buttons[0];
              if (trig?.pressed && !wasPressed[id][0]) session.end();
              wasPressed[id][0] = trig?.pressed;
            }}
          }}
        }}, 100);
        session.addEventListener('end', () => clearInterval(ctrlInterval));
      }});
    }}

    function onSessionEnded() {{
      vrBtn.textContent = 'Enter VR';
      if (xrVideo) {{ xrVideo.pause(); xrVideo.src = ''; xrVideo = null; }}
      xrSession = null;
      statusEl.textContent = '';
    }}

    function buildSphereRenderer(gl) {{
      const STACKS = 32, SLICES = 64;
      const verts = [], indices = [];
      for (let s = 0; s <= STACKS; s++) {{
        const phi = Math.PI * s / STACKS;
        for (let sl = 0; sl <= SLICES; sl++) {{
          const theta = 2 * Math.PI * sl / SLICES;
          verts.push(Math.sin(phi)*Math.cos(theta), Math.cos(phi), Math.sin(phi)*Math.sin(theta));
        }}
      }}
      for (let s = 0; s < STACKS; s++) {{
        for (let sl = 0; sl < SLICES; sl++) {{
          const a = s*(SLICES+1)+sl, b = a+SLICES+1;
          indices.push(a,b,a+1,b,b+1,a+1);
        }}
      }}
      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(indices), gl.STATIC_DRAW);

      const vs = `#version 300 es
        in vec3 aPos; uniform mat4 uProj, uView; out vec3 vDir;
        void main() {{
          vDir = aPos;
          gl_Position = uProj * uView * vec4(aPos * 100.0, 1.0);
        }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec3 vDir; uniform sampler2D uTex;
        uniform float uOffsetX, uHalfFovH, uAspect, uScale;
        out vec4 fragColor;
        void main() {{
          vec3 d = normalize(vDir);
          float az = atan(d.x, -d.z);
          float el = atan(d.y, length(d.xz));
          float hFov = uHalfFovH * uScale;
          float u01 = az / (2.0 * hFov) + 0.5;
          float v01 = el / (2.0 * hFov * uAspect) + 0.5;
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0); return;
          }}
          fragColor = texture(uTex, vec2(uOffsetX + u01 * 0.5, 1.0 - v01));
        }}`;
      const compile = (type, src) => {{
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      }};
      const p = gl.createProgram();
      gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
      gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      const posLoc = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 12, 0);
      gl.bindVertexArray(null);

      return {{
        prog: p, vao, indexCount: indices.length,
        uProj:     gl.getUniformLocation(p, 'uProj'),
        uView:     gl.getUniformLocation(p, 'uView'),
        uTex:      gl.getUniformLocation(p, 'uTex'),
        uOffsetX:  gl.getUniformLocation(p, 'uOffsetX'),
        uHalfFovH: gl.getUniformLocation(p, 'uHalfFovH'),
        uAspect:   gl.getUniformLocation(p, 'uAspect'),
        uScale:    gl.getUniformLocation(p, 'uScale'),
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, projMat, viewMat, zoom, vidW, vidH) {{
      gl.useProgram(sphere.prog);
      gl.bindVertexArray(sphere.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniformMatrix4fv(sphere.uProj, false, projMat);
      gl.uniformMatrix4fv(sphere.uView, false, viewMat);
      gl.uniform1i(sphere.uTex, 0);
      gl.uniform1f(sphere.uOffsetX, uOffset);
      gl.uniform1f(sphere.uHalfFovH, (65.0 / 2.0) * Math.PI / 180.0);
      gl.uniform1f(sphere.uAspect, (vidW / 2) / vidH);
      gl.uniform1f(sphere.uScale, zoom);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, sphere.indexCount, gl.UNSIGNED_INT, 0);
      gl.bindVertexArray(null);
    }}
  </script>
</body>
</html>'''
