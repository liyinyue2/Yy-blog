<script setup>
/**
 * GlassBall — 导航选中的 Liquid Glass 小球
 *
 * 交互（iOS 26 手感）：
 *  1. 平时弹性吸附在当前选中项上（路由切换时弹簧滑动）
 *  2. 可抓起随手势拖动，实时跟随手指
 *  3. 拖出导航边界 → rubber-band 橡皮筋阻力（超出部分按 25% 折算）
 *  4. 松手 → 带初速度弹簧吸附到最近导航项（fling 手感），并触发选中
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { createGlass, supportsRefraction, spring } from '../glass/engine'

const props = defineProps({
  container: { type: Object, required: true },   // 导航容器元素（ref）
  items: { type: Array, required: true },        // [{ el: HTMLElement, value }]
  active: { type: String, default: '' },
})
const emit = defineEmits(['select'])

const ball = ref(null)
const PAD_X = 7, PAD_Y = 4       // 球比项大一圈
const OVER_DRAG = 0.25           // rubber-band 阻力系数
let ctrl = null
let stopX = null, stopY = null
let pos = { x: 0, y: 0, w: 0, h: 0 }
let dragging = false

const itemRect = item => {
  const c = item.el.getBoundingClientRect(), p = props.container.getBoundingClientRect()
  return { x: c.left - p.left - PAD_X, y: c.top - p.top - PAD_Y, w: c.width + PAD_X * 2, h: c.height + PAD_Y * 2 }
}

const render = () => {
  const b = ball.value
  b.style.width = pos.w + 'px'
  b.style.height = pos.h + 'px'
  b.style.transform = `translate(${pos.x}px, ${pos.y}px)`
}

const activeIndex = () => Math.max(0, props.items.findIndex(it => it.value === props.active))

/* 弹簧滑到目标项（可带 fling 初速度，px/s） */
const glideTo = (index, vx = 0) => {
  stopX?.(); stopY?.()
  const r = itemRect(props.items[index])
  pos.w = r.w; pos.h = r.h
  stopX = spring({
    from: pos.x, to: r.x, velocity: vx,
    stiffness: 210, damping: 17,
    onUpdate: x => { pos.x = x; render() },
  })
  stopY = spring({
    from: pos.y, to: r.y,
    stiffness: 210, damping: 17,
    onUpdate: y => { pos.y = y; render() },
  })
}

/* 悬停跟随：指针扫过其他项时球追过去 */
const hoverTo = index => { if (!dragging) glideTo(index) }
defineExpose({ hoverTo })

/* ---------- 手势（事件挂导航容器：点在球上=抓起拖拽，点在文字上=正常导航） ---------- */
let grabOffset = { x: 0, y: 0 }
let lastPts = []
let intentX = 0   // 未 clamp 的指针意图位置（球被边界 band 压住时仍代表用户指向的项）

const nearestIndex = (fromX = pos.x + pos.w / 2) => {
  let best = 0, dist = Infinity
  props.items.forEach((it, i) => {
    const r = itemRect(it)
    const d = Math.abs(r.x + r.w / 2 - fromX)
    if (d < dist) { dist = d; best = i }
  })
  return best
}

const startDrag = e => {
  dragging = true
  stopX?.(); stopY?.()
  const p = props.container.getBoundingClientRect()
  grabOffset.x = e.clientX - p.left - pos.x
  grabOffset.y = e.clientY - p.top - pos.y
  lastPts = [{ x: e.clientX, y: e.clientY, t: performance.now() }]
  ball.value.classList.add('is-grabbed')
  props.container.setPointerCapture?.(e.pointerId)
  e.preventDefault()
}

const onNavPointerDown = e => {
  const p = props.container.getBoundingClientRect()
  const lx = e.clientX - p.left, ly = e.clientY - p.top
  const HIT = 5
  const inBall = lx >= pos.x - HIT && lx <= pos.x + pos.w + HIT &&
                 ly >= pos.y - HIT && ly <= pos.y + pos.h + HIT
  if (inBall) startDrag(e)
}

const onNavPointerMove = e => {
  if (!dragging) return
  const p = props.container.getBoundingClientRect()
  const rawX = e.clientX - p.left - grabOffset.x
  const rawY = e.clientY - p.top - grabOffset.y
  intentX = rawX + pos.w / 2
  const maxX = p.width - pos.w, maxY = p.height - pos.h
  const band = (v, max) => v < 0 ? v * OVER_DRAG : v > max ? max + (v - max) * OVER_DRAG : v
  pos.x = band(rawX, maxX)
  pos.y = band(rawY, maxY)
  render()
  lastPts.push({ x: e.clientX, y: e.clientY, t: performance.now() })
  if (lastPts.length > 6) lastPts.shift()
}

const onNavPointerUp = () => {
  if (!dragging) return
  dragging = false
  ball.value.classList.remove('is-grabbed')
  // fling 初速度：取最近 ~80ms 的指针速度
  let vx = 0
  const now = performance.now()
  const recent = lastPts.filter(pt => now - pt.t < 80)
  if (recent.length >= 2) {
    const a = recent[0], b = recent[recent.length - 1]
    const dt = Math.max((b.t - a.t) / 1000, 0.001)
    const pv = (b.x - a.x) / dt
    vx = Math.sign(pv) * Math.min(Math.abs(pv) * 0.9, 2400)
  }
  const idx = nearestIndex(intentX || pos.x + pos.w / 2)
  glideTo(idx, vx)
  const item = props.items[idx]
  if (item && item.value !== props.active) emit('select', item.value)
}

/* 初始化：定位到当前项 + 挂折射（items 就绪后才执行，父组件异步填充 items） */
let inited = false
const init = () => {
  if (inited || !props.items.length || !props.container) return
  inited = true
  pos = itemRect(props.items[activeIndex()])
  render()
  if (supportsRefraction()) {
    ctrl = createGlass(ball.value, { radius: 999, bevelDepth: 8, scale: 26, aberration: 0, frost: 0 })
  } else {
    ball.value.classList.add('lg-fallback')
  }
  ro?.observe(props.container)
  /* 手势事件挂在容器上（命中球才抓取，不拦截导航点击） */
  props.container.addEventListener('pointerdown', onNavPointerDown)
  props.container.addEventListener('pointermove', onNavPointerMove)
  props.container.addEventListener('pointerup', onNavPointerUp)
  props.container.addEventListener('pointercancel', onNavPointerUp)
}

onMounted(init)
watch(() => props.items, init)
watch(() => props.active, () => { if (!dragging) glideTo(activeIndex()) })

const ro = 'ResizeObserver' in window ? new ResizeObserver(() => {
  if (dragging) return
  const r = itemRect(props.items[activeIndex()])
  pos = { x: r.x, y: r.y, w: r.w, h: r.h }
  render()
}) : null

onBeforeUnmount(() => {
  ctrl?.destroy(); stopX?.(); stopY?.(); ro?.disconnect()
  const c = props.container
  if (c) {
    c.removeEventListener('pointerdown', onNavPointerDown)
    c.removeEventListener('pointermove', onNavPointerMove)
    c.removeEventListener('pointerup', onNavPointerUp)
    c.removeEventListener('pointercancel', onNavPointerUp)
  }
})
</script>

<template>
  <span
    ref="ball"
    class="glass-ball lg-surface"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  ><span class="ball-inner" /></span>
</template>
