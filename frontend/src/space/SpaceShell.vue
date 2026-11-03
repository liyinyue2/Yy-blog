<script setup>
/**
 * SpaceShell —— 个人数字空间外壳
 * 两栏导航：第 1 列分区图标（6 项），第 2 列当前分区的子项（≤12 项），避免一屏塞 40 多个链接。
 * 登录门、聚合搜索、确认模态由本壳统一持有。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, login, logout, isAuthed } from '../api/client'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import { vSlideBall } from '../directives/slideBall'

const route = useRoute()
const router = useRouter()

const ICONS = {
  dashboard: 'M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z',
  site: 'M3 4h18v13H3zM3 9h18M7 4v5M10.5 21h3M12 17v4',
  personal: 'M4 20V9l8-5 8 5v11zM9 20v-6h6v6',
  tools: 'M14.7 6.3a4 4 0 0 1 5 5L21 12l-9 9-2-2 1-1.5-4-4 1.5-1L6 9l2-2zM4 20l3-3',
  ai: 'M12 3v3M12 18v3M3 12h3M18 12h3M7 7l2 2M15 15l2 2M17 7l-2 2M9 15l-2 2M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z',
  system: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 13.5H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.6 7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 2.7-1.1V3a2 2 0 1 1 4 0v.1A1.6 1.6 0 0 0 16.5 5l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1.5z',
}

/* 分区 → 子项（子项即面板，不再嵌套三级标题） */
const SECTIONS = [
  { key: 'dashboard', label: '工作台', base: '/space/dashboard', items: [{ label: '概览面板', to: '/space/dashboard' }] },
  {
    key: 'site', label: '网站管理', base: '/space/site/workspace',
    items: [
      { label: '网站概览', to: '/space/site/workspace' },
      { label: '文章', to: '/space/site/articles' },
      { label: '分类', to: '/space/site/categories' },
      { label: '标签', to: '/space/site/tags' },
      { label: '留言', to: '/space/site/messages' },
      { label: '订阅者', to: '/space/site/subscribers' },
      { label: '音乐', to: '/space/site/music' },
      { label: '项目', to: '/space/site/projects' },
      { label: '云盘', to: '/space/site/cloud' },
      { label: '站点设置', to: '/space/site/settings' },
      { label: '审计日志', to: '/space/site/audit' },
      { label: '账号与安全', to: '/space/site/admins' },
    ],
  },
  {
    key: 'personal', label: '个人空间', base: '/space/notes',
    items: [
      { label: '知识库', to: '/space/notes' },
      { label: '云文件', to: '/space/files' },
      { label: '项目中心', to: '/space/projects-manage' },
      { label: '学习记录', to: '/space/learning' },
    ],
  },
  {
    key: 'tools', label: '效率工具', base: '/space/todos',
    items: [
      { label: '待办事项', to: '/space/todos' },
      { label: '番茄钟', to: '/space/pomodoro' },
      { label: '书签', to: '/space/bookmarks' },
      { label: '日程', to: '/space/calendar' },
    ],
  },
  {
    key: 'ai', label: 'AI 中心', base: '/space/ai/chat',
    items: [
      { label: 'AI 对话', to: '/space/ai/chat' },
      { label: '智能体', to: '/space/ai/agents' },
      { label: '工作流', to: '/space/ai/flows' },
    ],
  },
  {
    key: 'system', label: '系统设置', base: '/space/system',
    items: [
      { label: '系统状态', to: '/space/system' },
      { label: '个人资料', to: '/space/profile' },
      { label: '界面设置', to: '/space/appearance' },
    ],
  },
]

const sectionOf = path => {
  if (path.startsWith('/space/site')) return 'site'
  if (path.startsWith('/space/notes') || path.startsWith('/space/files')
      || path.startsWith('/space/projects-manage') || path.startsWith('/space/learning')) return 'personal'
  if (path.startsWith('/space/todos') || path.startsWith('/space/pomodoro')
      || path.startsWith('/space/bookmarks') || path.startsWith('/space/calendar')) return 'tools'
  if (path.startsWith('/space/ai')) return 'ai'
  if (path.startsWith('/space/system') || path.startsWith('/space/profile')
      || path.startsWith('/space/appearance')) return 'system'
  return 'dashboard'
}

const authed = ref(isAuthed())
const username = ref('admin')
const password = ref('')
const gateErr = ref('')
const gating = ref(false)
const active = ref(sectionOf(route.path))

const current = computed(() => SECTIONS.find(s => s.key === active.value) || SECTIONS[0])
const isOn = to => {
  const url = new URL(to, 'http://x')
  return url.pathname === route.path && url.searchParams.toString() === new URLSearchParams(route.query).toString()
}
const go = to => { if (to !== route.path + route.search) router.push(to) }
const pickSection = s => { active.value = s.key; go(s.base) }

const doLogin = async () => {
  gating.value = true; gateErr.value = ''
  const r = await login(username.value.trim(), password.value)
  if (r.ok) { authed.value = true; startClock() }
  else gateErr.value = r.error || '登录失败'
  gating.value = false
}
const doLogout = () => { logout(); authed.value = false }
const onUnauthorized = () => { authed.value = false }

/* 顶栏时钟 */
const now = ref(new Date())
let timer = null
const startClock = () => { clearInterval(timer); timer = setInterval(() => { now.value = new Date() }, 1000) }
const clock = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))
const today = computed(() => now.value.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }))

/* 聚合搜索 */
const query = ref('')
const groups = ref([])
const searching = ref(false)
const searchOpen = ref(false)
let searchTimer = null
const onQuery = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    const q = query.value.trim()
    if (!q) { groups.value = []; searchOpen.value = false; return }
    searching.value = true
    const r = await api('/api/space/search?q=' + encodeURIComponent(q))
    groups.value = r.ok ? (r.data.groups || []) : []
    searching.value = false
    searchOpen.value = true
  }, 260)
}
/* 搜索接口给的是 v2 静态地址，映射到 SPA 路由 */
const openHit = hit => {
  searchOpen.value = false
  if (!hit.url) return
  const post = hit.url.match(/^\/post-(.+)\.html$/)
  if (post) return go('/post/' + post[1])
  if (hit.url.startsWith('/projects')) return // 公开项目页已下线，跳到 404 不如停在这里
  go(hit.url)
}

onMounted(() => { if (authed.value) startClock() })
onBeforeUnmount(() => { clearInterval(timer); clearTimeout(searchTimer) })
</script>

<template>
  <!-- 登录门 -->
  <form v-if="!authed" class="space-gate" @submit.prevent="doLogin">
    <h1>个人数字空间</h1>
    <p class="gate-sub">管理网站，也处理学习、项目与日常事务。</p>
    <input v-model="username" type="text" placeholder="用户名" autocomplete="username" />
    <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" />
    <button type="submit" :disabled="gating">{{ gating ? '登录中…' : '进入空间' }}</button>
    <p class="gate-error">{{ gateErr }}</p>
  </form>

  <div v-else class="space-shell">
    <!-- 第 1 列：分区 -->
    <nav class="space-icons" aria-label="空间分区" v-slide-ball="{ active: '.on', radius: '14px' }">
      <div class="icon-brand" title="数字空间">Y</div>
      <button v-for="s in SECTIONS" :key="s.key" type="button" class="icon-btn"
              :class="{ on: active === s.key }" :title="s.label" :aria-label="s.label"
              :aria-current="active === s.key ? 'page' : undefined" @click="pickSection(s)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS[s.key]"/></svg>
        <span>{{ s.label }}</span>
      </button>
      <div class="icon-foot">
        <a href="/" target="_blank" rel="noopener" title="查看公开站点">↗</a>
        <button type="button" title="退出登录" aria-label="退出登录" @click="doLogout">⏻</button>
      </div>
    </nav>

    <!-- 第 2 列：当前分区子项 -->
    <aside class="space-rail">
      <p class="rail-title">{{ current.label }}</p>
      <div class="rail-list" v-slide-ball="{ radius: 'var(--r-s)' }">
        <button v-for="it in current.items" :key="it.to" type="button" class="rail-item"
                :class="{ 'is-active': isOn(it.to) }" @click="go(it.to)">{{ it.label }}</button>
      </div>
    </aside>

    <div class="space-main">
      <header class="space-top">
        <div class="top-clock"><b>{{ clock }}</b><span>{{ today }}</span></div>
        <div class="top-search">
          <input v-model="query" type="search" placeholder="搜索笔记、文章、项目、文件、待办、书签…"
                 @input="onQuery" @focus="searchOpen = groups.length > 0" />
          <div v-if="searchOpen" class="search-pop lg-panel">
            <p v-if="searching" class="pop-hint">正在搜索…</p>
            <template v-else-if="groups.length">
              <div v-for="g in groups" :key="g.type" class="pop-group">
                <p class="pop-title">{{ g.label || g.type }}</p>
                <button v-for="(it, i) in g.items" :key="i" type="button" class="pop-item"
                        @click="openHit(it)">{{ it.title || it.name || '(无标题)' }}</button>
              </div>
            </template>
            <p v-else class="pop-hint">没有匹配结果。</p>
          </div>
        </div>
      </header>

      <main class="space-body">
        <router-view v-slot="{ Component }">
          <component :is="Component" @unauthorized="onUnauthorized" />
        </router-view>
      </main>
    </div>

    <ConfirmDialog />
  </div>
</template>
