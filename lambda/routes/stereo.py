"""Stereo photography — gallery and WebXR viewer."""

import json
import boto3

S3_BUCKET = "petergrecian.co.uk"
S3_PREFIX = "stereo"
S3_BASE = "https://s3-eu-west-1.amazonaws.com/petergrecian.co.uk/stereo/"


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

      prog = buildShader(gl);

      session.addEventListener('end', () => {{
        canvas.style.display = 'none';
        vrBtn.textContent = 'Enter VR';
        xrSession = null;
      }});

      session.requestAnimationFrame(function frame(t, xrFrame) {{
        session.requestAnimationFrame(frame);
        const pose = xrFrame.getViewerPose(refSpace);
        if (!pose) return;
        gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const convergence = parseFloat(convergenceSlider.value);
        const separation = parseFloat(separationSlider.value);
        for (const view of pose.views) {{
          const vp = layer.getViewport(view);
          gl.viewport(vp.x, vp.y, vp.width, vp.height);
          const isLeft = view.eye === 'left';
          const eyeIsLeft = swapped ? !isLeft : isLeft;
          const uOffset = eyeIsLeft ? 0.0 : 0.5;
          const shiftNorm = (convergence / (img.naturalWidth / 2)) * 0.5 * (eyeIsLeft ? 1 : -1);
          renderEye(gl, prog, tex, uOffset, shiftNorm, separation);
        }}
      }});
    }}

    function renderEye(gl, prog, tex, uOffset, shiftNorm, separation) {{
      gl.useProgram(prog);
      const verts = new Float32Array([-1,-1, 1,-1, -1,1, 1,1]);
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);
      const posLoc = gl.getAttribLocation(prog, 'aPos');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
      gl.uniform1i(gl.getUniformLocation(prog, 'uTex'), 0);
      gl.uniform1f(gl.getUniformLocation(prog, 'uOffsetX'), uOffset + shiftNorm);
      gl.uniform1f(gl.getUniformLocation(prog, 'uSeparation'), separation);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      gl.deleteBuffer(buf);
    }}

    function buildShader(gl) {{
      const vs = `#version 300 es
        in vec2 aPos; out vec2 vUv;
        void main() {{ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }}`;
      const fs = `#version 300 es
        precision highp float;
        in vec2 vUv; uniform sampler2D uTex;
        uniform float uOffsetX; uniform float uSeparation;
        out vec4 fragColor;
        void main() {{
          float margin = (1.0 - uSeparation) * 0.25;
          float u = uOffsetX + (margin + vUv.x * uSeparation) * 0.5;
          fragColor = texture(uTex, vec2(u, 1.0 - vUv.y));
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
