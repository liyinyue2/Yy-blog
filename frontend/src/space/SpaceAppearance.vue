<script setup>
/** 界面设置 —— 主题（跟随系统 / 浅色 / 深色），存 localStorage，启动时在 main.js 应用 */
import { onMounted, ref } from 'vue'
import { vSlideBall } from '../directives/slideBall'

const MODES = [
  { v: 'auto', label: '跟随系统' },
  { v: 'light', label: '浅色' },
  { v: 'dark', label: '深色' },
]
const mode = ref('auto')
const sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)')

const apply = v => {
  const root = document.documentElement
  const dark = v === 'dark' || (v === 'auto' && sysDark && sysDark.matches)
  if (dark) root.dataset.theme = 'dark'
  else root.removeAttribute('data-theme')
  try { localStorage.setItem('theme', v) } catch { /* 隐私模式下忽略 */ }
}
const pick = v => { mode.value = v; apply(v) }
onMounted(() => {
  try { mode.value = localStorage.getItem('theme') || 'auto' } catch { mode.value = 'auto' }
  if (sysDark) sysDark.addEventListener('change', () => { if (mode.value === 'auto') apply('auto') })
})
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>界面设置</h2><p class="hint">主题偏好只影响当前浏览器，不写入站点设置</p></div>
    </header>

    <div class="card">
      <h3>主题</h3>
      <div class="seg" v-slide-ball>
        <button v-for="m in MODES" :key="m.v" type="button" class="chip"
                :class="{ 'is-active': mode === m.v }" @click="pick(m.v)">{{ m.label }}</button>
      </div>
      <p class="hint mt">深色基于同一套玻璃 token 反向取值：底、文字、玻璃填充与描边都会切换，选中球同理。</p>
    </div>
  </section>
</template>
