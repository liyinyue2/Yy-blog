<script setup>
/**
 * DraggableLens — hero 的 Liquid Glass 大透镜（官方 demo 交互）
 * 自由拖拽 + 松手惯性滑行 + 活动范围边缘 rubber-band 回弹
 */
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { createGlass, supportsRefraction, spring } from '../glass/engine'

const lens = ref(null)
let ctrl = null
let stopX = null, stopY = null
let dragging = false
let lastPts = []
const OVER = 0.25

const render = () => lens.value.style.transform = `translate(${pos.x}px, ${pos.y}px)`
const pos = { x: 0, y: 0 }

/**
 * 活动范围（偏移坐标系）：透镜是 right 定位，初始基准 P0 在 hero 右侧，
 * pos 是相对 P0 的偏移 → 合法区间 = [-P0, host宽-透镜宽-P0]。
 * 之前把边界写成 [0, host宽-透镜宽]（绝对坐标系），
 * 导致向左/上拖被误判越界（跟手 25% 黏滞）、向右下可拖出屏幕。
 */
const base = { x: 0, y: 0 }   // pointerdown 时冻结的无 transform 基准位置

const bounds = () => {
  const hr = lens.value.parentElement.getBoundingClientRect()
  const lr = lens.value.getBoundingClientRect()
  return {
    minX: -base.x,
    maxX: hr.width - lr.width - base.x,
    minY: -base.y,
    maxY: hr.height - lr.height - base.y,
  }
}
const clampV = (v, minX, maxX) => Math.max(minX, Math.min(maxX, v))
const band = (v, minX, maxX) =>
  v < minX ? minX + (v - minX) * OVER :
  v > maxX ? maxX + (v - maxX) * OVER : v

const glide = (vx = 0, vy = 0) => {
  stopX?.(); stopY?.()
  const b = bounds()
  stopX = spring({
    from: pos.x,
    to: clampV(pos.x + vx * 0.12, b.minX, b.maxX),
    velocity: vx * 0.9,
    stiffness: 110, damping: 19,
    onUpdate: x => { pos.x = band(x, b.minX, b.maxX); render() },
    onSettle: () => { pos.x = clampV(pos.x, b.minX, b.maxX); render() },
  })
  stopY = spring({
    from: pos.y,
    to: clampV(pos.y + vy * 0.12, b.minY, b.maxY),
    velocity: vy * 0.9,
    stiffness: 110, damping: 19,
    onUpdate: y => { pos.y = band(y, b.minY, b.maxY); render() },
    onSettle: () => { pos.y = clampV(pos.y, b.minY, b.maxY); render() },
  })
}

const onDown = e => {
  dragging = true
  stopX?.(); stopY?.()
  const hr = lens.value.parentElement.getBoundingClientRect()
  const lr = lens.value.getBoundingClientRect()
  base.x = lr.left - hr.left - pos.x
  base.y = lr.top - hr.top - pos.y
  grab.dx = e.clientX - pos.x
  grab.dy = e.clientY - pos.y
  lastPts = [{ x: e.clientX, y: e.clientY, t: performance.now() }]
  lens.value.classList.add('is-grabbed')
  lens.value.setPointerCapture?.(e.pointerId)
  e.preventDefault()
}
const grab = { dx: 0, dy: 0 }

const onMove = e => {
  if (!dragging) return
  const b = bounds()
  const rawX = e.clientX - grab.dx, rawY = e.clientY - grab.dy
  pos.x = band(rawX, b.minX, b.maxX)
  pos.y = band(rawY, b.minY, b.maxY)
  render()
  lastPts.push({ x: e.clientX, y: e.clientY, t: performance.now() })
  if (lastPts.length > 6) lastPts.shift()
}

const onUp = () => {
  if (!dragging) return
  dragging = false
  lens.value.classList.remove('is-grabbed')
  let vx = 0, vy = 0
  const now = performance.now()
  const recent = lastPts.filter(pt => now - pt.t < 90)
  if (recent.length >= 2) {
    const a = recent[0], b = recent[recent.length - 1]
    const dt = Math.max((b.t - a.t) / 1000, 0.001)
    vx = Math.max(-2200, Math.min(2200, (b.x - a.x) / dt))
    vy = Math.max(-2200, Math.min(2200, (b.y - a.y) / dt))
  }
  glide(vx, vy)
}

onMounted(() => {
  if (supportsRefraction()) {
    ctrl = createGlass(lens.value, { radius: 999, bevelDepth: 30, scale: 44, aberration: 4, frost: 0 })
  } else {
    lens.value.classList.add('lg-fallback')
  }
})
onBeforeUnmount(() => { ctrl?.destroy(); stopX?.(); stopY?.() })
</script>

<template>
  <div
    ref="lens"
    class="hero-lens lg-surface"
    @pointerdown="onDown"
    @pointermove="onMove"
    @pointerup="onUp"
    @pointercancel="onUp"
  >
    <span>Liquid Glass</span>
  </div>
</template>

<style scoped>
.hero-lens {
  position: absolute; z-index: 5;
  width: clamp(220px, 24vw, 320px); height: clamp(220px, 24vw, 320px);
  right: clamp(24px, 12vw, 220px); top: clamp(140px, 24vh, 240px);
  display: grid; place-items: center;
  border-radius: 999px;
  cursor: grab; touch-action: none; user-select: none; -webkit-user-select: none;
}
.hero-lens span {
  font-size: clamp(30px, 3.4vw, 44px); font-weight: 700;
  letter-spacing: -.02em; color: var(--ink); pointer-events: none;
}
.hero-lens.is-grabbed { cursor: grabbing; }
.hero-lens.is-grabbed span { transform: scale(1.04); transition: transform var(--t-fast) var(--ease); }
@media (max-width: 900px) { .hero-lens { display: none; } }
</style>
