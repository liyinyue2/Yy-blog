<script setup>
/**
 * 音乐管理 —— 上传、试听、公开/私密切换、删除
 * 此前该面板只有列表与删除，上传要跳回 v2 旧后台。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'

const rows = ref([])
const state = ref('loading')
const busy = ref(false)
const note = ref('')
const playing = ref(null)
const audio = ref(null)

const fmtDur = s => { s = Math.round(+s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` }
const load = async () => {
  const r = await api('/api/admin/music/tracks')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
}
const publicCount = computed(() => rows.value.filter(t => t.visibility === 'public').length)

const upload = async e => {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!f) return
  busy.value = true; note.value = `上传中：${f.name}（最大 100 MB）`
  const fd = new FormData()
  fd.append('file', f)
  const r = await api('/api/admin/music/upload', { method: 'POST', body: fd })
  note.value = r.ok ? `已上传：${f.name}` : errOf(r.data, '上传失败')
  busy.value = false
  load()
}

const togglePlay = async t => {
  if (playing.value === t.id) { audio.value?.pause(); playing.value = null; return }
  if (!audio.value) {
    audio.value = new window.Audio()
    audio.value.onended = () => { playing.value = null }
    audio.value.onerror = () => { note.value = '该曲目无法播放（文件可能已被移除）'; playing.value = null }
  }
  audio.value.src = `/api/public/music/stream/${t.id}`
  try {
    await audio.value.play()
    playing.value = t.id
    // 播放计入最近播放（首页「正在听」数据来源）
    api(`/api/admin/music/${t.id}/play`, { method: 'POST' })
  } catch {
    note.value = '浏览器阻止了自动播放，请再点一次播放按钮。'
  }
}

const setVisibility = async t => {
  const visibility = t.visibility === 'public' ? 'private' : 'public'
  const r = await api('/api/admin/music/' + t.id, { method: 'PATCH', body: JSON.stringify({ visibility }) })
  if (!r.ok) { note.value = errOf(r.data, '切换失败'); return }
  note.value = visibility === 'public' ? `《${t.title}》已公开。` : `《${t.title}》已转为私密。`
  load()
}

const remove = async t => {
  if (!(await confirmAsk({ title: '删除曲目', text: '音频文件与记录都会被删除。', detail: `${t.title} — ${t.artist || '未知艺术家'}`, ok: '删除' }))) return
  await api('/api/admin/music/' + t.id, { method: 'DELETE' })
  if (playing.value === t.id) { audio.value?.pause(); playing.value = null }
  load()
}

onMounted(load)
onBeforeUnmount(() => audio.value?.pause())
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>音乐库</h2><p class="hint">{{ rows.length }} 首 · 公开 {{ publicCount }} 首会出现在博客「音乐」页</p></div>
      <label class="g-btn g-btn--primary">
        {{ busy ? '上传中…' : '上传音频' }}
        <input type="file" accept=".mp3,.flac,.wav,.ogg,.m4a,.aac" hidden :disabled="busy" @change="upload" />
      </label>
    </header>
    <p v-if="note" class="hint inline-note">{{ note }}</p>

    <DataState :state="state" empty-text="曲库是空的，点右上「上传音频」。" @retry="load">
      <ul class="rows">
        <li v-for="t in rows" :key="t.id" class="row">
          <button type="button" class="play" :class="{ on: playing === t.id }" @click="togglePlay(t)"
                  :aria-label="playing === t.id ? '暂停' : '播放'">{{ playing === t.id ? '❚❚' : '▶' }}</button>
          <div class="row-main">
            <b>{{ t.title }}</b>
            <p class="row-sum">{{ t.artist || '未知艺术家' }}<template v-if="t.album"> · {{ t.album }}</template></p>
            <span class="row-meta">
              <em>{{ fmtDur(t.duration) }}</em>
              <em class="g-tag" :class="{ accent: t.visibility === 'public' }">{{ t.visibility === 'public' ? '公开' : '私密' }}</em>
            </span>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="setVisibility(t)">{{ t.visibility === 'public' ? '转为私密' : '设为公开' }}</button>
            <button type="button" class="danger g-btn--sm" @click="remove(t)">删除</button>
          </div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
