/*!
 * liquid-glass.js — 真实折射玻璃（原生 JS/CSS 移植版）
 *
 * 改编自 Aceternity UI 的 LiquidGlass 组件（React/TSX）：
 *   来源: https://ui.aceternity.com/components/liquid-glass
 *   版权: 归 Aceternity UI 所有，遵循其站点公布的免费使用条款；
 *         本文件为集成于 Yy-blog 项目的改编移植，非独立再分发。
 *
 * 实现机制（与官方一致）：
 *   1. Canvas 生成位移贴图：圆角盒 SDF + Snell 折射定律弯曲场，
 *      R=水平位移 G=垂直位移 B=边缘高光 A=形状遮罩（中性灰 128 = 零位移）
 *   2. SVG 滤镜：feImage(贴图) → feDisplacementMap ×3（色散：RGB 三通道
 *      分别位移后 feColorMatrix 分离、feBlend screen 混合）→ feGaussianBlur(frost)
 *   3. 整个滤镜经 CSS backdrop-filter: url(#id) 作用于元素背后内容
 *
 * 降级（与官方一致）：
 *   Chromium（支持 backdrop-filter: url(#id)）→ 真实折射
 *   Safari / Firefox / 不支持的环境           → 磨砂 blur(20px) saturate(1.4)
 *   prefers-reduced-transparency: reduce      → 不透明玻璃（无模糊）
 *
 * 用法：给元素加 data-liquid-glass 属性即可。
 * 可选参数（data 属性）：data-lg-radius / data-lg-bevel / data-lg-scale /
 *   data-lg-aberration / data-lg-frost / data-lg-tint
 * 动态插入的节点需手动调用 LiquidGlass.scan(container)。
 */
(function () {
  'use strict';

  var seq = 0;
  var registry = new WeakMap();          // el → state
  var svgHost = null;                    // 全站共享的滤镜注入容器

  /* ---------- 能力检测（与官方判定一致） ---------- */
  function supportsUrlBackdropFilter() {
    if (typeof CSS === 'undefined' || !CSS.supports) return false;
    return CSS.supports('backdrop-filter', 'url(#x)') ||
           CSS.supports('-webkit-backdrop-filter', 'url(#x)');
  }
  function prefersReducedTransparency() {
    return window.matchMedia &&
      window.matchMedia('(prefers-reduced-transparency: reduce)').matches;
  }
  function isSafariLike() {
    var ua = navigator.userAgent;
    return /Safari/.test(ua) && !/Chrome|Chromium|Edg|OPR/.test(ua);
  }

  /* ---------- 位移贴图（算法原样移植自官方） ---------- */

  /** 圆角盒 SDF，<0 在内部 */
  function sdRoundedBox(px, py, halfW, halfH, r) {
    var qx = Math.abs(px) - halfW + r;
    var qy = Math.abs(py) - halfH + r;
    var outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0));
    var inside = Math.min(Math.max(qx, qy), 0);
    return inside + outside - r;
  }

  /** Squircle 穹顶坡度 → Snell 折射弯曲。x: 0=边缘 1=中心 */
  function bendFromDepth(x) {
    var u = 1 - Math.min(1, Math.max(0, x));
    var denom = Math.pow(1 - Math.pow(u, 4), 0.75);
    if (denom < 1e-6) return 0;
    var thetaI = Math.atan(Math.min(Math.pow(u, 3) / denom, 8));
    var sinT = Math.sin(thetaI) / 1.5;
    if (sinT >= 1) return Math.sin(thetaI);
    return Math.sin(thetaI - Math.asin(sinT));
  }

  /** φ(d) = 沿边缘距离对 bend 的积分（查表用） */
  function buildPhiTable(bevelPx) {
    var n = Math.max(1, Math.ceil(bevelPx));
    var phi = new Float32Array(n + 1);
    for (var d = 1; d <= n; d++) phi[d] = phi[d - 1] + bendFromDepth(d / n);
    return phi;
  }

  function samplePhi(phi, depth) {
    var max = phi.length - 1;
    if (depth <= 0) return phi[0];
    if (depth >= max) return phi[max];
    var i = Math.floor(depth);
    var f = depth - i;
    return phi[i] * (1 - f) + phi[i + 1] * f;
  }

  function computeDisplacementData(opts) {
    var dpr = opts.dpr || 1;
    var gain = opts.gain != null ? opts.gain : 1.35;
    var light = opts.light || { x: -0.55, y: -0.85 };
    var lightLen = Math.hypot(light.x, light.y) || 1;
    var lx = light.x / lightLen, ly = light.y / lightLen;

    var W = Math.max(1, Math.round(opts.width * dpr));
    var H = Math.max(1, Math.round(opts.height * dpr));
    var halfW = W / 2, halfH = H / 2;
    var r = Math.min(opts.radius * dpr, halfW, halfH);
    var bevel = Math.max(1, opts.bevelDepth * dpr);
    var phi = buildPhiTable(bevel);

    // 高度场：随后沿其梯度方向位移
    var field = new Float32Array(W * H);
    for (var y = 0; y < H; y++) {
      var py = y - halfH + 0.5;
      for (var x = 0; x < W; x++) {
        var d0 = sdRoundedBox(x - halfW + 0.5, py, halfW, halfH, r);
        field[y * W + x] = d0 > 0 ? 0 : samplePhi(phi, Math.min(bevel, -d0));
      }
    }

    var data = new Uint8ClampedArray(W * H * 4);
    for (y = 0; y < H; y++) {
      py = y - halfH + 0.5;
      for (x = 0; x < W; x++) {
        var px = x - halfW + 0.5;
        var i = (y * W + x) << 2;
        var d = sdRoundedBox(px, py, halfW, halfH, r);

        if (d > 0) { // 形状外：透明 + 零位移
          data[i] = data[i + 1] = data[i + 2] = 128;
          data[i + 3] = 0;
          continue;
        }

        var x0 = Math.max(0, x - 1), x1 = Math.min(W - 1, x + 1);
        var y0 = Math.max(0, y - 1), y1 = Math.min(H - 1, y + 1);
        var dPhiX = (field[y * W + x1] - field[y * W + x0]) / (x1 - x0 || 1);
        var dPhiY = (field[y1 * W + x] - field[y0 * W + x]) / (y1 - y0 || 1);

        // 限幅：边缘压缩但不折叠
        var dx = Math.max(-1, Math.min(1, dPhiX * gain));
        var dy = Math.max(-1, Math.min(1, dPhiY * gain));

        var specular = 0;
        if (d >= -bevel) {
          var gx = sdRoundedBox(px + 1, py, halfW, halfH, r) -
                   sdRoundedBox(px - 1, py, halfW, halfH, r);
          var gy = sdRoundedBox(px, py + 1, halfW, halfH, r) -
                   sdRoundedBox(px, py - 1, halfW, halfH, r);
          var len = Math.hypot(gx, gy) || 1;
          var dot = (gx / len) * lx + (gy / len) * ly;
          var rim = 1 - Math.min(1, -d / bevel);
          specular = (Math.max(0, dot) + Math.max(0, -dot) * 0.35) * rim;
        }

        data[i]     = 128 + dx * 127;
        data[i + 1] = 128 + dy * 127;
        data[i + 2] = Math.round(specular * 255);
        data[i + 3] = 255;
      }
    }
    return { data: data, width: W, height: H };
  }

  /** 贴图编码为 PNG blob URL（官方注：WebKit 拒绝 feImage 内的 data: URI） */
  function generateDisplacementBlobUrl(opts) {
    var packed = computeDisplacementData(opts);
    var canvas = document.createElement('canvas');
    canvas.width = packed.width;
    canvas.height = packed.height;
    var ctx = canvas.getContext('2d');
    if (!ctx) return Promise.reject(new Error('2d context unavailable'));
    ctx.putImageData(new ImageData(packed.data, packed.width, packed.height), 0, 0);
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (blob) {
        if (blob) resolve(URL.createObjectURL(blob));
        else reject(new Error('encode failed'));
      }, 'image/png');
    });
  }

  /* ---------- SVG 滤镜构建（结构原样移植自官方） ---------- */
  function buildFilterSvg(o) {
    var pad = Math.ceil(o.scale + o.aberration + 4);
    var px = (pad / Math.max(1, o.width)) * 100;
    var py = (pad / Math.max(1, o.height)) * 100;
    var region = 'x="-' + px.toFixed(3) + '%" y="-' + py.toFixed(3) + '%" width="' +
                 (100 + 2 * px).toFixed(3) + '%" height="' + (100 + 2 * py).toFixed(3) + '%"';

    // 像素级贴图与镜片精确匹配（百分比单位会冲淡边缘弯曲）
    var map = '<feImage href="' + o.mapUrl + '" xlink:href="' + o.mapUrl +
              '" x="0" y="0" width="' + o.width + '" height="' + o.height +
              '" result="map" preserveAspectRatio="none"/>';
    var displace = function (s, result) {
      return '<feDisplacementMap in="SourceGraphic" in2="map" scale="' + s +
             '" xChannelSelector="R" yChannelSelector="G" result="' + result + '"/>';
    };

    // 无色散时单次位移，避免 screen 混合接缝
    var body;
    if (o.aberration <= 0) {
      body = displace(o.scale, 'rgb');
    } else {
      body = displace(o.scale + o.aberration, 'dispR') +
        '<feColorMatrix in="dispR" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="red"/>' +
        displace(o.scale, 'dispG') +
        '<feColorMatrix in="dispG" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="green"/>' +
        displace(Math.max(0, o.scale - o.aberration), 'dispB') +
        '<feColorMatrix in="dispB" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="blue"/>' +
        '<feBlend in="red" in2="green" mode="screen" result="rg"/>' +
        '<feBlend in="rg" in2="blue" mode="screen" result="rgb"/>';
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ' +
      'width="0" height="0" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">' +
      '<filter id="' + o.id + '" color-interpolation-filters="sRGB" ' + region + '>' +
      map + body +
      '<feGaussianBlur in="rgb" stdDeviation="' + o.frost + '"/>' +
      '</filter></svg>';
  }

  /* ---------- 元素增强 ---------- */
  function readOpts(el) {
    var num = function (name, dflt) {
      var v = parseFloat(el.getAttribute('data-lg-' + name));
      return isNaN(v) ? dflt : v;
    };
    // 默认值与官方组件一致：radius 999 / bevel 14 / scale 48 / aberration 4 / frost 0.4
    return {
      radius: num('radius', 999),
      bevelDepth: num('bevel', 14),
      scale: num('scale', 48),
      aberration: num('aberration', 4),
      frost: num('frost', 0.4),
      draggable: el.hasAttribute('data-lg-draggable'),
    };
  }

  function ensureSvgHost() {
    if (!svgHost) {
      svgHost = document.createElement('div');
      svgHost.setAttribute('aria-hidden', 'true');
      svgHost.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
      (document.body || document.documentElement).appendChild(svgHost);
    }
    return svgHost;
  }

  function applyFallback(el, reduced) {
    el.classList.add(reduced ? 'lg-opaque' : 'lg-frosted');
    el.style.backdropFilter = reduced ? 'none' : 'blur(20px) saturate(1.4)';
    el.style.webkitBackdropFilter = el.style.backdropFilter;
    el.setAttribute('data-refract', reduced ? 'opaque' : 'false');
  }

  function enhance(el) {
    if (registry.has(el)) return;
    var opts = readOpts(el);
    var state = { el: el, opts: opts, ro: null, blobUrl: null };
    registry.set(el, state);
    el.classList.add('lg-glass');
    // 官方行为：radius 同时决定 CSS 圆角与贴图形状（显式指定时才覆盖 CSS）
    if (!isNaN(parseFloat(el.getAttribute('data-lg-radius')))) {
      el.style.borderRadius = Math.min(opts.radius, 999) + 'px';
    }
    ensureSvgHost();

    if (prefersReducedTransparency()) { applyFallback(el, true); return; }
    if (isSafariLike() || !supportsUrlBackdropFilter()) { applyFallback(el, false); return; }

    // 折射模式：tint 底色交给 CSS（亮暗主题各自定义 --lg-tint）
    el.classList.add('lg-refract');

    var rebuilding = null;
    var lastW = 0, lastH = 0;
    var rebuild = function (w, h) {
      if (w === lastW && h === lastH) return;
      lastW = w; lastH = h;
      if (rebuilding) clearTimeout(rebuilding);
      rebuilding = setTimeout(function () {
        rebuilding = null;
        var radius = Math.min(opts.radius, w / 2, h / 2);
        var bevel = Math.min(opts.bevelDepth, Math.min(w, h) / 2);
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        generateDisplacementBlobUrl({ width: w, height: h, radius: radius, bevelDepth: bevel, dpr: dpr })
          .then(function (mapUrl) {
            return new Promise(function (resolve) { // 先解码再挂滤镜（官方同款）
              var img = new Image();
              img.onload = img.onerror = resolve;
              img.src = mapUrl;
            }).then(function () { return mapUrl; });
          })
          .then(function (mapUrl) {
            if (state.blobUrl) URL.revokeObjectURL(state.blobUrl);
            state.blobUrl = mapUrl;
            // 每次重建换新 id：浏览器会按 id 缓存滤镜输出（官方同款）
            var id = 'lg-' + (++seq) + '-' + w + 'x' + h + '-' + Date.now().toString(36);
            svgHost.insertAdjacentHTML('beforeend',
              buildFilterSvg({ id: id, mapUrl: mapUrl, width: w, height: h,
                               scale: opts.scale, aberration: opts.aberration, frost: opts.frost }));
            var chain = 'url(#' + id + ') blur(0.5px) saturate(1.85) brightness(1.02)';
            el.style.backdropFilter = chain;
            el.style.webkitBackdropFilter = chain;
            el.setAttribute('data-refract', 'true');
          })
          .catch(function () { applyFallback(el, false); });
      }, 80);
    };

    if ('ResizeObserver' in window) {
      state.ro = new ResizeObserver(function (entries) {
        var e = entries[0];
        if (!e) return;
        var w = Math.max(1, Math.round(e.borderBoxSize ? e.borderBoxSize[0].inlineSize : e.contentRect.width));
        var h = Math.max(1, Math.round(e.borderBoxSize ? e.borderBoxSize[0].blockSize : e.contentRect.height));
        if (w <= 1 || h <= 1) return;
        rebuild(w, h);
      });
      state.ro.observe(el);
    } else {
      var rect = el.getBoundingClientRect();
      rebuild(Math.max(1, Math.round(rect.width)), Math.max(1, Math.round(rect.height)));
    }

    if (opts.draggable) enableDrag(el);
  }

  /** 官方 demo 交互：透镜可拖拽（Pointer Events，含触摸） */
  function enableDrag(el) {
    el.classList.add('lg-draggable');
    var sx = 0, sy = 0, ox = 0, oy = 0, dragging = false;
    el.addEventListener('pointerdown', function (e) {
      dragging = true;
      sx = e.clientX - ox; sy = e.clientY - oy;
      el.classList.add('is-dragging');
      if (el.setPointerCapture) el.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    // 兼容事件与原生拖选一并拦掉（pointerdown 的 preventDefault 不覆盖它们）
    el.addEventListener('mousedown', function (e) { e.preventDefault(); });
    el.addEventListener('dragstart', function (e) { e.preventDefault(); });
    el.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      ox = e.clientX - sx; oy = e.clientY - sy;
      el.style.transform = 'translate(' + ox + 'px,' + oy + 'px)';
    });
    var end = function (e) {
      if (!dragging) return;
      dragging = false;
      el.classList.remove('is-dragging');
      if (el.releasePointerCapture && e.pointerId != null) {
        try { el.releasePointerCapture(e.pointerId); } catch (err) {}
      }
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  }

  /** 扫描并增强容器内所有 [data-liquid-glass] 元素 */
  function scan(root) {
    var els = (root || document).querySelectorAll('[data-liquid-glass]');
    for (var i = 0; i < els.length; i++) {
      try { enhance(els[i]); } catch (e) { /* 单个失败不影响其余 */ }
    }
  }

  window.LiquidGlass = { scan: scan };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { scan(); });
  } else {
    scan();
  }
})();
