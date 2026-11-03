<script setup>
/** PostView — 文章详情（fetch /api/articles/{slug}，正文服务端已净化） */
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const post = ref(null)
const state = ref('loading')

onMounted(async () => {
  try {
    const res = await fetch(`/api/articles/${route.params.slug}`)
    if (!res.ok) throw new Error()
    post.value = await res.json()
    state.value = 'ok'
    document.title = `${post.value.title} — Y's Blog`
  } catch { state.value = 'error' }
})
</script>

<template>
  <main class="page-main">
    <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    <p v-else-if="state === 'error'" class="list-empty">文章不存在或已被移除。<router-link class="back" to="/articles">← 返回文章列表</router-link></p>
    <template v-else>
      <header class="page-head post-head">
        <p class="section-kicker">{{ post.category_name || '文章' }} {{ post.date ? '· ' + post.date : '' }}</p>
        <h1>{{ post.title }}</h1>
        <p class="page-desc">{{ post.summary }}</p>
      </header>
      <article class="post-body lg-panel" v-html="post.content"></article>
      <div class="post-footer">
        <router-link class="back" to="/articles">← 返回文章列表</router-link>
        <span class="views">{{ post.views }} 次阅读</span>
      </div>
    </template>
  </main>
</template>

<style scoped>
.post-head { margin-bottom: 40px; }
.post-body {
  padding: 36px 40px; border-radius: var(--r-l);
  background: var(--glass-bg);
  -webkit-backdrop-filter: var(--glass-blur-thin); backdrop-filter: var(--glass-blur-thin);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.28),
    inset 1.5px 2px 2px -.5px rgba(255,255,255,.55),
    inset -1px -1.5px 2px -.5px rgba(255,255,255,.30),
    0 16px 44px rgba(0,0,0,.08);
}
.post-body :deep(h2) { font-size: 24px; font-weight: 600; letter-spacing: -.02em; margin: 34px 0 16px; color: var(--ink); }
.post-body :deep(h2:first-child) { margin-top: 0; }
.post-body :deep(p) { margin: 0 0 18px; font-size: 15.5px; line-height: 2; color: var(--ink-2); }
.post-body :deep(code) { padding: 2px 7px; border-radius: 6px; background: rgba(0,0,0,.06); font-size: 13px; }
.post-body :deep(pre) { padding: 18px 20px; border-radius: var(--r-m); background: rgba(0,0,0,.75); overflow-x: auto; }
.post-body :deep(pre code) { background: none; color: #eee; }
.post-body :deep(img) { max-width: 100%; border-radius: var(--r-m); }
.post-body :deep(blockquote) {
  margin: 20px 0; padding: 14px 20px; border-left: 3px solid var(--accent);
  background: rgba(10,132,255,.06); border-radius: 0 var(--r-s) var(--r-s) 0;
  color: var(--ink-2);
}
.post-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 36px; font-size: 13px; color: var(--ink-3);
}
.back { color: var(--ink-2); transition: color var(--t-fast) var(--ease); }
.back:hover { color: var(--ink); }
@media (max-width: 760px) { .post-body { padding: 26px 22px; } }
</style>
