<script setup>
/** 书签 —— /api/workspace/bookmarks（URL 仅允许 http/https，服务端校验） */
import { onMounted, ref } from 'vue'
import { api, asList, errOf } from '../api/client'
import DataState from '../components/ui/DataState.vue'

const rows = ref([])
const state = ref('loading')
const title = ref('')
const url = ref('')
const note = ref('')
const busy = ref(false)

const load = async () => {
  const r = await api('/api/workspace/bookmarks?limit=100')
  if (r.ok) { rows.value = asList(r.data); state.value = rows.value.length ? 'ok' : 'empty' }
  else state.value = 'error'
}

const add = async () => {
  const t = title.value.trim(); const u = url.value.trim()
  if (!t) { note.value = '先写个标题。'; return }
  if (!/^https?:\/\//i.test(u)) { note.value = '地址需以 http:// 或 https:// 开头。'; return }
  busy.value = true
  const r = await api('/api/workspace/bookmarks', { method: 'POST', body: JSON.stringify({ title: t, url: u }) })
  busy.value = false
  if (!r.ok) { note.value = errOf(r.data, '添加失败'); return }
  title.value = ''; url.value = ''; note.value = ''
  load()
}

const remove = async b => {
  const r = await api('/api/workspace/bookmarks/' + b.id, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  load()
}
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>书签</h2><p class="hint">收藏常用站点与资料，仅自己可见</p></div>
    </header>

    <form class="card" @submit.prevent="add">
      <div class="field-grid">
        <div class="field"><label for="b-title">标题</label>
          <input id="b-title" v-model="title" maxlength="200" placeholder="例如：Vue 文档" /></div>
        <div class="field"><label for="b-url">地址</label>
          <input id="b-url" v-model="url" placeholder="https://…" /></div>
      </div>
      <div class="set-foot">
        <button type="submit" class="g-btn--sm g-btn--primary" :disabled="busy">{{ busy ? '添加中…' : '添加' }}</button>
        <span class="hint">{{ note }}</span>
      </div>
    </form>

    <DataState :state="state" empty-text="还没有书签，先加一条。" @retry="load">
      <ul class="rows">
        <li v-for="b in rows" :key="b.id" class="row">
          <div class="row-main">
            <b><a :href="b.url" target="_blank" rel="noopener noreferrer">{{ b.title }}</a></b>
            <span class="hint">{{ b.url }}</span>
          </div>
          <div class="row-ops">
            <button type="button" class="danger g-btn--sm" @click="remove(b)">删除</button>
          </div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
