/**
 * glass-engine.js — iOS 26 Liquid Glass 折射引擎（原生 JS，零依赖）
 *
 * 算法与 Aceternity LiquidGlass 官方组件一致（MIT 来源已注明）：
 *   Canvas 位移贴图（圆角盒 SDF + Snell 折射）→ SVG feImage + feDisplacementMap
 *   → CSS backdrop-filter:url(#id)
 *
 * iOS 质感调校（修复"浑浊"）：
 *   - 色散默认关闭：RGB screen 混合在小元素浅色背景上会过曝发灰（浑浊主因）
 *   - frost/blur 默认 0：玻璃中心必须通透清晰，折射集中在边缘环带
 *   - tint 极轻（0.05）：白雾感来源
 *   - 边缘质感交给 CSS rim light（见 glass.css 的 .lg-rim）
 */

let seq = 0
const registry = new WeakMap()
let svgHost = null

export function supportsRefraction() {
  if (typeof CSS === 'undefined' || !CSS.supports) return false
  return CSS.supports('backdrop-filter', 'url(#x)') ||
         CSS.supports('-webkit-backdrop-filter', 'url(#x)')
}

/* ---------- 位移贴图（与官方一致） ---------- */

function sdRoundedBox(px, py, halfW, halfH, r) {
  const qx = Math.abs(px) - halfW + r
  const qy = Math.abs(py) - halfH + r
  const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0))
  const inside = Math.min(Math.max(qx, qy), 0)
  return inside + outside - r
}

function bendFromDepth(x) {
  const u = 1 - Math.min(1, Math.max(0, x))
  const denom = Math.pow(1 - Math.pow(u, 4), 0.75)
  if (denom < 1e-6) return 0
  const thetaI = Math.atan(Math.min(Math.pow(u, 3) / denom, 8))
  const sinT = Math.sin(thetaI) / 1.5
  if (sinT >= 1) return Math.sin(thetaI)
  return Math.sin(thetaI - Math.asin(sinT))
}

function buildPhiTable(bevelPx) {
  const n = Math.max(1, Math.ceil(bevelPx))
  const phi = new Float32Array(n + 1)
  for (let d = 1; d <= n; d++) phi[d] = phi[d - 1] + bendFromDepth(d / n)
  return phi
}

function samplePhi(phi, depth) {
  const max = phi.length - 1
  if (depth <= 0) return phi[0]
  if (depth >= max) return phi[max]
  const i = Math.floor(depth)
  const f = depth - i
  return phi[i] * (1 - f) + phi[i + 1] * f
}

function computeDisplacementData(opts) {
  const dpr = opts.dpr || 1
  const gain = opts.gain != null ? opts.gain : 1.35
  const light = opts.light || { x: -0.55, y: -0.85 }
  const lightLen = Math.hypot(light.x, light.y) || 1
  const lx = light.x / lightLen, ly = light.y / lightLen

  const W = Math.max(1, Math.round(opts.width * dpr))
  const H = Math.max(1, Math.round(opts.height * dpr))
  const halfW = W / 2, halfH = H / 2
  const r = Math.min(opts.radius * dpr, halfW, halfH)
  const bevel = Math.max(1, opts.bevelDepth * dpr)
  const phi = buildPhiTable(bevel)

  const field = new Float32Array(W * H)
  for (let y = 0; y < H; y++) {
    const py = y - halfH + 0.5
    for (let x = 0; x < W; x++) {
      const d = sdRoundedBox(x - halfW + 0.5, py, halfW, halfH, r)
      field[y * W + x] = d > 0 ? 0 : samplePhi(phi, Math.min(bevel, -d))
    }
  }

  const data = new Uint8ClampedArray(W * H * 4)
  for (let y = 0; y < H; y++) {
    const py = y - halfH + 0.5
    for (let x = 0; x < W; x++) {
      const px = x - halfW + 0.5
      const i = (y * W + x) << 2
      const d = sdRoundedBox(px, py, halfW, halfH, r)
      if (d > 0) {
        data[i] = data[i + 1] = data[i + 2] = 128
        data[i + 3] = 0
        continue
      }
      const x0 = Math.max(0, x - 1), x1 = Math.min(W - 1, x + 1)
      const y0 = Math.max(0, y - 1), y1 = Math.min(H - 1, y + 1)
      const dPhiX = (field[y * W + x1] - field[y * W + x0]) / (x1 - x0 || 1)
      const dPhiY = (field[y1 * W + x] - field[y0 * W + x]) / (y1 - y0 || 1)
      const dx = Math.max(-1, Math.min(1, dPhiX * gain))
      const dy = Math.max(-1, Math.min(1, dPhiY * gain))
      let specular = 0
      if (d >= -bevel) {
        const gx = sdRoundedBox(px + 1, py, halfW, halfH, r) -
                   sdRoundedBox(px - 1, py, halfW, halfH, r)
        const gy = sdRoundedBox(px, py + 1, halfW, halfH, r) -
                   sdRoundedBox(px, py - 1, halfW, halfH, r)
        const len = Math.hypot(gx, gy) || 1
        const dot = (gx / len) * lx + (gy / len) * ly
        const rim = 1 - Math.min(1, -d / bevel)
        specular = (Math.max(0, dot) + Math.max(0, -dot) * 0.35) * rim
      }
      data[i] = 128 + dx * 127
      data[i + 1] = 128 + dy * 127
      data[i + 2] = Math.round(specular * 255)
      data[i + 3] = 255
    }
  }
  return { data, width: W, height: H }
}

function generateDisplacementBlobUrl(opts) {
  const packed = computeDisplacementData(opts)
  const canvas = document.createElement('canvas')
  canvas.width = packed.width
  canvas.height = packed.height
  const ctx = canvas.getContext('2d')
  if (!ctx) return Promise.reject(new Error('2d context unavailable'))
  ctx.putImageData(new ImageData(packed.data, packed.width, packed.height), 0, 0)
  return new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) resolve(URL.createObjectURL(blob))
      else reject(new Error('encode failed'))
    }, 'image/png')
  })
}

/* ---------- SVG 滤镜 ---------- */

function buildFilterSvg(o) {
  const pad = Math.ceil(o.scale + o.aberration + 4)
  const px = (pad / Math.max(1, o.width)) * 100
  const py = (pad / Math.max(1, o.height)) * 100
  const region = `x="-${px.toFixed(3)}%" y="-${py.toFixed(3)}%" width="${(100 + 2 * px).toFixed(3)}%" height="${(100 + 2 * py).toFixed(3)}%"`
  const map = `<feImage href="${o.mapUrl}" xlink:href="${o.mapUrl}" x="0" y="0" width="${o.width}" height="${o.height}" result="map" preserveAspectRatio="none"/>`
  const displace = (s, result) =>
    `<feDisplacementMap in="SourceGraphic" in2="map" scale="${s}" xChannelSelector="R" yChannelSelector="G" result="${result}"/>`

  let body
  if (o.aberration <= 0) {
    // 无色散：单次位移，避免 screen 混合过曝（iOS 中心通透的关键）
    body = displace(o.scale, 'rgb')
  } else {
    body = displace(o.scale + o.aberration, 'dispR') +
      '<feColorMatrix in="dispR" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="red"/>' +
      displace(o.scale, 'dispG') +
      '<feColorMatrix in="dispG" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="green"/>' +
      displace(Math.max(0, o.scale - o.aberration), 'dispB') +
      '<feColorMatrix in="dispB" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="blue"/>' +
      '<feBlend in="red" in2="green" mode="screen" result="rg"/>' +
      '<feBlend in="rg" in2="blue" mode="screen" result="rgb"/>'
  }

  const frost = o.frost > 0 ? `<feGaussianBlur in="rgb" stdDeviation="${o.frost}"/>` : ''
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="0" height="0" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden"><filter id="${o.id}" color-interpolation-filters="sRGB" ${region}>${map}${body}${frost}</filter></svg>`
}

/* ---------- 元素增强 ---------- */

function ensureSvgHost() {
  if (!svgHost) {
    svgHost = document.createElement('div')
    svgHost.setAttribute('aria-hidden', 'true')
    svgHost.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden'
    document.body.appendChild(svgHost)
  }
  return svgHost
}

/**
 * 把折射玻璃挂到元素上。
 * opts: { radius, bevelDepth, scale, aberration, frost, gain }
 * 返回 { destroy() }。尺寸变化自动重建贴图。
 */
export function createGlass(el, opts = {}) {
  if (registry.has(el)) return registry.get(el).api
  const o = {
    radius: 16,
    bevelDepth: 10,
    scale: 32,
    aberration: 0,      // iOS 质感：默认关闭色散（浑浊主因）
    frost: 0,           // 中心通透
    gain: 1.35,
    ...opts,
  }
  // 官方行为：radius 同时决定 CSS 圆角与贴图形状（方形元素配圆形贴图会折射错乱）
  el.style.borderRadius = Math.min(o.radius, 999) + 'px'
  const state = { el, o, ro: null, blobUrl: null, destroyed: false }
  ensureSvgHost()

  const applyFallback = () => {
    if (state.destroyed) return
    el.style.backdropFilter = 'blur(18px) saturate(1.6)'
    el.style.webkitBackdropFilter = el.style.backdropFilter
    el.dataset.refract = 'false'
  }

  let rebuilding = null
  let lastW = 0, lastH = 0
  const rebuild = (w, h) => {
    if (state.destroyed || w === lastW && h === lastH) return
    lastW = w; lastH = h
    if (rebuilding) clearTimeout(rebuilding)
    rebuilding = setTimeout(() => {
      if (state.destroyed) return
      const radius = Math.min(o.radius, w / 2, h / 2)
      const bevel = Math.min(o.bevelDepth, Math.min(w, h) / 2)
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      generateDisplacementBlobUrl({ width: w, height: h, radius, bevelDepth: bevel, dpr, gain: o.gain })
        .then(mapUrl => new Promise(resolve => {
          const img = new Image()
          img.onload = img.onerror = resolve
          img.src = mapUrl
        }).then(() => mapUrl))
        .then(mapUrl => {
          if (state.destroyed) { URL.revokeObjectURL(mapUrl); return }
          if (state.blobUrl) URL.revokeObjectURL(state.blobUrl)
          state.blobUrl = mapUrl
          const id = `lg-${++seq}-${w}x${h}-${Date.now().toString(36)}`
          svgHost.insertAdjacentHTML('beforeend', buildFilterSvg({
            id, mapUrl, width: w, height: h,
            scale: o.scale, aberration: o.aberration, frost: o.frost,
          }))
          // iOS 质感链：纯折射 + 轻饱和提亮，无模糊无叠加
          const chain = `url(#${id}) saturate(1.8) brightness(1.03)`
          el.style.backdropFilter = chain
          el.style.webkitBackdropFilter = chain
          el.dataset.refract = 'true'
        })
        .catch(applyFallback)
    }, 80)
  }

  if ('ResizeObserver' in window) {
    state.ro = new ResizeObserver(entries => {
      const e = entries[0]
      if (!e) return
      const w = Math.max(1, Math.round(e.borderBoxSize ? e.borderBoxSize[0].inlineSize : e.contentRect.width))
      const h = Math.max(1, Math.round(e.borderBoxSize ? e.borderBoxSize[0].blockSize : e.contentRect.height))
      if (w <= 1 || h <= 1) return
      rebuild(w, h)
    })
    state.ro.observe(el)
  } else {
    const rect = el.getBoundingClientRect()
    rebuild(Math.max(1, Math.round(rect.width)), Math.max(1, Math.round(rect.height)))
  }

  state.api = {
    destroy() {
      state.destroyed = true
      state.ro?.disconnect()
      if (state.blobUrl) URL.revokeObjectURL(state.blobUrl)
      registry.delete(el)
    },
  }
  registry.set(el, state)
  return state.api
}

/* ---------- 阻尼弹簧（手势回弹/吸附动画） ---------- */

/**
 * damped spring 数值积分。返回 stop()。
 * onUpdate(x, v) 每帧回调；稳定后自动停止。
 */
export function spring({ from = 0, to = 0, velocity = 0, stiffness = 170, damping = 18, onUpdate, onSettle }) {
  let x = from, v = velocity, raf = null, last = performance.now()
  const step = now => {
    const dt = Math.min((now - last) / 1000, 1 / 30)
    last = now
    const a = (to - x) * stiffness - v * damping
    v += a * dt
    x += v * dt
    if (Math.abs(to - x) < 0.1 && Math.abs(v) < 0.1) {
      onUpdate(to, 0)
      onSettle?.()
      return
    }
    onUpdate(x, v)
    raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
  return () => cancelAnimationFrame(raf)
}
