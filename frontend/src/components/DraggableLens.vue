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

const glide = (vx = 0, vy = 0) => {
  stopX?.(); stopY?.()
  const host = lens.value.parentElement
  const hr = host.getBoundingClientRect()
  const lr = lens.value.getBoundingClientRect()
  const maxX = hr.width - lr.width - (lr.left - hr.left - pos.x)
  const maxY = hr.height - lr.height - (lr.top - hr.top - pos.y)
  stopX = spring({
    from: pos.x, to: Math.max(0, Math.min(maxX, pos.x + vx * 0.14)), velocity: vx * 0.9,
    stiffness: 120, damping: 20,
    onUpdate: x => {
      // rubber-band：超出边界部分衰减
      pos.x = x < 0 ? x * OVER : x > maxX ? maxX + (x - maxX) * OVER : x
      render()
    },
    onSettle: () => { pos.x = Math.max(0, Math.min(maxX, pos.x)); render() },
  })
  stopY = spring({
    from: pos.y, to: Math.max(0, Math.min(maxY, pos.y + vy * 0.14)), velocity: vy * 0.9,
    stiffness: 120, damping: 20,
    onUpdate: y => {
      pos.y = y < 0 ? y * OVER : y > maxY ? maxY + (y - maxY) * OVER : y
      render()
    },
    onSettle: () => { pos.y = Math.max(0, Math.min(maxY, pos.y)); render() },
  })
}

const onDown = e => {
  dragging = true
  stopX?.(); stopY?.()
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
  const host = lens.value.parentElement
  const hr = host.getBoundingClientRect()
  const lr = lens.value.getBoundingClientRect()
  const maxX = hr.width - lr.width, maxY = hr.height - lr.height
  const rawX = e.clientX - grab.dx, rawY = e.clientY - grab.dy
  pos.x = rawX < 0 ? rawX * OVER : rawX > maxX ? maxX + (rawX - maxX) * OVER : rawX
  pos.y = rawY < 0 ? rawY * OVER : rawY > maxY ? maxY + (rawY - maxY) * OVER : rawY
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
