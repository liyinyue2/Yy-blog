<script setup>
/** 分类管理 —— 列表 + 新建/编辑 + 文章计数 + 非空保护提示 */
import { ref, onMounted } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'

const rows = ref([])
const state = ref('loading')
const form = ref({ name: '', slug: '', description: '' })
const editing = ref('')
const note = ref('')

const load = async () => {
  const r = await api('/api/categories')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
}
const reset = () => { editing.value = ''; form.value = { name: '', slug: '', description: '' } }
const save = async () => {
  if (!form.value.name.trim()) { note.value = '名称必填。'; return }
  const body = JSON.stringify(form.value)
  const r = editing.value
    ? await api('/api/admin/categories/' + encodeURIComponent(editing.value), { method: 'PUT', body })
    : await api('/api/admin/categories', { method: 'POST', body })
  if (!r.ok) { note.value = errOf(r.data, '保存失败'); return }
  note.value = '已保存。'; reset(); load()
}
const edit = c => {
  editing.value = c.slug
  form.value = { name: c.name, slug: c.slug, description: c.description || '' }
  note.value = ''
}
const remove = async c => {
  if (c.article_count) {
    note.value = `「${c.name}」下还有 ${c.article_count} 篇文章，先移走或删掉它们。`
    return
  }
  if (!(await confirmAsk({ title: '删除分类', text: '该分类将从站点中移除。', detail: c.name, ok: '删除' }))) return
  const r = await api('/api/admin/categories/' + encodeURIComponent(c.slug), { method: 'DELETE' })
  note.value = r.ok ? '已删除。' : errOf(r.data, '删除失败')
  load()
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>分类</h2><p class="hint">{{ rows.length }} 个分类</p></div>
    </header>

    <form class="card inline-form" @submit.prevent="save">
      <input v-model="form.name" placeholder="名称" maxlength="80" />
      <input v-model="form.slug" placeholder="slug（留空按名称生成）" maxlength="100" />
      <input v-model="form.description" placeholder="描述（选填）" maxlength="400" />
      <button type="submit" class="g-btn--sm g-btn--primary">{{ editing ? '保存修改' : '添加分类' }}</button>
      <button v-if="editing" type="button" class="g-btn--sm" @click="reset">取消</button>
      <span class="hint">{{ note }}</span>
    </form>

    <DataState :state="state" empty-text="还没有分类。" @retry="load">
      <ul class="rows">
        <li v-for="c in rows" :key="c.slug" class="row">
          <div class="row-main">
            <b>{{ c.name }}</b>
            <p class="row-sum">{{ c.description || '（无描述）' }}</p>
            <span class="row-meta"><em>{{ c.article_count }} 篇文章</em><em class="slug">/{{ c.slug }}</em></span>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="edit(c)">编辑</button>
            <button type="button" class="danger g-btn--sm" @click="remove(c)">删除</button>
          </div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
