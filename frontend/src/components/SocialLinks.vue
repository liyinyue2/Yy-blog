<script setup>
/**
 * SocialLinks — 社交链接区（1:1 复刻原版 socials）
 * 数据来自站点设置 social_wechat/qq/douyin/github；
 * 值是链接 → 新窗口打开；是文本 → 点击复制并提示。
 */
import { ref, onMounted } from 'vue'
import { loadSettings } from '../composables/useSettings'

const ICONS = {
  wechat: 'M385.2 167.6c6.4 0 12.6.3 18.7 1.2C387.4 90.3 303.3 32 207.7 32 100.5 32 13 104.8 13 197.4c0 53.4 29.3 97.5 77.9 131.6l-19.3 58.6 68-34.1c24.4 4.8 43.8 9.7 68.2 9.7 6.2 0 12.1-.3 18.3-.8-4.1-14-6.5-28.7-6.5-44 0-83.4 74.5-150.8 165.6-150.8zm-105.5-52.5c15 0 27.2 12.1 27.2 27.2s-12.2 27.2-27.2 27.2c-15 0-27.2-12.1-27.2-27.2s12.2-27.2 27.2-27.2zm-118.3 54.4c-15 0-27.2-12.1-27.2-27.2s12.2-27.2 27.2-27.2 27.2 12.1 27.2 27.2-12.2 27.2-27.2 27.2zM563 319.4c0-69.6-69.6-126.2-147.9-126.2-83.2 0-148.4 56.6-148.4 126.2 0 69.9 65.2 126.2 148.4 126.2 17.3 0 34.6-2.4 51.9-7.3l48.5 26.6-13.3-43.4C537.7 399.4 563 362.7 563 319.4zm-196.1-34.9c-9.7 0-17.6-7.8-17.6-17.6s7.9-17.6 17.6-17.6 17.6 7.8 17.6 17.6-7.9 17.6-17.6 17.6zm96.9 0c-9.7 0-17.6-7.8-17.6-17.6s7.9-17.6 17.6-17.6 17.6 7.8 17.6 17.6-7.9 17.6-17.6 17.6z',
  qq: 'M21.395 15.035a40 40 0 0 0-.803-2.264l-1.079-2.695c.001-.032.014-.562.014-.836C19.526 4.632 17.351 0 12 0S4.474 4.632 4.474 9.241c0 .274.013.804.014.836l-1.08 2.695a39 39 0 0 0-.802 2.264c-1.021 3.283-.69 4.643-.438 4.673.54.065 2.103-2.472 2.103-2.472 0 1.469.756 3.387 2.394 4.771-.612.188-1.363.479-1.845.835-.434.32-.379.646-.301.778.343.578 5.883.369 7.482.189 1.6.18 7.14.389 7.483-.189.078-.132.132-.458-.301-.778-.483-.356-1.233-.646-1.846-.836 1.637-1.384 2.393-3.302 2.393-4.771 0 0 1.563 2.537 2.103 2.472.251-.03.581-1.39-.438-4.673',
  douyin: 'M448,209.91a210.06,210.06,0,0,1-122.77-39.25V349.38A162.55,162.55,0,1,1,185,188.31V278.2a74.62,74.62,0,1,0,52.23,71.18V0l88,0a121.18,121.18,0,0,0,1.86,22.17h0A122.18,122.18,0,0,0,381,102.39a121.43,121.43,0,0,0,67,20.14Z',
  github: 'M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.04c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.74.08-.74 1.2.09 1.83 1.23 1.83 1.23 1.07 1.83 2.8 1.3 3.48.99.11-.77.42-1.3.76-1.6-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.38 1.23-3.22-.12-.3-.53-1.52.12-3.18 0 0 1-.32 3.3 1.23A11.5 11.5 0 0 1 12 6.2c1.02 0 2.05.14 3.01.42 2.29-1.55 3.29-1.23 3.29-1.23.65 1.66.24 2.88.12 3.18.76.84 1.23 1.91 1.23 3.22 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.21.7.83.58A12 12 0 0 0 12 .5z',
}
const LABELS = { wechat: '微信', qq: 'QQ', douyin: '抖音', github: 'GitHub' }

const emit = defineEmits(['copied'])
const socials = ref([])

onMounted(async () => {
  try {
    /* 走设置单例：与 App.vue 共用同一次请求，避免首页重复拉 /api/settings */
    const s = await loadSettings()
    socials.value = Object.keys(ICONS)
      .filter(k => (s['social_' + k] || '').trim())
      .map(k => ({ key: k, value: s['social_' + k].trim() }))
  } catch { /* 设置拉取失败则不显示 */ }
})

const isLink = v => /^https?:\/\//i.test(v)

/* 非安全上下文（http、部分内嵌浏览器）没有 navigator.clipboard，
   直接调用会抛未处理的 Promise 拒绝；这里做可用性判断 + 选区复制兜底。 */
const copyText = async text => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch { /* 权限被拒时继续走兜底 */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;top:-1000px;left:0;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    ta.remove()
    return ok
  } catch { return false }
}

const openOrCopy = async item => {
  if (isLink(item.value)) { window.open(item.value, '_blank', 'noopener'); return }
  const ok = await copyText(item.value)
  emit(ok ? 'copied' : 'copyfailed', LABELS[item.key])
}
</script>

<template>
  <div class="socials" aria-label="社交链接">
    <a
      v-for="s in socials" :key="s.key"
      class="social" href="#"
      :aria-label="LABELS[s.key]"
      @click.prevent="openOrCopy(s)"
    >
      <svg :viewBox="s.key === 'wechat' ? '0 0 576 512' : s.key === 'douyin' ? '0 0 448 512' : '0 0 24 24'" aria-hidden="true"><path :d="ICONS[s.key]"/></svg>
      <span>{{ LABELS[s.key] }}</span>
    </a>
  </div>
</template>

<style scoped>
.socials { display: flex; justify-content: center; gap: clamp(14px, 2vw, 24px); }
.social {
  display: inline-flex; flex-direction: column; align-items: center; gap: 7px;
  font-size: 11.5px; color: var(--ink-3);
  transition: color var(--t-fast) var(--ease), transform var(--t-fast) var(--ease);
}
.social:hover { color: var(--ink); transform: translateY(-2px); }
.social svg { width: 21px; height: 21px; fill: currentColor; }
</style>
