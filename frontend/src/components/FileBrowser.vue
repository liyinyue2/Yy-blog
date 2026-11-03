<script setup>
/**
 * FileBrowser —— 云文件浏览与传输（个人空间「云文件」与网站管理「云盘」共用一份实现）
 */
import { ref, onMounted } from 'vue'
import { api, asList, errOf, accessToken } from '../api/client'
import DataState from './ui/DataState.vue'
import { confirmAsk } from '../composables/useConfirm'

const props = defineProps({ title: { type: String, default: '云文件' } })

const files = ref([])
const state = ref('loading')
const q = ref('')
const onlyStar = ref(false)
const busy = ref(false)
const note = ref('')

const fmtSize = n => n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB'
  : n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : (n || 0) + ' B'

const load = async () => {
  const params = new URLSearchParams({ limit: '100' })
  if (q.value.trim()) params.set('q', q.value.trim())
  if (onlyStar.value) params.set('star', '1')
  const r = await api('/api/cloud/files?' + params)
  if (!r.ok) { state.value = 'error'; return }
  files.value = asList(r.data)
  state.value = 'ok'
}

const upload = async e => {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!f) return
  busy.value = true; note.value = `上传中：${f.name}`
  const fd = new FormData()
  fd.append('file', f)
  const r = await api('/api/admin/cloud/upload', { method: 'POST', body: fd })
  note.value = r.ok ? `已上传：${f.name}` : errOf(r.data, '上传失败')
  busy.value = false
  load()
}

const star = async f => {
  await api('/api/admin/cloud/files/' + f.id, { method: 'PATCH', body: JSON.stringify({ is_starred: !f.is_starred }) })
  load()
}

/* 下载接口需鉴权，<a> 带不了 Bearer → blob + 临时 objectURL */
const download = async f => {
  note.value = '准备下载…'
  const res = await fetch('/api/cloud/download/' + f.id, { headers: { Authorization: 'Bearer ' + accessToken() } })
  if (!res.ok) { note.value = errOf(await res.json().catch(() => ({})), '下载失败'); return }
  const cd = res.headers.get('content-disposition') || ''
  const utf = cd.match(/filename\*=UTF-8''([^;]+)/i)
  const plain = cd.match(/filename="?([^";]+)"?/i)
  const name = utf ? decodeURIComponent(utf[1]) : (plain ? plain[1] : f.original_name)
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 4000)
  note.value = ''
}

const remove = async f => {
  if (!(await confirmAsk({ title: '删除文件', text: '删除后不可恢复。', detail: f.original_name, ok: '删除' }))) return
  await api('/api/admin/cloud/files/' + f.id, { method: 'DELETE' })
  load()
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>{{ title }}</h2><p class="hint">{{ files.length }} 个文件 · 单文件上限 20 MB</p></div>
      <div class="panel-ops">
        <button type="button" class="chip" :class="{ 'is-active': onlyStar }" @click="onlyStar = !onlyStar; load()">只看收藏</button>
        <label class="g-btn g-btn--primary">
          {{ busy ? '上传中…' : '上传文件' }}
          <input type="file" hidden :disabled="busy" @change="upload" />
        </label>
      </div>
    </header>

    <div class="toolbar">
      <input v-model="q" type="search" placeholder="按文件名搜索…" @keyup.enter="load" />
      <button type="button" class="g-btn--sm" @click="load">搜索</button>
      <span v-if="note" class="hint inline-note">{{ note }}</span>
    </div>

    <DataState :state="state" empty-text="云盘是空的，点右上「上传文件」。" @retry="load">
      <ul class="file-rows">
        <li v-for="f in files" :key="f.id">
          <button type="button" class="star" :class="{ on: f.is_starred }" @click="star(f)"
                  :aria-label="f.is_starred ? '取消收藏' : '收藏'">{{ f.is_starred ? '★' : '☆' }}</button>
          <div class="fb-main">
            <b>{{ f.original_name }}</b>
            <span>{{ fmtSize(f.size) }} · {{ f.mime || '未知类型' }} · {{ (f.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="download(f)">下载</button>
            <button type="button" class="danger g-btn--sm" @click="remove(f)">删除</button>
          </div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
