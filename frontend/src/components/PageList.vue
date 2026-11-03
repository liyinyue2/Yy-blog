<script setup>
/** PageList — 文章/笔记列表（对接 /api/articles，1:1 复刻原列表卡片） */
import { ref, onMounted } from 'vue'
import { vSlideBall } from '../directives/slideBall'

const props = defineProps({ kind: { type: String, default: 'all' } })
const articles = ref([])
const state = ref('loading')
const kinds = [
  { value: 'all', label: '全部' },
  { value: 'article', label: '文章' },
  { value: 'note', label: '技术笔记' },
]
const curKind = ref('all')
const keyword = ref('')

const load = async () => {
  state.value = 'loading'
  try {
    const params = new URLSearchParams()
    if (curKind.value !== 'all') params.set('kind', curKind.value)
    const res = await fetch(`/api/articles?${params}`)
    const data = await res.json()
    const list = Array.isArray(data) ? data : (data.articles || data.items || [])
    const kw = keyword.value.trim().toLowerCase()
    articles.value = kw
      ? list.filter(a => `${a.title} ${a.summary || ''}`.toLowerCase().includes(kw))
      : list
    state.value = 'ok'
  } catch { state.value = 'error' }
}

const pick = k => { curKind.value = k; load() }
onMounted(load)
</script>

<template>
  <div>
    <div class="filters" v-slide-ball>
      <button
        v-for="k in kinds" :key="k.value"
        class="chip" :class="{ 'is-active': curKind === k.value }"
        type="button" @click="pick(k.value)"
      >{{ k.label }}</button>
    </div>
    <div class="search-row">
      <input v-model="keyword" type="search" placeholder="搜索文章标题或摘要…" @input="load" />
    </div>
    <div class="article-list">
      <router-link v-for="a in articles" :key="a.slug" class="article-card" :to="`/post/${a.slug}`">
        <h3>{{ a.title }}</h3>
        <p>{{ a.summary || '点击阅读全文…' }}</p>
        <span class="card-meta">
          <span v-if="a.kind === 'note'" class="g-tag accent kind-badge">技术笔记</span>
          {{ a.category_name || '' }}<i v-if="a.category_name && a.date">·</i>{{ a.date || '' }}
        </span>
      </router-link>
      <p v-if="state === 'ok' && !articles.length" class="list-empty">还没有内容。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
      <p v-if="state === 'error'" class="list-empty">加载失败，请稍后再试。</p>
    </div>
  </div>
</template>
