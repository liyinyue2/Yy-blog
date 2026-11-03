<script setup>
/**
 * 博客管理 · 文章 —— 列表 + 抽屉编辑器 + Word/PDF 导入
 * 此前该面板只有删除，写文章要跳回 v2 旧后台。
 */
import { ref, computed, onMounted } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'
import { vSlideBall } from '../../directives/slideBall'

const props = defineProps({ autoOpen: { type: Boolean, default: false } })

const rows = ref([])
const cats = ref([])
const state = ref('loading')
const query = ref('')
const kind = ref('all')

const load = async () => {
  state.value = state.value === 'ok' ? 'ok' : 'loading'
  const [a, c] = await Promise.all([api('/api/admin/articles'), api('/api/categories')])
  if (!a.ok) { state.value = 'error'; return }
  rows.value = asList(a.data)
  cats.value = asList(c.data)
  state.value = 'ok'
}

const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return rows.value.filter(a =>
    (kind.value === 'all' || (a.kind || 'article') === kind.value)
    && (!q || `${a.title} ${a.slug} ${a.summary || ''}`.toLowerCase().includes(q)))
})

/* ---------- 编辑器 ---------- */
const emptyForm = () => ({
  title: '', slug: '', category: '', summary: '', content: '',
  date: new Date().toISOString().slice(0, 10), kind: 'article', tags: '',
})
const open = ref(false)
const editingSlug = ref('')      // 空串 = 新建
const form = ref(emptyForm())
const saving = ref(false)
const note = ref('')
const preview = ref(false)

const startNew = () => {
  editingSlug.value = ''
  form.value = emptyForm()
  note.value = ''
  preview.value = false
  open.value = true
}
const startEdit = async a => {
  const r = await api('/api/articles/' + encodeURIComponent(a.slug))
  if (!r.ok) { note.value = errOf(r.data, '读取文章详情失败'); return }
  const d = r.data
  /* 详情里的 date 是展示格式（2026.10.28），input[type=date] 只认 ISO，用 published_at 兜底 */
  const iso = String(d.published_at || '').slice(0, 10)
  const date = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso : String(d.date || '').replace(/\./g, '-')
  editingSlug.value = a.slug
  form.value = {
    title: d.title || '', slug: d.slug || '', category: d.category_name || d.category || '',
    summary: d.summary || '', content: d.content || '', date,
    kind: d.kind || 'article', tags: (d.tags || []).join(', '),
  }
  note.value = ''
  preview.value = false
  open.value = true
}
const close = () => { open.value = false }

const save = async () => {
  const f = form.value
  if (!f.title.trim()) { note.value = '标题不能为空。'; return }
  if (!f.category.trim()) { note.value = '请选择分类。'; return }
  saving.value = true; note.value = ''
  const body = JSON.stringify({
    title: f.title.trim(), slug: f.slug.trim(), category: f.category.trim(),
    summary: f.summary.trim(), content: f.content, date: f.date, kind: f.kind,
    tags: f.tags.split(/[,，]/).map(s => s.trim()).filter(Boolean),
  })
  const r = editingSlug.value
    ? await api('/api/admin/articles/' + encodeURIComponent(editingSlug.value), { method: 'PUT', body })
    : await api('/api/admin/articles', { method: 'POST', body })
  saving.value = false
  if (!r.ok) { note.value = errOf(r.data, '保存失败'); return }
  note.value = `已保存：${r.data.slug || f.title}`
  editingSlug.value = r.data.slug || editingSlug.value
  await load()
  setTimeout(() => { if (note.value.startsWith('已保存')) { note.value = ''; close() } }, 900)
}

const remove = async a => {
  if (!(await confirmAsk({ title: '删除文章', text: '删除后不可恢复。', detail: a.title, ok: '删除' }))) return
  const r = await api('/api/admin/articles/' + encodeURIComponent(a.slug), { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  if (editingSlug.value === a.slug) close()
  load()
}

/* ---------- 文档导入 ---------- */
const importing = ref(false)
const pickDoc = async e => {
  const file = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!file) return
  importing.value = true; note.value = ''
  try {
    const buf = await file.arrayBuffer()
    let bin = ''
    const bytes = new Uint8Array(buf)
    for (let i = 0; i < bytes.length; i += 0x8000) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000))
    }
    const r = await api('/api/admin/convert', {
      method: 'POST',
      body: JSON.stringify({ filename: file.name, data: btoa(bin) }),
    })
    if (!r.ok) { note.value = errOf(r.data, '导入失败'); return }
    if (!open.value) startNew()
    form.value.title = form.value.title || r.data.title
    form.value.content = r.data.content
    note.value = `已导入 ${file.name}（${r.data.chars} 字），请补分类与标签后保存。`
  } catch {
    note.value = '导入失败：文件读取异常。'
  } finally {
    importing.value = false
  }
}

const KINDS = [{ value: 'all', label: '全部' }, { value: 'article', label: '文章' }, { value: 'note', label: '技术笔记' }]
const previewHtml = computed(() => form.value.content.trim() || '<p class="hint">(暂无内容)</p>')
onMounted(() => { load(); if (props.autoOpen) startNew() })
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>文章</h2><p class="hint">{{ rows.length }} 篇 · 支持 Word / PDF 导入</p></div>
      <div class="panel-ops">
        <label class="g-btn">
          {{ importing ? '解析中…' : '导入 Word / PDF' }}
          <input type="file" accept=".docx,.pdf" hidden :disabled="importing" @change="pickDoc" />
        </label>
        <button type="button" class="g-btn g-btn--primary" @click="startNew">新建文章</button>
      </div>
    </header>

    <div class="toolbar">
      <input v-model="query" type="search" placeholder="搜索标题、slug 或摘要…" />
      <div class="seg" v-slide-ball>
        <button v-for="k in KINDS" :key="k.value" type="button" class="chip"
                :class="{ 'is-active': kind === k.value }" @click="kind = k.value">{{ k.label }}</button>
      </div>
    </div>

    <DataState :state="state" empty-text="还没有文章，点右上「新建文章」开始写。" @retry="load">
      <ul class="rows">
        <li v-for="a in shown" :key="a.slug" class="row">
          <div class="row-main">
            <b>{{ a.title }}</b>
            <p class="row-sum">{{ a.summary || '（无摘要）' }}</p>
            <span class="row-meta">
              <em class="g-tag">{{ a.category_name || '未分类' }}</em>
              <em v-if="a.kind === 'note'" class="g-tag accent">技术笔记</em>
              <em>{{ a.date }}</em><em>{{ a.views }} 阅读</em><em class="slug">/post/{{ a.slug }}</em>
            </span>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="startEdit(a)">编辑</button>
            <button type="button" class="danger g-btn--sm" @click="remove(a)">删除</button>
          </div>
        </li>
        <li v-if="!shown.length" class="hint pad">没有匹配「{{ query }}」的文章。</li>
      </ul>
    </DataState>

    <!-- 编辑器抽屉 -->
    <transition name="drawer">
      <div v-if="open" class="drawer-mask" @click.self="close">
        <form class="drawer" @submit.prevent="save">
          <header class="drawer-head">
            <h3>{{ editingSlug ? '编辑文章' : '新建文章' }}</h3>
            <button type="button" class="g-btn--sm" @click="close">收起</button>
          </header>

          <div class="field">
            <label for="a-title">标题</label>
            <input id="a-title" v-model="form.title" maxlength="120" placeholder="给文章起个标题" />
          </div>
          <div class="field-grid">
            <div class="field">
              <label for="a-cat">分类</label>
              <input id="a-cat" v-model="form.category" list="cat-list" placeholder="选择或输入新分类" />
              <datalist id="cat-list"><option v-for="c in cats" :key="c.slug" :value="c.name"></option></datalist>
            </div>
            <div class="field">
              <label for="a-kind">类型</label>
              <select id="a-kind" v-model="form.kind"><option value="article">文章</option><option value="note">技术笔记</option></select>
            </div>
            <div class="field">
              <label for="a-date">日期</label>
              <input id="a-date" v-model="form.date" type="date" />
            </div>
            <div class="field">
              <label for="a-slug">slug（留空自动生成）</label>
              <input id="a-slug" v-model="form.slug" placeholder="留空则按标题生成，支持中文" />
            </div>
          </div>
          <div class="field">
            <label for="a-tags">标签（逗号分隔，最多 20 个）</label>
            <input id="a-tags" v-model="form.tags" placeholder="如：前端, 交互设计" />
          </div>
          <div class="field">
            <label for="a-sum">摘要</label>
            <textarea id="a-sum" v-model="form.summary" rows="2" maxlength="300" placeholder="列表里展示的一两句话"></textarea>
          </div>
          <div class="field grow">
            <label for="a-body">
              正文（HTML）
              <button type="button" class="link-btn" @click="preview = !preview">{{ preview ? '继续编辑' : '预览' }}</button>
            </label>
            <textarea v-if="!preview" id="a-body" v-model="form.content" class="body-area"
                      placeholder="<h2>小标题</h2>&#10;<p>正文…</p>"></textarea>
            <div v-else class="body-area preview" v-html="previewHtml"></div>
          </div>

          <footer class="drawer-foot">
            <button type="submit" class="g-btn g-btn--primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
            <button type="button" @click="close">取消</button>
            <span class="hint">{{ note }}</span>
          </footer>
        </form>
      </div>
    </transition>
  </section>
</template>
