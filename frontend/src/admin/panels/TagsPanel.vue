<script setup>
/** 标签管理 —— 统一标签体系（文章/项目/曲目共用），含关联计数 */
import { ref, computed, onMounted } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'

const rows = ref([])
const state = ref('loading')
const name = ref('')
const query = ref('')
const note = ref('')

const load = async () => {
  const r = await api('/api/tags')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
}
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? rows.value.filter(t => t.name.toLowerCase().includes(q)) : rows.value
})
const add = async () => {
  const v = name.value.trim()
  if (!v) { note.value = '请输入标签名。'; return }
  const r = await api('/api/admin/tags', { method: 'POST', body: JSON.stringify({ name: v }) })
  if (!r.ok) { note.value = errOf(r.data, '创建失败'); return }
  note.value = '已创建。'; name.value = ''; load()
}
const remove = async t => {
  if (!(await confirmAsk({
    title: '删除标签',
    text: t.count ? `将解除它与 ${t.count} 条内容的关联。` : '该标签尚未挂任何内容。',
    detail: t.name, ok: '删除',
  }))) return
  const r = await api('/api/admin/tags/' + t.id, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  note.value = '已删除。'; load()
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>标签</h2><p class="hint">{{ rows.length }} 个标签 · 保存文章时填的标签会自动创建</p></div>
    </header>

    <form class="card inline-form" @submit.prevent="add">
      <input v-model="name" placeholder="新建标签名" maxlength="32" />
      <button type="submit" class="g-btn--sm g-btn--primary">创建</button>
      <input v-model="query" type="search" placeholder="搜索标签…" />
      <span class="hint">{{ note }}</span>
    </form>

    <DataState :state="state" empty-text="还没有标签。" @retry="load">
      <div class="tag-wrap">
        <span v-for="t in shown" :key="t.id" class="tag-item">
          <b>{{ t.name }}</b><em>{{ t.count }}</em>
          <button type="button" @click="remove(t)" :aria-label="'删除标签 ' + t.name">×</button>
        </span>
      </div>
    </DataState>
  </section>
</template>
