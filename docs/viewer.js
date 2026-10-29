// 3D-Ansicht des Hamsterpalasts. WebGL2, ohne Bibliotheken.
// Jedes Teil ist eine Platte: Vorder- und Rueckseite als Rechteck mit Textur
// (Alpha = Material, Rot = Gravur), Kanten als Vierecke entlang der Schnittkontur.
(function () {
  "use strict";
  const M = window.PALAST;
  const canvas = document.getElementById("gl");
  const gl = canvas.getContext("webgl2", { antialias: true });

  document.getElementById("mat").textContent = M.T;
  const files = document.getElementById("files");
  M.sheets.forEach(function (s, i) {
    const li = document.createElement("li");
    li.innerHTML = '<a href="' + s + '" download>Schnittplan Blatt ' + (i + 1) + "</a> (SVG)";
    files.appendChild(li);
  });

  if (!gl) {
    document.getElementById("view").innerHTML =
      '<p class="err">Dieser Browser kann kein WebGL2, die 3D-Ansicht fehlt deshalb.</p>';
    return;
  }

  // ------------------------------------------------------------ Shader
  const VS = `#version 300 es
  in vec3 aPos; in vec3 aNor; in vec2 aUV; in vec2 aLoc; in float aKind;
  uniform mat4 uMVP; uniform vec3 uOff;
  out vec3 vNor; out vec2 vUV; out vec2 vLoc; out float vKind;
  void main() {
    vNor = aNor; vUV = aUV; vLoc = aLoc; vKind = aKind;
    gl_Position = uMVP * vec4(aPos + uOff, 1.0);
  }`;
  const FS = `#version 300 es
  precision highp float;
  in vec3 vNor; in vec2 vUV; in vec2 vLoc; in float vKind;
  uniform sampler2D uTex; uniform vec3 uLight; uniform float uEng; uniform float uSeed;
  out vec4 outColor;
  void main() {
    vec3 col;
    if (vKind > 2.5) {
      // Boden (Einstreu)
      float g = fract(sin(dot(floor(vLoc * 0.5), vec2(12.9898, 78.233))) * 43758.5453);
      col = mix(vec3(0.90, 0.85, 0.74), vec3(0.95, 0.91, 0.82), g);
    } else {
      vec4 t = texture(uTex, vUV);
      if (vKind < 1.5 && t.a < 0.5) discard;
      float x = vLoc.x + uSeed * 37.0, y = vLoc.y + uSeed * 11.0;
      float ring = 0.5 + 0.5 * sin(y * 0.9 + sin(x * 0.06) * 2.5 + sin(x * 0.013 + uSeed) * 5.0);
      col = mix(vec3(0.88, 0.73, 0.53), vec3(0.80, 0.63, 0.43), ring * ring);
      if (vKind < 0.5) col = mix(col, vec3(0.48, 0.32, 0.19), t.r * uEng);
      if (vKind > 1.5) col = vec3(0.33, 0.22, 0.14);   // Brandkante
    }
    vec3 n = normalize(vNor);
    float d = max(dot(n, uLight), 0.0) * 0.75 + max(dot(n, -uLight), 0.0) * 0.15;
    outColor = vec4(col * (0.42 + d), 1.0);
  }`;

  function shader(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS));
  gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);
  const A = {}, U = {};
  ["aPos", "aNor", "aUV", "aLoc", "aKind"].forEach(function (n) { A[n] = gl.getAttribLocation(prog, n); });
  ["uMVP", "uOff", "uTex", "uLight", "uEng", "uSeed"].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });

  // ------------------------------------------------------------ Geometrie
  const T = M.T;
  function mesh(verts) {
    // verts: Folge von [x,y,z, nx,ny,nz, u,v, lx,ly, kind]
    const data = new Float32Array(verts);
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const st = 11 * 4;
    [["aPos", 3, 0], ["aNor", 3, 3], ["aUV", 2, 6], ["aLoc", 2, 8], ["aKind", 1, 10]].forEach(function (a) {
      gl.enableVertexAttribArray(A[a[0]]);
      gl.vertexAttribPointer(A[a[0]], a[1], gl.FLOAT, false, st, a[2] * 4);
    });
    gl.bindVertexArray(null);
    return { vao: vao, count: data.length / 11 };
  }

  function texture(p) {
    const s = Math.min(5, 2048 / Math.max(p.w, p.h));
    const c = document.createElement("canvas");
    c.width = Math.ceil(p.w * s);
    c.height = Math.ceil(p.h * s);
    const g = c.getContext("2d");
    g.setTransform(s, 0, 0, -s, 0, p.h * s);
    function trace(list) {
      g.beginPath();
      list.forEach(function (q) {
        g.moveTo(q.p[0], q.p[1]);
        for (let i = 2; i < q.p.length; i += 2) g.lineTo(q.p[i], q.p[i + 1]);
        if (q.c) g.closePath();
      });
    }
    trace(p.cut);
    g.fillStyle = "#000";
    g.fill("evenodd");
    if (p.eng.length) {
      g.globalCompositeOperation = "source-atop";
      trace(p.eng);
      g.strokeStyle = "#f00";
      g.lineWidth = 0.7;
      g.stroke();
    }
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, c);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return tex;
  }

  function at(p, x, y, t) {
    return [0, 1, 2].map(function (k) { return p.o[k] + x * p.u[k] + y * p.v[k] + t * p.n[k]; });
  }

  function pieceMesh(p) {
    const v = [];
    function quad(c, nor, kind) {
      // c: 4 Ecken [pos, uv, loc], Dreiecke 0-1-2, 0-2-3
      [0, 1, 2, 0, 2, 3].forEach(function (i) {
        v.push.apply(v, c[i][0].concat(nor, c[i][1], c[i][2], [kind]));
      });
    }
    function face(t, kind, sign) {
      const nor = p.n.map(function (k) { return k * sign; });
      quad([[0, 0], [p.w, 0], [p.w, p.h], [0, p.h]].map(function (q) {
        return [at(p, q[0], q[1], t), [q[0] / p.w, (p.h - q[1]) / p.h], q];
      }), nor, kind);
    }
    face(0, 0, -1);
    face(T, 1, 1);
    p.cut.forEach(function (q) {
      if (!q.c) return;
      const n = q.p.length / 2;
      for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const x0 = q.p[2 * i], y0 = q.p[2 * i + 1], x1 = q.p[2 * j], y1 = q.p[2 * j + 1];
        const dx = x1 - x0, dy = y1 - y0, l = Math.hypot(dx, dy) || 1;
        const nx = dy / l, ny = -dx / l;
        const nor = [0, 1, 2].map(function (k) { return nx * p.u[k] + ny * p.v[k]; });
        quad([[at(p, x0, y0, 0), [0, 0], [0, 0]], [at(p, x1, y1, 0), [0, 0], [0, 0]],
              [at(p, x1, y1, T), [0, 0], [0, 0]], [at(p, x0, y0, T), [0, 0], [0, 0]]], nor, 2);
      }
    });
    return mesh(v);
  }

  const pieces = M.pieces.map(function (p, i) {
    return { p: p, m: pieceMesh(p), tex: texture(p), seed: (i * 0.618) % 1 * 10 };
  });
  const G = 2000;
  const ground = mesh([[-G, -G], [G, -G], [G, G], [-G, -G], [G, G], [-G, G]].reduce(function (a, q) {
    return a.concat([q[0], q[1], -0.2, 0, 0, 1, 0, 0, q[0], q[1], 3]);
  }, []));

  // ------------------------------------------------------------ Matrizen
  function mul(a, b) {
    const r = new Float32Array(16);
    for (let i = 0; i < 4; i++)
      for (let j = 0; j < 4; j++) {
        let s = 0;
        for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
        r[i * 4 + j] = s;
      }
    return r;
  }
  function persp(fov, asp, n, f) {
    const t = 1 / Math.tan(fov / 2);
    return new Float32Array([t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]);
  }
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function norm(a) { const l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function lookAt(e, c, up) {
    const z = norm(sub(e, c)), x = norm(cross(up, z)), y = cross(z, x);
    return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
      -dot(x, e), -dot(y, e), -dot(z, e), 1]);
  }

  // ------------------------------------------------------------ Kamera
  const S = M.size;
  const home = { yaw: -2.05, pitch: 0.5, dist: 1.25 * Math.hypot(S[0], S[1], S[2]) * 1.15,
                 target: [S[0] / 2, S[1] / 2, S[2] * 0.35] };
  let cam = JSON.parse(JSON.stringify(home));
  function eye() {
    const cp = Math.cos(cam.pitch);
    return [cam.target[0] + cam.dist * cp * Math.cos(cam.yaw),
            cam.target[1] + cam.dist * cp * Math.sin(cam.yaw),
            cam.target[2] + cam.dist * Math.sin(cam.pitch)];
  }

  const ui = {
    explode: document.getElementById("explode"),
    lids: document.getElementById("lids"),
    bricks: document.getElementById("bricks"),
  };
  const q = new URLSearchParams(location.search);
  if (q.has("explode")) ui.explode.value = q.get("explode");
  if (q.get("lids") === "1") ui.lids.checked = true;
  if (q.has("yaw")) cam.yaw = parseFloat(q.get("yaw"));
  let lift = ui.lids.checked ? 1 : 0, liftGoal = lift, queued = false;

  function draw() {
    queued = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    gl.viewport(0, 0, w, h);
    gl.clearColor(0.87, 0.91, 0.93, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    const e = eye();
    const mvp = mul(persp(0.62, w / h, 10, 20000), lookAt(e, cam.target, [0, 0, 1]));
    gl.uniformMatrix4fv(U.uMVP, false, mvp);
    gl.uniform3fv(U.uLight, norm([-0.45, -0.7, 0.9]));
    gl.uniform1f(U.uEng, ui.bricks.checked ? 1 : 0);
    gl.uniform1i(U.uTex, 0);
    gl.activeTexture(gl.TEXTURE0);

    const ex = parseFloat(ui.explode.value) * 90;
    pieces.forEach(function (q) {
      const g = q.p.group;
      const up = g === "deckel_turm" || g === "deckel_haus" ? lift * 90 : 0;
      gl.uniform3fv(U.uOff, [q.p.ex[0] * ex, q.p.ex[1] * ex, q.p.ex[2] * ex + up]);
      gl.uniform1f(U.uSeed, q.seed);
      gl.bindTexture(gl.TEXTURE_2D, q.tex);
      gl.bindVertexArray(q.m.vao);
      gl.drawArrays(gl.TRIANGLES, 0, q.m.count);
    });
    gl.uniform3fv(U.uOff, [0, 0, 0]);
    gl.bindVertexArray(ground.vao);
    gl.drawArrays(gl.TRIANGLES, 0, ground.count);

    if (Math.abs(liftGoal - lift) > 0.001) {
      lift += (liftGoal - lift) * 0.15;
      request();
    } else {
      lift = liftGoal;
    }
  }
  function request() {
    if (!queued) { queued = true; requestAnimationFrame(draw); }
  }

  // ------------------------------------------------------------ Bedienung
  const ptrs = new Map();
  let pinch = 0;
  canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  canvas.addEventListener("pointerdown", function (e) {
    canvas.setPointerCapture(e.pointerId);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY, b: e.button });
    if (ptrs.size === 2) {
      const a = Array.from(ptrs.values());
      pinch = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y);
    }
  });
  canvas.addEventListener("pointermove", function (e) {
    const p = ptrs.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (ptrs.size === 2) {
      const a = Array.from(ptrs.values());
      const d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y);
      if (pinch > 0) cam.dist = Math.min(4000, Math.max(150, cam.dist * pinch / d));
      pinch = d;
    } else if (p.b === 2 || e.shiftKey) {
      const k = cam.dist / canvas.clientHeight * 0.75;
      const r = [Math.sin(cam.yaw), -Math.cos(cam.yaw), 0];
      cam.target[0] += (-dx * r[0]) * k;
      cam.target[1] += (-dx * r[1]) * k;
      cam.target[2] += dy * k;
    } else {
      cam.yaw -= dx * 0.008;
      cam.pitch = Math.min(1.5, Math.max(-0.05, cam.pitch + dy * 0.008));
    }
    request();
  });
  function up(e) { ptrs.delete(e.pointerId); pinch = 0; }
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("wheel", function (e) {
    e.preventDefault();
    cam.dist = Math.min(4000, Math.max(150, cam.dist * Math.exp(e.deltaY * 0.001)));
    request();
  }, { passive: false });
  ui.explode.addEventListener("input", request);
  ui.bricks.addEventListener("change", request);
  ui.lids.addEventListener("change", function () { liftGoal = ui.lids.checked ? 1 : 0; request(); });
  document.getElementById("reset").addEventListener("click", function () {
    cam = JSON.parse(JSON.stringify(home));
    request();
  });
  window.addEventListener("resize", request);
  request();
})();
