/**
 * v-slide-ball —— 选中球：容器内唯一的「当前项」白玻璃，切换时弹性平移到新位置。
 *
 * 定位用 offsetLeft / offsetTop（相对最近定位祖先的 padding 边），
 * 不用 getBoundingClientRect：后者含视口偏移与缩放，是上一版小球恒定偏 2px 的根因。
 * 动画交给 CSS transition（合成器线程），JS 只负责写目标值。
 */
const STATE = new WeakMap()

function place(root, ball, opt) {
  const cur = root.querySelector(opt.active)
  if (!cur || !cur.offsetParent) { ball.style.opacity = '0'; return }
  ball.style.opacity = '1'
  ball.style.width = `${cur.offsetWidth + opt.pad * 2}px`
  ball.style.height = `${cur.offsetHeight + opt.pad * 2}px`
  ball.style.transform = `translate3d(${cur.offsetLeft - opt.pad}px, ${cur.offsetTop - opt.pad}px, 0)`
}

export const vSlideBall = {
  mounted(el, binding) {
    const opt = { pad: 0, radius: '', active: '.is-active', ...binding.value }
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative'

    const ball = document.createElement('span')
    ball.className = 'slide-ball'
    ball.setAttribute('aria-hidden', 'true')
    if (opt.radius) ball.style.borderRadius = opt.radius
    el.appendChild(ball)
    el.classList.add('has-ball')

    let raf = 0
    const sync = (animate) => {
      ball.style.transition = animate ? '' : 'none'
      place(el, ball, opt)
      if (!animate) requestAnimationFrame(() => { ball.style.transition = '' })
    }

    /* 选中类变化 / 增删子项 / 文字改宽度，都重新量一次；同一帧内合并 */
    const mo = new MutationObserver(() => {
      if (raf) return
      raf = requestAnimationFrame(() => { raf = 0; sync(true) })
    })
    mo.observe(el, { subtree: true, childList: true, characterData: true, attributeFilter: ['class'] })

    const ro = new ResizeObserver(() => sync(false))
    ro.observe(el)
    const onResize = () => sync(false)
    window.addEventListener('resize', onResize)
    if (document.fonts?.ready) document.fonts.ready.then(() => sync(false))

    sync(false)
    STATE.set(el, {
      cleanup() {
        mo.disconnect(); ro.disconnect()
        window.removeEventListener('resize', onResize)
        if (raf) cancelAnimationFrame(raf)
      },
    })
  },
  unmounted(el) {
    STATE.get(el)?.cleanup()
    STATE.delete(el)
  },
}
