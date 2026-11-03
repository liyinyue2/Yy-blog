<script setup>
/** 知识库 —— 私人笔记（/api/workspace/notes，富文本入库前服务端清洗） */
import { ref, onMounted } from 'vue'
import { api, asList, errOf } from '../api/client'
import { confirmAsk } from '../composables/useConfirm'

const notes = ref([])
const total = ref(0)
const q = ref('')
const editing = ref(null)      // null=新建，数字=编辑中的 id
const form = ref({ title: '', content: '' })
const note = ref('')
const loading = ref(true)

const load = async () => {
  const r = await api('/api/workspace/notes?limit=50')
  if (r.ok) { notes.value = asList(r.data); total.value = r.data.total || 0 }
  loading.value = false
}
const open = n => {
  editing.value = n ? n.id : 'new'
  form.value = { title: n ? n.title : '', content: n ? n.content : '' }
  note.value = ''
}
const close = () => { editing.value = null; form.value = { title: '', content: '' } }
const save = async () => {
  if (!form.value.title.trim() && !form.value.content.trim()) { note.value = '标题或内容至少填一项。'; return }
  const body = JSON.stringify({ title: form.value.title.trim(), content: form.value.content })
  const r = editing.value === 'new'
    ? await api('/api/workspace/notes', { method: 'POST', body })
    : await api('/api/workspace/notes/' + editing.value, { method: 'PUT', body })
  note.value = r.ok ? '已保存。' : errOf(r.data, '保存失败')
  if (r.ok) { close(); load() }
}
const del = async n => {
  if (!(await confirmAsk({
    title: '删除笔记', text: '删除后不可恢复。', detail: n.title || '(无标题)', ok: '删除',
  }))) return
  await api('/api/workspace/notes/' + n.id, { method: 'DELETE' })
  close()
  load()
}
const shown = () => {
  const k = q.value.trim().toLowerCase()
  if (!k) return notes.value
  return notes.value.filter(n => `${n.title} ${n.content}`.toLowerCase().includes(k))
}
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>知识库</h2><p class="hint">共 {{ total }} 条私人笔记，仅自己可见。</p></div>
      <button type="button" class="g-btn--primary" @click="open(null)">新建笔记</button>
    </header>

    <div class="notes-layout" :class="{ editing: !!editing }">
      <div class="notes-side">
        <input v-model="q" type="search" placeholder="搜索标题或内容…" />
        <ul class="notes-list">
          <li v-for="n in shown()" :key="n.id" :class="{ on: editing === n.id }" @click="open(n)">
            <b>{{ n.title || '(无标题)' }}</b>
            <span>{{ (n.updated_at || '').slice(0, 16).replace('T', ' ') }}</span>
          </li>
          <li v-if="!shown().length && !loading" class="hint">还没有笔记。</li>
        </ul>
      </div>

      <div v-if="editing" class="card notes-edit">
        <input v-model="form.title" placeholder="标题" maxlength="200" />
        <textarea v-model="form.content" placeholder="支持 Markdown 原文或 HTML；保存时服务端会做白名单清洗。" rows="18"></textarea>
        <div class="row">
          <button type="button" class="g-btn--primary" @click="save">保存</button>
          <button type="button" @click="close">收起</button>
          <button v-if="editing !== 'new'" type="button" class="danger" @click="del({ id: editing, title: form.title })">删除</button>
          <span class="hint">{{ note }}</span>
        </div>
      </div>
      <p v-else class="hint pick">从左侧选一条笔记，或点「新建笔记」。</p>
    </div>
  </section>
</template>
