<script setup>
/** AboutView — 1:1 复刻原版关于页（设置驱动内容 + 找到我 + 订阅） */
import { ref, onMounted } from 'vue'
import SocialLinks from '../components/SocialLinks.vue'

const intro = ref('')
const content = ref('')
const fallback = `<p>我是一名在代码与设计之间来回探索的人。这个博客没有标准答案，只有持续记录的过程：做过什么、为什么这样做，以及下一次会如何做得更好。</p><p>我相信好的作品来自持续观察，也来自愿意把模糊的直觉写清楚。感谢你来到这里，如果你也喜欢把好奇心变成作品，欢迎通过订阅保持联系。</p>`
const email = ref('')
const subNote = ref('')
const subbing = ref(false)
const copied = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/settings')
    const s = await res.json()
    intro.value = s.about_intro || ''
    content.value = s.about_content || ''
  } catch { /* 默认文案兜底 */ }
})

const onCopied = label => {
  copied.value = `${label} 已复制到剪贴板`
  setTimeout(() => { copied.value = '' }, 2200)
}
const onCopyFailed = label => {
  copied.value = `${label} 复制失败，请手动复制`
  setTimeout(() => { copied.value = '' }, 2600)
}

const subscribe = async () => {
  const v = email.value.trim()
  if (!v || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { subNote.value = '请输入有效的邮箱地址。'; return }
  subbing.value = true; subNote.value = '正在提交…'
  try {
    const res = await fetch('/api/subscribe', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: v }),
    })
    subNote.value = res.ok ? '订阅成功，新文章发布时会第一时间通知你！' : '订阅失败，请稍后再试。'
    if (res.ok) email.value = ''
  } catch { subNote.value = '网络异常，请稍后再试。' }
  subbing.value = false
}
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">About / 05</p>
      <h1>关于</h1>
      <p class="page-desc">{{ intro || '关于我、做过的事，以及联系我的方式。' }}</p>
    </header>
    <article class="article-card about-card" v-html="content || fallback"></article>

    <section class="about-social-wrap">
      <h2>找到我</h2>
      <p class="about-social-hint">点击即可复制，或跳转到对应主页。</p>
      <div class="about-social-panel">
        <SocialLinks @copied="onCopied" @copyfailed="onCopyFailed" />
      </div>
      <transition name="toast-in">
        <div v-if="copied" class="copy-toast">{{ copied }}</div>
      </transition>
    </section>

    <section class="subscribe-wrap">
      <h2>订阅更新</h2>
      <p class="about-social-hint">新文章发布时收到邮件通知，随时可退订。</p>
      <form class="sub-form" @submit.prevent="subscribe">
        <input v-model="email" type="email" placeholder="你的邮箱地址" />
        <button type="submit" :disabled="subbing">{{ subbing ? '提交中…' : '订阅' }}</button>
      </form>
      <p v-if="subNote" class="form-note">{{ subNote }}</p>
    </section>
  </main>
</template>

<style scoped>
.about-card { padding: 32px 36px; margin-bottom: 44px; }
.about-card :deep(p) { margin: 0 0 16px; font-size: 15px; line-height: 2; color: var(--ink-2); }
.about-card :deep(p:last-child) { margin-bottom: 0; }
.about-social-wrap, .subscribe-wrap { margin-top: 44px; }
.about-social-wrap h2, .subscribe-wrap h2 { font-size: 22px; font-weight: 600; letter-spacing: -.02em; margin-bottom: 8px; }
.about-social-hint { font-size: 13px; color: var(--ink-3); margin-bottom: 20px; }
.about-social-panel {
  display: flex; justify-content: center; padding: 26px 20px; border-radius: var(--r-l);
  background: var(--glass-bg);
  -webkit-backdrop-filter: var(--glass-blur-thin); backdrop-filter: var(--glass-blur-thin);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.28), inset 1.5px 2px 2px -.5px rgba(255,255,255,.55),
              0 0 0 1px rgba(60,60,67,.06), 0 16px 44px rgba(0,0,0,.08);
}
.copy-toast {
  margin: 14px auto 0; width: fit-content; padding: 10px 18px; border-radius: var(--r-pill);
  background: var(--glass-bg-dark); color: #fff; font-size: 12.5px;
}
.toast-in-enter-active, .toast-in-leave-active { transition: opacity var(--t-base) var(--ease), transform var(--t-base) var(--ease); }
.toast-in-enter-from, .toast-in-leave-to { opacity: 0; transform: translateY(8px); }
.sub-form { display: flex; gap: 12px; max-width: 520px; }
.sub-form input {
  flex: 1; padding: 14px 20px; border-radius: var(--r-pill); border: 1px solid var(--hairline);
  outline: none; background: var(--glass-bg); color: var(--ink); font: inherit; font-size: 14px;
  -webkit-backdrop-filter: var(--glass-blur-thin); backdrop-filter: var(--glass-blur-thin);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 2px 10px rgba(0,0,0,.05);
}
.sub-form input:focus { border-color: var(--accent); box-shadow: var(--focus-ring); }
.sub-form button {
  padding: 13px 30px; font-size: 13.5px; font-weight: 500;
  color: var(--ink); background: var(--gbtn-bg-hover);
}
.sub-form button:hover:not(:disabled) { background: var(--gbtn-bg-on); transform: translateY(-2px); box-shadow: var(--gbtn-rim-on), var(--gbtn-shadow-on); }
.form-note { margin-top: 12px; font-size: 12.5px; color: var(--ink-3); }
</style>
