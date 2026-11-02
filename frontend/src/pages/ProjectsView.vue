<script setup>
import { ref, onMounted } from 'vue'

const projects = ref([])
const state = ref('loading')
const statuses = [
  { value: 'all', label: '全部' },
  { value: 'building', label: '开发中' },
  { value: 'maintained', label: '维护中' },
  { value: 'idea', label: '构想中' },
  { value: 'archived', label: '已归档' },
]
const cur = ref('all')

const load = async () => {
  state.value = 'loading'
  try {
    const res = await fetch('/api/public/projects')
    const data = await res.json()
    const list = data.projects || data.items || []
    projects.value = cur.value === 'all' ? list : list.filter(p => (p.status || '') === cur.value)
    state.value = 'ok'
  } catch { state.value = 'error' }
}
const pick = s => { cur.value = s; load() }
onMounted(load)

const STATUS_LABEL = { building: '开发中', maintained: '维护中', idea: '构想中', archived: '已归档' }
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Projects / 05</p>
      <h1>项目</h1>
      <p class="page-desc">正在构建与长期维护的作品：从构想到上线，开发日志持续更新。</p>
    </header>
    <div class="filters">
      <button
        v-for="s in statuses" :key="s.value"
        class="chip" :class="{ 'is-active': cur === s.value }"
        type="button" @click="pick(s.value)"
      >{{ s.label }}</button>
    </div>
    <div class="article-list">
      <article v-for="p in projects" :key="p.slug" class="article-card">
        <h3>{{ p.name || p.title }}</h3>
        <p>{{ p.summary || p.description || '' }}</p>
        <span class="card-meta">{{ STATUS_LABEL[p.status] || p.status || '' }}</span>
      </article>
      <p v-if="state === 'ok' && !projects.length" class="list-empty">还没有公开项目。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    </div>
  </main>
</template>
