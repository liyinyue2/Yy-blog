<script setup>
/**
 * 工作台 —— 数字空间首页
 * 组件：网站状态 / 今日待办 / 番茄钟 / 内容动态 / 快捷启动 / 最近访问
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, asList } from '../api/client'
import { projectStatusLabel } from '../constants'
import PomodoroCard from '../components/PomodoroCard.vue'

const router = useRouter()

const stats = ref(null)
const todos = ref([])
const recentArticles = ref([])
const recentMessages = ref([])
const recentProjects = ref([])
const pomodoros = ref([])
const failed = ref([])
const loading = ref(true)

const load = async () => {
  const [s, td, arts, msgs, projs, po] = await Promise.all([
    api('/api/stats'),
    api('/api/workspace/todos?limit=8'),
    api('/api/admin/articles'),
    api('/api/admin/messages'),
    api('/api/admin/projects'),
    api('/api/space/pomodoro?limit=20'),
  ])
  const bad = []
  if (!s.ok) bad.push('站点统计')
  if (!td.ok) bad.push('待办')
  if (!po.ok) bad.push('番茄钟')
  failed.value = bad
  stats.value = s.ok ? s.data : null
  todos.value = td.ok ? asList(td.data) : []
  recentArticles.value = arts.ok ? asList(arts.data).slice(0, 4) : []
  recentMessages.value = msgs.ok ? asList(msgs.data).slice(0, 4) : []
  recentProjects.value = projs.ok ? asList(projs.data).slice(0, 3) : []
  pomodoros.value = po.ok ? asList(po.data) : []
  loading.value = false
}

const toggleTodo = async t => {
  await api('/api/workspace/todos/' + t.id, { method: 'PUT', body: JSON.stringify({ ...t, done: !t.done }) })
  load()
}

/* ---------- 番茄钟（组件复用，独立页在「效率工具」） ---------- */
const todayFocus = computed(() => {
  const d = new Date().toISOString().slice(0, 10)
  return pomodoros.value.filter(p => String(p.started_at || '').slice(0, 10) === d)
    .reduce((n, p) => n + (p.minutes || 0), 0)
})
const onPomo = () => load()

/* ---------- 快捷启动 / 最近访问 ---------- */
const QUICK = [
  { label: '写文章', to: '/space/site/write' },
  { label: '留言审核', to: '/space/site/messages' },
  { label: '知识库', to: '/space/notes' },
  { label: '云文件', to: '/space/files' },
  { label: '待办', to: '/space/todos' },
  { label: '站点设置', to: '/space/site/settings' },
]
const recent = ref(JSON.parse(localStorage.getItem('space-recent') || '[]'))
const go = to => router.push(to)

const onVisible = () => { if (!document.hidden) recent.value = JSON.parse(localStorage.getItem('space-recent') || '[]') }
onMounted(() => { load(); document.addEventListener('visibilitychange', onVisible) })
</script>

<template>
  <section class="dash">
    <p v-if="failed.length" class="dash-warn">数据未取到：{{ failed.join('、') }}（其余组件不受影响）</p>

    <div class="dash-grid">
      <!-- 网站状态 -->
      <div class="card widget">
        <h3>网站状态</h3>
        <div class="kv" v-if="stats">
          <div><b>{{ stats.articles }}</b><span>文章</span></div>
          <div><b>{{ stats.categories }}</b><span>分类</span></div>
          <div><b>{{ stats.messages }}</b><span>留言</span></div>
          <div><b>{{ stats.subscribers }}</b><span>订阅者</span></div>
          <div><b>{{ stats.views }}</b><span>总阅读</span></div>
        </div>
        <p v-else class="hint">正在加载…</p>
      </div>

      <!-- 番茄钟 -->
      <div class="card widget">
        <h3>番茄钟</h3>
        <PomodoroCard @completed="onPomo" />
        <p class="hint">今日专注 {{ todayFocus }} 分钟</p>
      </div>

      <!-- 今日待办 -->
      <div class="card widget">
        <h3>待办事项</h3>
        <ul class="todo-list">
          <li v-for="t in todos" :key="t.id">
            <button type="button" class="tick" :class="{ on: t.done }" @click="toggleTodo(t)"
                    :aria-label="t.done ? '标记未完成' : '标记完成'">✓</button>
            <span :class="{ done: t.done }">{{ t.content }}</span>
            <em v-if="t.priority" class="g-tag danger">{{ t.priority === 2 ? '紧急' : '重要' }}</em>
            <em v-if="t.due" class="g-tag">{{ t.due }}</em>
          </li>
          <li v-if="!todos.length && !loading" class="hint">暂无待办，去「效率工具 → 待办事项」添加。</li>
        </ul>
      </div>

      <!-- 快捷启动 -->
      <div class="card widget">
        <h3>快捷启动</h3>
        <div class="quick">
          <button v-for="q in QUICK" :key="q.to" type="button" @click="go(q.to)">{{ q.label }}</button>
        </div>
        <h3 class="mt">最近访问</h3>
        <ul class="recent">
          <li v-for="(r, i) in recent.slice(0, 6)" :key="i">
            <button type="button" @click="go(r.to)">{{ r.label }}</button><span>{{ r.at }}</span>
          </li>
          <li v-if="!recent.length" class="hint">还没有访问记录。</li>
        </ul>
      </div>

      <!-- 内容动态 -->
      <div class="card widget span2">
        <h3>内容动态</h3>
        <div class="feed">
          <div>
            <h4>最近更新的文章</h4>
            <ul>
              <li v-for="a in recentArticles" :key="a.slug">{{ a.title }}<span>{{ a.date }}</span></li>
              <li v-if="!recentArticles.length" class="hint">还没有文章。</li>
            </ul>
          </div>
          <div>
            <h4>最近留言</h4>
            <ul>
              <li v-for="m in recentMessages" :key="m.id">{{ m.name }}：{{ (m.content || '').slice(0, 24) }}<span>{{ (m.created_at || '').slice(5, 10) }}</span></li>
              <li v-if="!recentMessages.length" class="hint">还没有留言。</li>
            </ul>
          </div>
          <div>
            <h4>项目</h4>
            <ul>
              <li v-for="p in recentProjects" :key="p.id">{{ p.name }} · {{ p.progress }}%<span>{{ projectStatusLabel(p.status) }}</span></li>
              <li v-if="!recentProjects.length" class="hint">还没有项目。</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
