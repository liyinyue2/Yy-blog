<script setup>
/** ProjectView — 项目详情（含开发日志） */
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const project = ref(null)
const logs = ref([])
const state = ref('loading')

onMounted(async () => {
  try {
    const res = await fetch('/api/public/projects')
    const list = Array.isArray(res) ? res : await res.json()
    project.value = (Array.isArray(list) ? list : list.projects || [])
      .find(p => p.slug === route.params.slug)
    if (!project.value) throw new Error()
    const lr = await fetch(`/api/public/projects/${project.value.id}/logs`).catch(() => null)
    if (lr?.ok) {
      const ld = await lr.json()
      logs.value = Array.isArray(ld) ? ld : (ld.logs || [])
    }
    state.value = 'ok'
    document.title = `${project.value.name} — Y's Blog`
  } catch { state.value = 'error' }
})
</script>

<template>
  <main class="page-main">
    <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    <p v-else-if="state === 'error'" class="list-empty">项目不存在。<router-link class="back" to="/projects">← 返回项目列表</router-link></p>
    <template v-else>
      <header class="page-head">
        <p class="section-kicker">Project · {{ project.status === 'building' ? '开发中' : project.status === 'maintained' ? '维护中' : project.status }}</p>
        <h1>{{ project.name }}</h1>
        <p class="page-desc">{{ project.summary }}</p>
        <div class="tech" v-if="project.tech_stack?.length">
          <span v-for="t in project.tech_stack" :key="t" class="chip">{{ t }}</span>
        </div>
      </header>
      <article class="post-body lg-panel" v-if="project.description" v-html="project.description"></article>
      <section class="logs" v-if="logs.length">
        <h2>开发日志</h2>
        <div v-for="log in logs" :key="log.id" class="article-card log-card">
          <span class="card-meta">{{ (log.created_at || '').replace('T', ' ').slice(0, 16) }}</span>
          <p>{{ log.content }}</p>
        </div>
      </section>
      <div class="post-footer">
        <router-link class="back" to="/projects">← 返回项目列表</router-link>
      </div>
    </template>
  </main>
</template>

<style scoped>
.tech { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.post-body { padding: 32px 36px; border-radius: var(--r-l); }
.logs { margin-top: 44px; }
.logs h2 { font-size: 22px; font-weight: 600; letter-spacing: -.02em; margin-bottom: 18px; }
.log-card { padding: 20px 26px; }
.log-card p { margin-top: 8px; -webkit-line-clamp: unset; }
.post-footer { margin-top: 40px; }
.back { color: var(--ink-2); font-size: 13.5px; }
.back:hover { color: var(--ink); }
</style>
