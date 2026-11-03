<script setup>
/**
 * 歌单管理 —— 公开页只负责播放；歌单的创建/改名/删除/选曲都在这里。
 * 数据：/api/admin/music/playlists（含私密曲目），曲库：/api/admin/music/tracks。
 */
import { computed, onMounted, ref } from 'vue'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import PlaylistDialog from '../../components/music/PlaylistDialog.vue'
import { confirmAsk } from '../../composables/useConfirm'

const playlists = ref([])
const tracks = ref([])
const state = ref('loading')
const note = ref('')
const openFor = ref(null)
const pick = ref('')
const dialog = ref({ open: false, mode: 'create', id: null, value: '' })

const load = async () => {
  const [p, t] = await Promise.all([api('/api/admin/music/playlists'), api('/api/admin/music/tracks?limit=500')])
  if (!p.ok) { state.value = 'error'; return }
  playlists.value = asList(p.data)
  tracks.value = t.ok ? asList(t.data) : []
  state.value = playlists.value.length ? 'ok' : 'empty'
}

const current = computed(() => playlists.value.find(p => p.id === openFor.value) || null)
const inIds = computed(() => new Set((current.value?.tracks || []).map(t => t.id)))
const candidates = computed(() => tracks.value.filter(t => !inIds.value.has(t.id)))
const fmt = s => {
  const n = Math.floor(Number(s) || 0)
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`
}

const openCreate = () => { dialog.value = { open: true, mode: 'create', id: null, value: '' } }
const openRename = p => { dialog.value = { open: true, mode: 'rename', id: p.id, value: p.name } }
const saveDialog = async name => {
  const r = dialog.value.mode === 'create'
    ? await api('/api/admin/music/playlists', { method: 'POST', body: JSON.stringify({ name }) })
    : await api('/api/admin/music/playlists/' + dialog.value.id, { method: 'PUT', body: JSON.stringify({ name }) })
  if (!r.ok) { note.value = errOf(r.data, '保存失败'); return }
  note.value = dialog.value.mode === 'create' ? '已创建。' : '已重命名。'
  dialog.value.open = false
  await load()
}

const removePlaylist = async p => {
  if (!(await confirmAsk({ title: '删除歌单', text: '只删除歌单本身，曲库中的歌曲不受影响。', detail: p.name, ok: '删除' }))) return
  const r = await api('/api/admin/music/playlists/' + p.id, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  if (openFor.value === p.id) openFor.value = null
  note.value = '已删除歌单。'
  await load()
}

const addTrack = async () => {
  if (!current.value || !pick.value) return
  const r = await api(`/api/admin/music/playlists/${current.value.id}/tracks`,
    { method: 'POST', body: JSON.stringify({ track_id: Number(pick.value) }) })
  if (!r.ok) { note.value = errOf(r.data, '添加失败'); return }
  pick.value = ''
  note.value = '已加入。'
  await load()
}
const removeTrack = async t => {
  if (!current.value) return
  const r = await api(`/api/admin/music/playlists/${current.value.id}/tracks/${t.id}`, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '移除失败'); return }
  note.value = '已移出。'
  await load()
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>歌单</h2><p class="hint">公开页只展示与播放；歌单在这里维护，删除歌单不会删除歌曲</p></div>
      <button type="button" class="g-btn--sm g-btn--primary" @click="openCreate">新建歌单</button>
    </header>

    <DataState :state="state" empty-text="还没有歌单，点右上新建。" @retry="load">
      <div class="toolbar"><span class="hint">{{ note }}</span></div>

      <ul class="rows">
        <li v-for="p in playlists" :key="p.id" class="row">
          <div class="row-main">
            <b>{{ p.name }}</b>
            <span class="hint">{{ p.count }} 首 · 创建于 {{ (p.created_at || '').slice(0, 10) }}</span>
          </div>
          <div class="row-ops">
            <button type="button" class="g-btn--sm" @click="openFor = openFor === p.id ? null : p.id">
              {{ openFor === p.id ? '收起' : '管理曲目' }}
            </button>
            <button type="button" class="g-btn--sm" @click="openRename(p)">重命名</button>
            <button type="button" class="danger g-btn--sm" @click="removePlaylist(p)">删除</button>
          </div>
        </li>
      </ul>

      <div v-if="current" class="card" style="margin-top: 14px;">
        <h3>「{{ current.name }}」的曲目</h3>
        <div class="toolbar" style="margin: 10px 0;">
          <select v-model="pick" class="g-btn--sm" aria-label="选择要加入的曲目">
            <option value="">选择曲目…</option>
            <option v-for="t in candidates" :key="t.id" :value="t.id">{{ t.title }} · {{ fmt(t.duration) }}</option>
          </select>
          <button type="button" class="g-btn--sm g-btn--primary" :disabled="!pick" @click="addTrack">加入歌单</button>
          <span class="hint">{{ candidates.length }} 首可加入</span>
        </div>
        <ul class="rows">
          <li v-for="t in current.tracks" :key="t.id" class="row">
            <div class="row-main">
              <b>{{ t.title }}</b>
              <span class="hint">{{ t.artist || '未知艺术家' }} · {{ fmt(t.duration) }}<template v-if="t.visibility !== 'public'"> · 私密曲目（公开页不显示）</template></span>
            </div>
            <div class="row-ops">
              <button type="button" class="danger g-btn--sm" @click="removeTrack(t)">移出</button>
            </div>
          </li>
          <li v-if="!current.tracks.length" class="hint" style="padding: 8px 2px;">这个歌单还没有曲目。</li>
        </ul>
      </div>
    </DataState>

    <PlaylistDialog :open="dialog.open" :value="dialog.value"
                    :title="dialog.mode === 'create' ? '新建歌单' : '重命名歌单'"
                    :confirm-text="dialog.mode === 'create' ? '创建' : '保存'"
                    @save="saveDialog" @close="dialog.open = false" />
  </section>
</template>
