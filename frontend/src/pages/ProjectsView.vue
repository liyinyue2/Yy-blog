<script setup>
import { ref, onMounted } from 'vue'
import { PROJECT_STATUS, projectStatusLabel } from '../constants'
import { publicApi, asList } from '../api/client'
import { vSlideBall } from '../directives/slideBall'

const projects = ref([])
const state = ref('loading')
const statuses = [
  { value: 'all', label: '全部' },
  ...Object.entries(PROJECT_STATUS).map(([value, label]) => ({ value, label })),
]
const cur = ref('all')

const load = async () => {
  state.value = 'loading'
  const res = await publicApi('/api/public/projects')
  if (!res.ok) { state.value = 'error'; return }
  const list = asList(res.data)
  projects.value = cur.value === 'all' ? list : list.filter(p => (p.status || '') === cur.value)
  state.value = 'ok'
}
const pick = s => { cur.value = s; load() }
onMounted(load)
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Projects / 05</p>
      <h1>项目</h1>
      <p class="page-desc">正在构建与长期维护的作品：从构想到上线，开发日志持续更新。</p>
    </header>
    <div class="filters" v-slide-ball>
      <button
        v-for="s in statuses" :key="s.value"
        class="chip" :class="{ 'is-active': cur === s.value }"
        type="button" @click="pick(s.value)"
      >{{ s.label }}</button>
    </div>
    <div class="article-list">
      <router-link v-for="p in projects" :key="p.slug" class="article-card" :to="`/projects/${p.slug}`">
        <h3>{{ p.name || p.title }}</h3>
        <p>{{ p.summary || p.description || '' }}</p>
        <span class="card-meta">{{ projectStatusLabel(p.status) }}</span>
      </router-link>
      <p v-if="state === 'ok' && !projects.length" class="list-empty">还没有公开项目。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
      <p v-if="state === 'error'" class="list-empty">项目列表加载失败。<button type="button" class="chip" @click="load">重试</button></p>
    </div>
  </main>
</template>
