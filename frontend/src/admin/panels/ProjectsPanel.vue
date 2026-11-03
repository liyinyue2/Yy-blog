<script setup>
/**
 * 项目中心 —— 项目 CRUD + 开发日志
 * 此前该面板只有删除。
 */
import { ref, computed, onMounted } from 'vue'
import { api, asList, errOf } from '../../api/client'
import { PROJECT_STATUS } from '../../constants'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'

const rows = ref([])
const state = ref('loading')
const query = ref('')
const note = ref('')

const load = async () => {
  const r = await api('/api/admin/projects')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
}
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? rows.value.filter(p => `${p.name} ${p.summary}`.toLowerCase().includes(q)) : rows.value
})

const emptyForm = () => ({
  name: '', slug: '', summary: '', description: '', tech: '', status: 'idea',
  repo_url: '', demo_url: '', progress: 0, sort: 0, visibility: 'public',
})
const editing = ref(null)          // null=关闭，'new'=新建，数字=编辑中的 id
const form = ref(emptyForm())
const saving = ref(false)

const startNew = () => { editing.value = 'new'; form.value = emptyForm(); note.value = '' }
const startEdit = p => {
  editing.value = p.id
  form.value = {
    name: p.name || '', slug: p.slug || '', summary: p.summary || '', description: p.description || '',
    tech: (p.tech_stack || []).join(', '), status: p.status || 'idea', repo_url: p.repo_url || '',
    demo_url: p.demo_url || '', progress: p.progress ?? 0, sort: p.sort ?? 0, visibility: p.visibility || 'public',
  }
  note.value = ''
}
const close = () => { editing.value = null }

const save = async () => {
  if (!form.value.name.trim()) { note.value = '项目名称必填。'; return }
  saving.value = true; note.value = ''
  const body = JSON.stringify({
    name: form.value.name.trim(), slug: form.value.slug.trim(), summary: form.value.summary.trim(),
    description: form.value.description, tech_stack: form.value.tech.split(/[,，]/).map(s => s.trim()).filter(Boolean).slice(0, 12),
    status: form.value.status, repo_url: form.value.repo_url.trim(), demo_url: form.value.demo_url.trim(),
    progress: Number(form.value.progress) || 0, sort: Number(form.value.sort) || 0, visibility: form.value.visibility,
  })
  const r = editing.value === 'new'
    ? await api('/api/admin/projects', { method: 'POST', body })
    : await api('/api/admin/projects/' + editing.value, { method: 'PUT', body })
  saving.value = false
  note.value = r.ok ? '已保存。' : errOf(r.data, '保存失败')
  if (r.ok) { close(); load() }
}
const remove = async p => {
  if (!(await confirmAsk({ title: '删除项目', text: '项目及其开发日志都会被删除。', detail: p.name, ok: '删除' }))) return
  await api('/api/admin/projects/' + p.id, { method: 'DELETE' })
  if (editing.value === p.id) close()
  load()
}

/* ---------- 开发日志 ---------- */
const logsFor = ref(null)
const logs = ref([])
const logForm = ref({ title: '', content: '', log_date: new Date().toISOString().slice(0, 10) })
const openLogs = async p => {
  logsFor.value = p
  logs.value = []
  const r = await api(`/api/admin/projects/${p.id}/logs`)
  if (r.ok) logs.value = asList(r.data)
}
const addLog = async () => {
  if (!logForm.value.log_date) { note.value = '日志日期必填。'; return }
  const r = await api(`/api/admin/projects/${logsFor.value.id}/logs`, {
    method: 'POST', body: JSON.stringify(logForm.value),
  })
  if (!r.ok) { note.value = errOf(r.data, '日志添加失败'); return }
  logForm.value = { title: '', content: '', log_date: logForm.value.log_date }
  openLogs(logsFor.value)
}
const delLog = async l => {
  if (!(await confirmAsk({ title: '删除开发日志', text: '这条日志会被删除。', detail: l.title || l.content.slice(0, 30), ok: '删除' }))) return
  await api(`/api/admin/projects/${logsFor.value.id}/logs/${l.id}`, { method: 'DELETE' })
  openLogs(logsFor.value)
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>项目</h2><p class="hint">{{ rows.length }} 个 · 公开项目会出现在博客「项目」页</p></div>
      <button type="button" class="g-btn g-btn--primary" @click="startNew">新建项目</button>
    </header>

    <div class="toolbar"><input v-model="query" type="search" placeholder="搜索项目名称或简介…" /></div>
    <p v-if="note" class="hint inline-note">{{ note }}</p>

    <DataState :state="state" empty-text="还没有项目。" @retry="load">
      <ul class="rows">
        <li v-for="p in shown" :key="p.id" class="row">
          <div class="row-main">
            <b>{{ p.name }}<em v-if="p.visibility === 'private'" class="g-tag">私有</em></b>
            <p class="row-sum">{{ p.summary || '（无简介）' }}</p>
            <span class="row-meta">
              <em class="g-tag accent">{{ PROJECT_STATUS[p.status] || p.status }}</em>
              <em>进度 {{ p.progress }}%</em>
              <em v-for="t in (p.tech_stack || []).slice(0, 4)" :key="t" class="g-tag">{{ t }}</em>
            </span>
            <div class="bar" :style="{ width: p.progress + '%' }" :aria-label="'进度 ' + p.progress + '%'"></div>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="startEdit(p)">编辑</button>
            <button type="button" class="g-btn--sm" @click="openLogs(p)">日志</button>
            <button type="button" class="danger g-btn--sm" @click="remove(p)">删除</button>
          </div>
        </li>
      </ul>
    </DataState>

    <!-- 编辑器 -->
    <transition name="drawer">
      <div v-if="editing" class="drawer-mask" @click.self="close">
        <form class="drawer" @submit.prevent="save">
          <header class="drawer-head">
            <h3>{{ editing === 'new' ? '新建项目' : '编辑项目' }}</h3>
            <button type="button" class="g-btn--sm" @click="close">收起</button>
          </header>
          <div class="field"><label for="p-name">名称</label><input id="p-name" v-model="form.name" maxlength="120" /></div>
          <div class="field-grid">
            <div class="field"><label for="p-status">状态</label>
              <select id="p-status" v-model="form.status">
                <option v-for="(label, value) in PROJECT_STATUS" :key="value" :value="value">{{ label }}</option>
              </select></div>
            <div class="field"><label for="p-vis">可见性</label>
              <select id="p-vis" v-model="form.visibility"><option value="public">公开</option><option value="private">仅自己</option></select></div>
            <div class="field"><label for="p-progress">进度 %</label><input id="p-progress" v-model.number="form.progress" type="number" min="0" max="100" /></div>
            <div class="field"><label for="p-sort">排序</label><input id="p-sort" v-model.number="form.sort" type="number" /></div>
          </div>
          <div class="field"><label for="p-slug">slug（留空自动生成）</label><input id="p-slug" v-model="form.slug" /></div>
          <div class="field"><label for="p-sum">简介</label><input id="p-sum" v-model="form.summary" maxlength="500" /></div>
          <div class="field"><label for="p-tech">技术栈（逗号分隔，最多 12 个）</label><input id="p-tech" v-model="form.tech" /></div>
          <div class="field-grid">
            <div class="field"><label for="p-repo">仓库地址</label><input id="p-repo" v-model="form.repo_url" placeholder="https://…" /></div>
            <div class="field"><label for="p-demo">演示地址</label><input id="p-demo" v-model="form.demo_url" placeholder="https://…" /></div>
          </div>
          <div class="field grow"><label for="p-desc">详情（HTML）</label><textarea id="p-desc" v-model="form.description" class="body-area" rows="8"></textarea></div>
          <footer class="drawer-foot">
            <button type="submit" class="g-btn g-btn--primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
            <button type="button" @click="close">取消</button>
          </footer>
        </form>
      </div>
    </transition>

    <!-- 开发日志 -->
    <transition name="drawer">
      <div v-if="logsFor" class="drawer-mask" @click.self="logsFor = null">
        <div class="drawer">
          <header class="drawer-head">
            <h3>开发日志 · {{ logsFor.name }}</h3>
            <button type="button" class="g-btn--sm" @click="logsFor = null">收起</button>
          </header>
          <form class="log-add" @submit.prevent="addLog">
            <input v-model="logForm.log_date" type="date" aria-label="日志日期" required />
            <input v-model="logForm.title" placeholder="标题（选填）" maxlength="200" />
            <input v-model="logForm.content" placeholder="这次做了什么" maxlength="20000" required />
            <button type="submit" class="g-btn--sm g-btn--primary">添加</button>
          </form>
          <ul class="log-list">
            <li v-for="l in logs" :key="l.id">
              <div class="log-main">
                <b>{{ l.title || '（无标题）' }}<em>{{ l.log_date }}</em></b>
                <p>{{ l.content }}</p>
              </div>
              <button type="button" class="danger g-btn--sm" @click="delLog(l)">删除</button>
            </li>
            <li v-if="!logs.length" class="hint pad">还没有开发日志。</li>
          </ul>
        </div>
      </div>
    </transition>
  </section>
</template>
