<script setup>
/** 网站概览 —— 关键数字 + 待处理事项 + 最近动作 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, asList } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'

const router = useRouter()
const stats = ref(null)
const recentMsgs = ref([])
const recentArts = ref([])
const audit = ref([])
const state = ref('loading')

const load = async () => {
  const [s, m, a, au] = await Promise.all([
    api('/api/stats'), api('/api/admin/messages?status=pending'),
    api('/api/admin/articles'), api('/api/admin/audit?limit=8'),
  ])
  if (!s.ok) { state.value = 'error'; return }
  stats.value = s.data
  recentMsgs.value = asList(m.data).slice(0, 5)
  recentArts.value = asList(a.data).slice(0, 5)
  audit.value = au.ok ? (au.data.items || []) : []
  state.value = 'ok'
}

/* 同类动作折叠成一条（否则最近动作会被 login-ok 之类刷屏） */
const recentActions = computed(() => {
  const map = new Map()
  for (const x of audit.value) {
    const hit = map.get(x.action)
    if (hit) { hit.n += 1; continue }
    map.set(x.action, { action: x.action, at: (x.created_at || '').slice(5, 16).replace('T', ' '), n: 1 })
  }
  return [...map.values()].slice(0, 8)
})

const cards = computed(() => stats.value ? [
  { k: '文章', v: stats.value.articles, to: '/space/site/articles' },
  { k: '分类', v: stats.value.categories, to: '/space/site/categories' },
  { k: '标签', v: stats.value.tags, to: '/space/site/tags' },
  { k: '待审留言', v: stats.value.pending_messages, to: '/space/site/messages', warn: stats.value.pending_messages > 0 },
  { k: '公开留言', v: stats.value.messages, to: '/space/site/messages' },
  { k: '订阅者', v: stats.value.subscribers, to: '/space/site/subscribers' },
  { k: '总阅读', v: stats.value.views },
] : [])

onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>网站概览</h2><p class="hint">数字与待处理事项</p></div>
      <button type="button" class="g-btn" @click="load">刷新</button>
    </header>

    <DataState :state="state" @retry="load">
      <div class="ov-cards">
        <button v-for="c in cards" :key="c.k" type="button" class="ov-card"
                :class="{ warn: c.warn, static: !c.to }" @click="c.to && router.push(c.to)">
          <b>{{ c.v }}</b><span>{{ c.k }}</span>
          <em v-if="c.warn" class="ov-hint">去处理 →</em>
        </button>
      </div>

      <div class="ov-cols">
        <div class="card">
          <h3>待审核留言</h3>
          <ul class="ov-list">
            <li v-for="m in recentMsgs" :key="m.id">
              <b>{{ m.name }}</b><span>{{ (m.content || '').slice(0, 34) }}</span>
            </li>
            <li v-if="!recentMsgs.length" class="hint">队列是空的，都处理完了。</li>
          </ul>
          <router-link v-if="recentMsgs.length" class="chip" to="/space/site/messages">全部待审 →</router-link>
        </div>
        <div class="card">
          <h3>最近更新的文章</h3>
          <ul class="ov-list">
            <li v-for="a in recentArts" :key="a.slug"><b>{{ a.title }}</b><span>{{ a.date }}</span></li>
            <li v-if="!recentArts.length" class="hint">还没有文章。</li>
          </ul>
          <router-link class="chip" to="/space/site/write">写一篇 →</router-link>
        </div>
        <div class="card">
          <h3>最近动作</h3>
          <ul class="ov-list">
            <li v-for="x in recentActions" :key="x.action"><b>{{ x.action }}<em v-if="x.n > 1"> ×{{ x.n }}</em></b><span>{{ x.at }}</span></li>
            <li v-if="!recentActions.length" class="hint">暂无记录。</li>
          </ul>
          <router-link class="chip" to="/space/site/audit">审计日志 →</router-link>
        </div>
      </div>
    </DataState>
  </section>
</template>
