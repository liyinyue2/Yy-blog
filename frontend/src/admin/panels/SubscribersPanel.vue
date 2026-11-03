<script setup>
/** 订阅者 —— 列表、搜索、导出 CSV、删除 */
import { ref, computed, onMounted } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'

const rows = ref([])
const state = ref('loading')
const query = ref('')
const note = ref('')

const load = async () => {
  const r = await api('/api/admin/subscribers')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
}
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? rows.value.filter(s => s.email.toLowerCase().includes(q)) : rows.value
})
const exportCsv = () => {
  if (!rows.value.length) { note.value = '没有可导出的订阅者。'; return }
  const csv = 'email,created_at\n' + rows.value.map(s => `${s.email},${s.created_at}`).join('\n')
  const url = URL.createObjectURL(new Blob(['' + csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url; a.download = 'subscribers.csv'
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 3000)
}
const remove = async s => {
  if (!(await confirmAsk({ title: '删除订阅者', text: '该邮箱将不再收到更新通知。', detail: s.email, ok: '删除' }))) return
  const r = await api('/api/admin/subscribers/' + s.id, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  load()
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>订阅者</h2><p class="hint">{{ rows.length }} 人</p></div>
      <button type="button" class="g-btn" @click="exportCsv">导出 CSV</button>
    </header>
    <div class="toolbar">
      <input v-model="query" type="search" placeholder="搜索邮箱…" />
      <span v-if="note" class="hint inline-note">{{ note }}</span>
    </div>

    <DataState :state="state" empty-text="还没有订阅者。" @retry="load">
      <ul class="rows">
        <li v-for="s in shown" :key="s.id" class="row">
          <div class="row-main"><b>{{ s.email }}</b>
            <span class="row-meta"><em>{{ (s.created_at || '').slice(0, 16).replace('T', ' ') }}</em></span>
          </div>
          <div class="row-ops"><button type="button" class="danger g-btn--sm" @click="remove(s)">删除</button></div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
