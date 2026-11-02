<script setup>
/**
 * AdminView — 后台管理（1:1 复刻原版 12 面板）
 * 路由 /yy-AviuuP3r（保持隐匿路径），hash 定位当前面板。
 * 认证：JWT 双令牌（api.js 自动刷新）。
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, login, isAuthed, clearTokens } from '../admin/api'

const route = useRoute()
const router = useRouter()

/* hash 变化实时切面板 */
const onHash = () => {
  const h = window.location.hash.slice(1)
  if (PANELS.includes(h)) panel.value = h
}

/* ---------- 登录 ---------- */
const authed = ref(isAuthed())
const username = ref('admin')
const password = ref('')
const gateErr = ref('')
const gating = ref(false)
const doLogin = async () => {
  gating.value = true; gateErr.value = ''
  const r = await login(username.value.trim(), password.value)
  if (r.ok) { authed.value = true; loadAll() }
  else gateErr.value = r.error
  gating.value = false
}
const logout = () => { clearTokens(); authed.value = false }

/* ---------- 面板路由（hash） ---------- */
const PANELS = ['workspace', 'cloud', 'music', 'articles', 'projects', 'categories', 'tags',
  'messages', 'subscribers', 'settings', 'audit', 'admins']
const LABELS = { workspace: '概览', cloud: '云盘', music: '音乐库', articles: '文章', projects: '项目',
  categories: '分类', tags: '标签', messages: '留言', subscribers: '订阅者', settings: '站点设置',
  audit: '审计日志', admins: '管理员' }
const panel = ref(PANELS.includes(route.hash.slice(1)) ? route.hash.slice(1) : 'workspace')
const showPanel = name => { panel.value = name; history.replaceState(null, '', '#' + name) }

/* ---------- 数据 ---------- */
const stats = ref(null)
const articles = ref([])
const categories = ref([])
const tags = ref([])
const messages = ref([])
const subscribers = ref([])
const settings = ref({})
const projects = ref([])
const cloudFiles = ref([])
const tracks = ref([])
const workspaceItems = ref([])
const auditRows = ref([])
const auditQuery = ref('')
const notes = ref({})

const err = (d, fb) => d?.error || d?.detail || fb

const loadAll = async () => {
  const [s, arts, cats, msgs, subs, sets, tgs, projs] = await Promise.all([
    api('/api/stats'), api('/api/admin/articles'), api('/api/categories'),
    api('/api/admin/messages'), api('/api/admin/subscribers'), api('/api/settings'),
    api('/api/tags'), api('/api/admin/projects'),
  ])
  if (!s.ok || !arts.ok) { logout(); return }
  stats.value = s.data
  articles.value = arts.data || []
  categories.value = cats.data || []
  messages.value = msgs.data || []
  subscribers.value = subs.data || []
  settings.value = sets.data || {}
  tags.value = tgs.data || []
  projects.value = projs.data || []
  loadCloud(); loadMusic(); loadWorkspace()
}

/* 文章删除 */
const delArticle = async slug => {
  if (!confirm(`确定删除文章「${slug}」？不可恢复。`)) return
  await api('/api/admin/articles/' + slug, { method: 'DELETE' })
  loadAll()
}

/* 分类 */
const catForm = ref({ name: '', slug: '', description: '' })
const catEditing = ref('')
const catNote = ref('')
const saveCat = async () => {
  const f = catForm.value
  if (!f.name.trim() || !f.slug.trim()) { catNote.value = '名称与 slug 必填。'; return }
  const r = catEditing.value
    ? await api('/api/admin/categories/' + catEditing.value, { method: 'PUT', body: JSON.stringify(f) })
    : await api('/api/admin/categories', { method: 'POST', body: JSON.stringify(f) })
  catNote.value = r.ok ? '已保存。' : err(r.data, '保存失败')
  if (r.ok) { catForm.value = { name: '', slug: '', description: '' }; catEditing.value = ''; loadAll() }
}
const editCat = c => { catEditing.value = c.slug; catForm.value = { name: c.name, slug: c.slug, description: c.description || '' } }
const delCat = async c => {
  if (!confirm(`确定删除分类「${c.name}」？`)) return
  await api('/api/admin/categories/' + c.slug, { method: 'DELETE' })
  loadAll()
}

/* 标签 */
const tagName = ref('')
const tagNote = ref('')
const addTag = async () => {
  if (!tagName.value.trim()) { tagNote.value = '请输入标签名。'; return }
  const r = await api('/api/admin/tags', { method: 'POST', body: JSON.stringify({ name: tagName.value.trim() }) })
  tagNote.value = r.ok ? '已创建。' : err(r.data, '创建失败')
  if (r.ok) { tagName.value = ''; loadAll() }
}
const delTag = async t => {
  if (!confirm(`确定删除标签「${t.name}」？将同时解除所有关联。`)) return
  await api('/api/admin/tags/' + t.id, { method: 'DELETE' })
  loadAll()
}

/* 留言 */
const replyInputs = ref({})
const sendReply = async m => {
  const reply = replyInputs.value[m.id] ?? m.reply ?? ''
  const r = await api('/api/admin/messages/' + m.id, { method: 'PUT', body: JSON.stringify({ reply, visible: m.visible }) })
  if (r.ok) loadAll()
}
const toggleMsg = async m => {
  await api('/api/admin/messages/' + m.id, { method: 'PUT', body: JSON.stringify({ visible: !m.visible }) })
  loadAll()
}
const delMsg = async m => {
  if (!confirm('确定删除这条留言？')) return
  await api('/api/admin/messages/' + m.id, { method: 'DELETE' })
  loadAll()
}

/* 订阅者 */
const delSub = async u => {
  if (!confirm(`确定删除订阅者 ${u.email}？`)) return
  await api('/api/admin/subscribers/' + u.id, { method: 'DELETE' })
  loadAll()
}

/* 设置 */
const saveSettings = async () => {
  const r = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify(settings.value) })
  notes.value.settings = r.ok ? '已保存。' : err(r.data, '保存失败')
  setTimeout(() => { notes.value.settings = '' }, 2500)
}

/* 审计 */
const loadAudit = async () => {
  const q = auditQuery.value.trim()
  const r = await api('/api/admin/audit?limit=100' + (q ? '&q=' + encodeURIComponent(q) : ''))
  if (r.ok) auditRows.value = r.data.items || []
}

/* 云盘 / 音乐 / 工作台（列表 + 删除；上传在原版后台或空间页） */
const loadCloud = async () => {
  const r = await api('/api/cloud/files')
  cloudFiles.value = r.ok ? (r.data.files || r.data.items || r.data || []) : []
}
const delCloud = async f => {
  if (!confirm(`确定删除云盘文件「${f.name || f.filename}」？`)) return
  await api('/api/admin/cloud/files/' + f.id, { method: 'DELETE' })
  loadCloud()
}
const loadMusic = async () => {
  const r = await api('/api/admin/music/tracks')
  tracks.value = r.ok ? (r.data.tracks || r.data.items || r.data || []) : []
}
const delTrack = async t => {
  if (!confirm(`确定删除音乐「${t.title}」？`)) return
  await api('/api/admin/music/' + t.id, { method: 'DELETE' })
  loadMusic()
}
const loadWorkspace = async () => {
  const r = await api('/api/workspace/notes?limit=50')
  workspaceItems.value = r.ok ? (r.data.notes || r.data.items || r.data || []) : []
}
const delNote = async n => {
  if (!confirm('确定删除该笔记？')) return
  await api('/api/workspace/notes/' + n.id, { method: 'DELETE' })
  loadWorkspace()
}

/* 项目状态 */
const STATUS = { idea: '构想中', building: '开发中', maintained: '维护中', archived: '已归档' }
const delProject = async p => {
  if (!confirm(`确定删除项目「${p.name}」？`)) return
  await api('/api/admin/projects/' + p.id, { method: 'DELETE' })
  loadAll()
}

onMounted(() => {
  window.addEventListener('hashchange', onHash)
  if (authed.value) loadAll()
})
onBeforeUnmount(() => window.removeEventListener('hashchange', onHash))
</script>

<template>
  <div class="admin-shell">
    <!-- 登录门 -->
    <form v-if="!authed" class="admin-gate" @submit.prevent="doLogin">
      <h1>Y's Blog 后台</h1>
      <input v-model="username" type="text" placeholder="用户名" autocomplete="username" />
      <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" />
      <button type="submit" :disabled="gating">{{ gating ? '登录中…' : '进入后台' }}</button>
      <p class="gate-error">{{ gateErr }}</p>
    </form>

    <!-- 管理面板 -->
    <div v-else class="admin-layout">
      <aside class="admin-side">
        <div class="side-brand">Y's Blog · 后台</div>
        <a v-for="p in PANELS" :key="p" href="javascript:;"
           :class="{ active: panel === p }" @click="showPanel(p)">{{ LABELS[p] }}</a>
        <div class="side-exit">
          <a href="/" target="_blank" rel="noopener">打开站点 ↗</a>
          <a href="javascript:;" @click="logout">退出登录</a>
        </div>
      </aside>

      <div class="admin-content">
        <!-- 概览 -->
        <template v-if="panel === 'workspace'">
          <h2>概览</h2>
          <div class="admin-stats" v-if="stats">
            <div class="stat-card" v-for="(v, k) in { 文章: stats.articles, 分类: stats.categories, 留言: stats.messages, 订阅者: stats.subscribers, 总阅读: stats.views }" :key="k">
              <b>{{ v }}</b><span>{{ k }}</span>
            </div>
          </div>
          <div class="admin-panel-card">
            <h3>知识笔记（最近 50 条）</h3>
            <table class="admin-table">
              <thead><tr><th>标题</th><th>更新时间</th><th></th></tr></thead>
              <tbody>
                <tr v-for="n in workspaceItems" :key="n.id">
                  <td>{{ n.title || '(无标题)' }}</td>
                  <td class="muted">{{ (n.updated_at || '').replace('T', ' ').slice(0, 16) }}</td>
                  <td class="actions"><button class="danger" @click="delNote(n)">删除</button></td>
                </tr>
                <tr v-if="!workspaceItems.length"><td colspan="3" class="muted">还没有笔记。</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- 云盘 -->
        <template v-else-if="panel === 'cloud'">
          <h2>云盘</h2>
          <p class="admin-note" style="margin-bottom:16px;">上传请在「个人空间 → 云盘」操作。</p>
          <table class="admin-table">
            <thead><tr><th>文件名</th><th>大小</th><th>时间</th><th></th></tr></thead>
            <tbody>
              <tr v-for="f in cloudFiles" :key="f.id">
                <td>{{ f.name || f.filename }}</td>
                <td class="muted">{{ f.size_human || f.size + ' B' }}</td>
                <td class="muted">{{ (f.created_at || '').replace('T', ' ').slice(0, 16) }}</td>
                <td class="actions"><button class="danger" @click="delCloud(f)">删除</button></td>
              </tr>
              <tr v-if="!cloudFiles.length"><td colspan="4" class="muted">云盘是空的。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 音乐库 -->
        <template v-else-if="panel === 'music'">
          <h2>音乐库</h2>
          <p class="admin-note" style="margin-bottom:16px;">上传请在「个人空间 → 音乐库」操作。</p>
          <table class="admin-table">
            <thead><tr><th>标题</th><th>艺术家</th><th>可见性</th><th></th></tr></thead>
            <tbody>
              <tr v-for="t in tracks" :key="t.id">
                <td>{{ t.title }}</td><td class="muted">{{ t.artist || '—' }}</td>
                <td class="muted">{{ t.visibility === 'public' ? '公开' : '私密' }}</td>
                <td class="actions"><button class="danger" @click="delTrack(t)">删除</button></td>
              </tr>
              <tr v-if="!tracks.length"><td colspan="4" class="muted">曲库是空的。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 文章 -->
        <template v-else-if="panel === 'articles'">
          <h2>文章</h2>
          <p class="admin-note" style="margin-bottom:16px;">新建与编辑请使用原版编辑器（<a class="link-muted" href="/yy-AviuuP3r.html#articles" target="_blank">打开旧版后台 ↗</a>），此处支持删除。</p>
          <table class="admin-table">
            <thead><tr><th>标题</th><th>分类</th><th>日期</th><th>阅读</th><th></th></tr></thead>
            <tbody>
              <tr v-for="a in articles" :key="a.slug">
                <td>{{ a.title }}<div class="muted">/post-{{ a.slug }}.html<template v-if="a.kind === 'note'"> · 技术笔记</template></div></td>
                <td>{{ a.category_name }}</td><td class="muted">{{ a.date }}</td><td>{{ a.views }}</td>
                <td class="actions"><button class="danger" @click="delArticle(a.slug)">删除</button></td>
              </tr>
              <tr v-if="!articles.length"><td colspan="5" class="muted">还没有文章。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 项目 -->
        <template v-else-if="panel === 'projects'">
          <h2>项目</h2>
          <p class="admin-note" style="margin-bottom:16px;">新建与编辑请在「个人空间」或原版后台操作。</p>
          <table class="admin-table">
            <thead><tr><th>名称</th><th>状态</th><th></th></tr></thead>
            <tbody>
              <tr v-for="p in projects" :key="p.id">
                <td>{{ p.name }}</td><td class="muted">{{ STATUS[p.status] || p.status }}</td>
                <td class="actions"><button class="danger" @click="delProject(p)">删除</button></td>
              </tr>
              <tr v-if="!projects.length"><td colspan="3" class="muted">还没有项目。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 分类 -->
        <template v-else-if="panel === 'categories'">
          <h2>分类</h2>
          <div class="admin-panel-card">
            <h3>{{ catEditing ? '编辑分类「' + catEditing + '」' : '新建分类' }}</h3>
            <div class="admin-form">
              <input v-model="catForm.name" placeholder="名称" />
              <input v-model="catForm.slug" placeholder="slug（如 frontend）" />
              <input v-model="catForm.description" placeholder="描述（选填）" style="min-width:220px" />
              <button type="button" @click="saveCat">保存</button>
              <span class="admin-note">{{ catNote }}</span>
            </div>
          </div>
          <table class="admin-table">
            <thead><tr><th>名称</th><th>slug</th><th>描述</th><th>文章数</th><th></th></tr></thead>
            <tbody>
              <tr v-for="c in categories" :key="c.slug">
                <td>{{ c.name }}</td><td class="muted">{{ c.slug }}</td>
                <td class="muted">{{ c.description || '—' }}</td><td>{{ c.article_count }}</td>
                <td class="actions">
                  <button @click="editCat(c)">编辑</button>
                  <button class="danger" @click="delCat(c)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- 标签 -->
        <template v-else-if="panel === 'tags'">
          <h2>标签</h2>
          <div class="admin-panel-card">
            <h3>新建标签</h3>
            <div class="admin-form">
              <input v-model="tagName" placeholder="标签名" @keyup.enter="addTag" />
              <button type="button" @click="addTag">创建</button>
              <span class="admin-note">{{ tagNote }}</span>
            </div>
          </div>
          <div class="admin-panel-card" v-if="tags.length">
            <div v-for="t in tags" :key="t.id" style="display:flex;align-items:center;gap:12px;padding:10px 4px;border-bottom:1px solid var(--hairline)">
              <b style="font-size:13.5px">{{ t.name }}</b>
              <span class="admin-note">{{ t.count }} 个关联</span>
              <button class="danger" style="margin-left:auto;padding:6px 14px;border-radius:999px;font-size:12px;background:none;border:1px solid rgba(229,72,77,.35);color:var(--danger);cursor:pointer" @click="delTag(t)">删除</button>
            </div>
          </div>
          <p v-else class="list-empty">还没有标签。保存文章时填写标签会自动创建。</p>
        </template>

        <!-- 留言 -->
        <template v-else-if="panel === 'messages'">
          <h2>留言管理</h2>
          <div class="msg-item" v-for="m in messages" :key="m.id" :class="{ 'is-hidden-msg': !m.visible }">
            <div class="head"><b>{{ m.name }}</b><span class="meta">{{ m.created_at }}<template v-if="m.contact"> · {{ m.contact }}</template></span></div>
            <p>{{ m.content }}</p>
            <div class="reply-box">
              <input v-model="replyInputs[m.id]" :placeholder="'写下回复…'" />
              <button type="button" @click="sendReply(m)">回复</button>
            </div>
            <div class="ops">
              <button type="button" @click="toggleMsg(m)">{{ m.visible ? '隐藏' : '取消隐藏' }}</button>
              <button type="button" class="danger" @click="delMsg(m)">删除</button>
              <span v-if="!m.visible" class="badge">已隐藏</span>
            </div>
          </div>
          <p v-if="!messages.length" class="list-empty">还没有留言。</p>
        </template>

        <!-- 订阅者 -->
        <template v-else-if="panel === 'subscribers'">
          <h2>订阅者</h2>
          <table class="admin-table">
            <thead><tr><th>#</th><th>邮箱</th><th>时间</th><th></th></tr></thead>
            <tbody>
              <tr v-for="u in subscribers" :key="u.id">
                <td>{{ u.id }}</td><td>{{ u.email }}</td><td class="muted">{{ u.created_at }}</td>
                <td class="actions"><button class="danger" @click="delSub(u)">删除</button></td>
              </tr>
              <tr v-if="!subscribers.length"><td colspan="4" class="muted">还没有订阅者。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 设置 -->
        <template v-else-if="panel === 'settings'">
          <h2>站点设置</h2>
          <div class="admin-panel-card">
            <div class="settings-grid">
              <label>站点名称<input v-model="settings.site_name" /></label>
              <label>首页标题（灰色部分）<input v-model="settings.hero_muted" /></label>
              <label>首页标题（主体）<input v-model="settings.hero_main" /></label>
              <label>首页副标题<input v-model="settings.hero_subline" /></label>
              <label>GitHub<input v-model="settings.social_github" /></label>
              <label>微信（链接或复制文本）<input v-model="settings.social_wechat" /></label>
              <label>QQ<input v-model="settings.social_qq" /></label>
              <label>抖音<input v-model="settings.social_douyin" /></label>
              <label>关于页引言<textarea v-model="settings.about_intro" rows="2"></textarea></label>
              <label>关于页正文（HTML）<textarea v-model="settings.about_content" rows="6"></textarea></label>
              <button type="button" @click="saveSettings">保存设置</button>
              <span class="admin-note">{{ notes.settings }}</span>
            </div>
          </div>
        </template>

        <!-- 审计 -->
        <template v-else-if="panel === 'audit'">
          <h2>审计日志</h2>
          <div class="import-row" style="margin-bottom:16px">
            <input v-model="auditQuery" type="search" placeholder="搜索动作 / 用户 / IP / 详情…" @keyup.enter="loadAudit" />
            <button type="button" class="import-btn" @click="loadAudit">刷新</button>
          </div>
          <table class="admin-table">
            <thead><tr><th>时间</th><th>动作</th><th>用户</th><th>IP</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="a in auditRows" :key="a.id">
                <td class="muted">{{ (a.created_at || '').replace('T', ' ').slice(0, 19) }}</td>
                <td>{{ a.action }}</td><td>{{ a.user }}</td><td class="muted">{{ a.ip }}</td>
                <td class="muted">{{ a.detail }}</td>
              </tr>
              <tr v-if="!auditRows.length"><td colspan="5" class="muted">暂无记录，点「刷新」加载。</td></tr>
            </tbody>
          </table>
        </template>

        <!-- 管理员 -->
        <template v-else-if="panel === 'admins'">
          <h2>管理员</h2>
          <p class="admin-note">管理员账号当前通过 app/scripts/init_admin.py 在服务器上维护，在线管理功能将在后续版本提供。</p>
        </template>
      </div>
    </div>
  </div>
</template>
