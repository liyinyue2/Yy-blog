<script setup>
/**
 * LibraryView —— 公开资源库
 * 数据来自 GET /api/public/resources（服务端 data/resources.json，改文件即生效）。
 * 支持按分类筛选 + 关键词搜索；卡片为外链，新窗口打开。
 */
import { computed, onMounted, ref } from 'vue'
import { publicApi, asList, errOf } from '../api/client'
import DataState from '../components/ui/DataState.vue'
import { vSlideBall } from '../directives/slideBall'

const items = ref([])
const state = ref('loading')
const error = ref('')
const kind = ref('')
const q = ref('')

const kinds = computed(() => [...new Set(items.value.map(i => i.kind).filter(Boolean))])
const shown = computed(() => {
  const s = q.value.trim().toLowerCase()
  return items.value.filter(i =>
    (!kind.value || i.kind === kind.value) &&
    (!s || `${i.title} ${i.note || ''} ${i.url}`.toLowerCase().includes(s))
  )
})
const host = url => { try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' } }

async function load() {
  state.value = 'loading'
  const r = await publicApi('/api/public/resources')
  if (!r.ok) { state.value = 'error'; error.value = errOf(r); return }
  items.value = asList(r.data)
  state.value = items.value.length ? 'ok' : 'empty'
}
onMounted(load)
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Library / 02</p>
      <h1>资源库</h1>
      <p class="page-desc">常看的文档、上手的工具与设计参考，集中放在这里。</p>
    </header>

    <div class="lib-bar">
      <div class="filters" v-slide-ball>
        <button type="button" class="chip" :class="{ 'is-active': kind === '' }" @click="kind = ''">全部</button>
        <button v-for="k in kinds" :key="k" type="button" class="chip"
                :class="{ 'is-active': kind === k }" @click="kind = k">{{ k }}</button>
      </div>
      <div class="search-row lib-search">
        <input v-model="q" type="search" placeholder="搜索标题、说明或网址…" aria-label="搜索资源" />
      </div>
    </div>

    <DataState :state="state" empty-text="资源库还没有内容。" @retry="load">
      <p v-if="!shown.length" class="hint lib-none">没有匹配的资源，换个关键词或分类试试。</p>
      <div v-else class="lib-grid">
        <a v-for="i in shown" :key="i.url" class="lib-card" :href="i.url" target="_blank" rel="noopener noreferrer">
          <h3>{{ i.title }}<span class="lib-out" aria-hidden="true">↗</span></h3>
          <p class="lib-note">{{ i.note }}</p>
          <p class="lib-meta">
            <span v-if="i.kind" class="g-tag">{{ i.kind }}</span>
            <span class="lib-host">{{ host(i.url) }}</span>
          </p>
        </a>
      </div>
    </DataState>
  </main>
</template>

<style scoped>
.lib-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }
.lib-search { flex: 1 1 260px; max-width: 380px; margin: 0; }
.lib-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr)); gap: 16px; }
.lib-card {
  display: flex; flex-direction: column; gap: 8px;
  padding: 20px 22px; border-radius: var(--r-l);
  background: var(--gbtn-bg);
  -webkit-backdrop-filter: var(--gbtn-blur); backdrop-filter: var(--gbtn-blur);
  box-shadow: var(--gbtn-rim), var(--gbtn-shadow);
  transition: transform var(--t-base) var(--ease), box-shadow var(--t-base) var(--ease), background var(--t-base) var(--ease);
}
.lib-card:hover {
  transform: translateY(-3px); background: var(--gbtn-bg-hover);
  box-shadow: var(--gbtn-rim-on), var(--gbtn-shadow-on);
}
.lib-card h3 {
  display: flex; align-items: baseline; gap: 6px;
  font-size: 15.5px; font-weight: 600; letter-spacing: -.01em; color: var(--ink);
}
.lib-out { font-size: 12px; color: var(--ink-3); opacity: 0; transition: opacity var(--t-fast) var(--ease); }
.lib-card:hover .lib-out { opacity: 1; }
.lib-note { flex: 1; font-size: 13px; line-height: 1.65; color: var(--ink-2); }
.lib-meta { display: flex; align-items: center; gap: 10px; margin-top: 2px; }
.lib-host { font-size: 11.5px; color: var(--ink-3); letter-spacing: .01em; }
.lib-none { padding: 40px 0; text-align: center; }
</style>
