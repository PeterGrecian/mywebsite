"""Stereo photography — gallery and WebXR viewer."""

import json
import boto3

S3_BUCKET = "petergrecian.co.uk"
S3_PREFIX = "stereo"
S3_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/"
S3_VIDEO_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/video/"

# Manually curated video list — add entries here after uploading to S3
STEREO_VIDEOS = [
    {"file": "may1-railway-sbs-1k.mp4", "label": "Railway — May 2026", "note": "5s · 1024×288 · 50% window in VR · 1-frame baseline"},
    {"file": "may1-train-sbs.mp4", "label": "Lift — May 2026", "note": "5s · needs rotation fix"},
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
    <a href="/stereo?video={v["file"]}" class="shot-card">
      <div class="shot-title">{v["label"]}</div>
      <div class="shot-meta">
        <span class="quality">{v["note"]}</span>
        <span class="timestamp">SBS MP4 · VR</span>
      </div>
    </a>'''

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
    let xrSession = null;
    let gl = null;
    let prog = null;

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

      const tex = gl.createTexture();
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
            img.naturalWidth, img.naturalHeight);
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
        out vec4 fragColor;
        void main() {{
          // Normalise direction; forward = -Z in world space
          vec3 d = normalize(vDir);
          // Angular offset from forward (-Z)
          float azimuth   = atan(d.x, -d.z);   // horizontal angle
          float elevation = atan(d.y, length(d.xz)); // vertical angle
          // Map angles to UV using effective FOV (zoom scales FOV)
          float hFov = uHalfFovH * uScale;
          float vFov = hFov / uAspect;
          float u01 = azimuth   / (2.0 * hFov) + 0.5;
          float v01 = elevation / (2.0 * vFov) + 0.5;
          // Discard pixels outside the photo's angular extent
          if (u01 < 0.0 || u01 > 1.0 || v01 < 0.0 || v01 > 1.0) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
            return;
          }}
          // Map into SBS half: u → [uOffsetX, uOffsetX+0.5]
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
      }};
    }}

    function renderEyeSphere(gl, sphere, tex, uOffset, separation, projMat, viewMat, yawDeg, eyeIsLeft, zoom, imgW, imgH) {{
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


def render_video_viewer_page(*, theme_css_js, video_file):
    """WebXR SBS video viewer. video_file is e.g. 'may1-railway-sbs.mp4'"""
    video_url = S3_VIDEO_BASE + video_file
    label = next((v["label"] for v in STEREO_VIDEOS if v["file"] == video_file), video_file)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stereo Video — {label}</title>
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
    <h1>{label}</h1>
    <video id="preview" src="{video_url}" controls playsinline crossorigin="anonymous" loop></video>
    <div id="controls">
      <div class="control-row">
        <label>Convergence</label>
        <input type="range" id="convergence" min="-200" max="200" value="0" step="1">
        <span id="convergence-val">0px</span>
      </div>
      <div class="control-row">
        <label>Eye separation</label>
        <input type="range" id="separation" min="0.3" max="1.0" value="0.5" step="0.01">
        <span id="separation-val">0.50</span>
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
    const video = document.getElementById('preview');
    const vrBtn = document.getElementById('vr-btn');
    const swapBtn = document.getElementById('swap-btn');
    const status = document.getElementById('status');
    const canvas = document.getElementById('xr-canvas');
    const convergenceSlider = document.getElementById('convergence');
    const separationSlider = document.getElementById('separation');
    const convergenceVal = document.getElementById('convergence-val');
    const separationVal = document.getElementById('separation-val');

    let swapped = false;
    let xrSession = null;
    let gl = null;
    let prog = null;
    let tex = null;

    convergenceSlider.addEventListener('input', () => {{
      convergenceVal.textContent = convergenceSlider.value + 'px';
    }});
    separationSlider.addEventListener('input', () => {{
      separationVal.textContent = parseFloat(separationSlider.value).toFixed(2);
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
        // Request 'layers' feature for native media layer compositing
        xrSession = await navigator.xr.requestSession('immersive-vr', {{
          requiredFeatures: ['local'],
          optionalFeatures: ['layers'],
        }});
        await startXR(xrSession);
      }} catch (e) {{
        status.textContent = 'VR error: ' + e.message;
      }}
    }});

    async function startXR(session) {{
      vrBtn.textContent = 'Exit VR';
      const refSpace = await session.requestReferenceSpace('local');

      // Use XRMediaQuadLayer (native compositing) if available — no CPU upload needed
      const hasLayers = !!XRMediaBinding;
      if (hasLayers) {{
        try {{
          await startWithMediaLayer(session, refSpace);
          return;
        }} catch(e) {{
          status.textContent = 'MediaLayer failed: ' + e.message + ' — falling back';
        }}
      }}
      // Fallback: WebGL texSubImage2D path
      await startWithWebGL(session, refSpace);
    }}

    async function startWithMediaLayer(session, refSpace) {{
      // XRMediaQuadLayer: compositor handles video natively at full frame rate
      // layout 'stereo-left-right' tells it the video is SBS — left half = left eye
      const mediaBinding = new XRMediaBinding(session);
      const quadLayer = mediaBinding.createQuadLayer(video, {{
        space: refSpace,
        layout: swapped ? 'stereo-right-left' : 'stereo-left-right',
        width: 2.0,   // 2m wide in world space
        height: 1.125, // 16:9 aspect (2.0 / 16 * 9)
      }});

      // Position the quad 2m in front of the viewer
      quadLayer.transform = new XRRigidTransform({{x: 0, y: 0, z: -2}});

      session.updateRenderState({{ layers: [quadLayer] }});
      video.play();

      status.textContent = 'Playing via Media Layer';

      session.addEventListener('end', () => {{
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};
      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);
        handleControllers(session, wasPressed, quadLayer, refSpace);
      }});
    }}

    async function startWithWebGL(session, refSpace) {{
      // WebGL fallback — video frames uploaded via texSubImage2D each frame
      canvas.style.display = 'block';
      gl = canvas.getContext('webgl2', {{ xrCompatible: true }});
      await gl.makeXRCompatible();
      const glLayer = new XRWebGLLayer(session, gl);
      session.updateRenderState({{ baseLayer: glLayer }});

      prog = buildShader(gl);
      tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, video.videoWidth, video.videoHeight, 0, gl.RGB, gl.UNSIGNED_BYTE, null);

      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      const quadBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
      const posLoc = gl.getAttribLocation(prog, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
      gl.bindVertexArray(null);

      gl.useProgram(prog);
      const uTex = gl.getUniformLocation(prog, 'uTex');
      const uOffsetX = gl.getUniformLocation(prog, 'uOffsetX');
      const uShift = gl.getUniformLocation(prog, 'uShift');
      const uSeparationLoc = gl.getUniformLocation(prog, 'uSeparation');
      const uAspect = gl.getUniformLocation(prog, 'uAspect');
      gl.uniform1i(uTex, 0);
      // Video is 16:9 per eye; pass aspect so shader can correct y margin
      gl.uniform1f(uAspect, (video.videoWidth / 2) / video.videoHeight);

      video.play();

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      const wasPressed = {{}};
      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);
        handleControllers(session, wasPressed, null, refSpace);

        if (video.readyState >= video.HAVE_CURRENT_DATA) {{
          gl.bindTexture(gl.TEXTURE_2D, tex);
          gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGB, gl.UNSIGNED_BYTE, video);
        }}

        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, glLayer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(prog);
        gl.bindVertexArray(vao);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, tex);
        const convergence = parseFloat(convergenceSlider.value);
        const separation = parseFloat(separationSlider.value);
        const shiftU = (video.videoWidth > 0) ? convergence / (video.videoWidth / 2) * 0.5 : 0;
        for (const view of pose.views) {{
          const vp = glLayer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          gl.uniform1f(uOffsetX, eyeIsLeft ? 0.0 : 0.5);
          gl.uniform1f(uShift, shiftU * (eyeIsLeft ? 1.0 : -1.0));
          gl.uniform1f(uSeparationLoc, separation);
          gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        }}
        gl.bindVertexArray(null);
      }});
    }}

    function handleControllers(session, wasPressed, quadLayer, refSpace) {{
      for (const src of session.inputSources) {{
        const gp = src.gamepad;
        if (!gp) continue;
        const id = src.handedness;
        if (!wasPressed[id]) wasPressed[id] = {{}};

        const aBtn = gp.buttons[4];
        if (aBtn?.pressed && !wasPressed[id][4]) {{
          swapped = !swapped;
          swapBtn.textContent = swapped ? 'Order B' : 'Order A';
          // Recreate layer with new layout if using media layers
          if (quadLayer) {{
            session.end(); // simplest — user re-enters with corrected swap
          }}
        }}
        wasPressed[id][4] = aBtn?.pressed;

        if (src.handedness === 'right') {{
          const trigger = gp.buttons[0];
          if (trigger?.pressed && !wasPressed[id][0]) {{
            video.paused ? video.play() : video.pause();
          }}
          wasPressed[id][0] = trigger?.pressed;

          const stick = gp.axes[2] ?? 0;
          if (Math.abs(stick) > 0.15 && !quadLayer) {{
            const val = Math.max(-200, Math.min(200,
              parseFloat(convergenceSlider.value) + stick * 3));
            convergenceSlider.value = val;
            convergenceVal.textContent = Math.round(val) + 'px';
          }}
        }}

        if (src.handedness === 'left') {{
          const trigger = gp.buttons[0];
          if (trigger?.pressed && !wasPressed[id][0]) session.end();
          wasPressed[id][0] = trigger?.pressed;
        }}
      }}
    }}

    function buildShader(gl) {{
      const vs = `#version 300 es
        in vec2 aPos; out vec2 vUv;
        void main() {{ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec2 vUv; uniform sampler2D uTex;
        uniform float uOffsetX;
        uniform float uShift;
        uniform float uSeparation;
        uniform float uAspect; // per-eye width/height (e.g. 1.78 for 16:9)
        out vec4 fragColor;
        void main() {{
          // Viewport aspect is ~1:1 on Quest; content is 16:9.
          // Scale margins so content fills width=uSeparation, height=uSeparation/uAspect
          float mx = (1.0 - uSeparation) * 0.5;
          float my = (1.0 - uSeparation / uAspect) * 0.5;
          if (vUv.x < mx || vUv.x > 1.0 - mx ||
              vUv.y < my || vUv.y > 1.0 - my) {{
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
            return;
          }}
          float cx = (vUv.x - mx) / uSeparation;
          float u = uOffsetX + clamp(cx * 0.5 + uShift, 0.0, 0.5);
          float v = (vUv.y - my) / (uSeparation / uAspect);
          fragColor = texture(uTex, vec2(u, 1.0 - v));
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
      return p;
    }}
  </script>
</body>
</html>'''
