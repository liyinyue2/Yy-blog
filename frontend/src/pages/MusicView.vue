<script setup>
/**
 * MusicView —— 音乐中心（Apple Music 式悬浮玻璃面板）
 * 左栏音乐库 / 右栏内容 / 底部播放栏；歌单存 localStorage，播放走 /api/public/music/stream。
 */
import { computed, onMounted, ref } from 'vue'
import { usePlayer } from '../composables/usePlayer'
import { usePlaylists } from '../composables/usePlaylists'
import MusicSidebar from '../components/music/MusicSidebar.vue'
import TrackList from '../components/music/TrackList.vue'
import PlaylistGrid from '../components/music/PlaylistGrid.vue'
import PlayerBar from '../components/music/PlayerBar.vue'
import PlaylistDialog from '../components/music/PlaylistDialog.vue'

const tracks = ref([])
const state = ref('loading')
const view = ref('all')
const dialog = ref({ open: false, mode: 'create', id: null, value: '' })

const player = usePlayer()
const pl = usePlaylists()

const byId = computed(() => new Map(tracks.value.map(t => [t.id, t])))
const counts = computed(() => {
  const m = { all: tracks.value.length }
  for (const p of pl.playlists.value) m[p.id] = p.trackIds.filter(id => byId.value.has(id)).length
  return m
})
const recentTracks = computed(() => pl.recent.value.map(r => byId.value.get(r.id)).filter(Boolean))
const currentPlaylist = computed(() => (view.value.startsWith('playlist:') ? pl.get(view.value.slice(9)) : null))
const listTracks = computed(() => {
  if (view.value === 'recent') return recentTracks.value
  if (currentPlaylist.value) return currentPlaylist.value.trackIds.map(id => byId.value.get(id)).filter(Boolean)
  return tracks.value
})

const title = computed(() => {
  if (currentPlaylist.value) return currentPlaylist.value.name
  return { all: '全部歌曲', recent: '最近播放', playlists: '我的歌单' }[view.value] || '全部歌曲'
})
const subtitle = computed(() => {
  if (currentPlaylist.value) return `${listTracks.value.length} 首 · 歌单保存在本机`
  if (view.value === 'playlists') return `${pl.playlists.value.length} 个歌单`
  if (view.value === 'recent') return `${recentTracks.value.length} 首 · 按本机播放时间倒序`
  return `${tracks.value.length} 首公开曲目`
})
const emptyText = computed(() => {
  if (view.value === 'recent') return '还没有播放记录，先听一首。'
  if (view.value === 'playlists') return '还没有歌单，点右上新建一个。'
  if (currentPlaylist.value) return '这个歌单还是空的：在歌曲行的 ⋯ 里加入。'
  return '曲库还是空的——等博主上传第一首歌。'
})

const load = async () => {
  state.value = 'loading'
  try {
    const res = await fetch('/api/public/music/tracks')
    const data = await res.json()
    tracks.value = Array.isArray(data) ? data : (data.tracks || [])
    state.value = 'ok'
  } catch { state.value = 'error' }
}
const playTrack = t => {
  player.play(t, listTracks.value)
  pl.pushRecent(t.id)
}
const playAll = () => {
  if (!listTracks.value.length) return
  player.playQueue(listTracks.value)
  pl.pushRecent(listTracks.value[0].id)
}
const addToPlaylist = ({ playlistId, track }) => pl.addTrack(playlistId, track.id)
const removeFromPlaylist = t => {
  if (currentPlaylist.value) pl.removeTrack(currentPlaylist.value.id, t.id)
}
const openCreate = () => { dialog.value = { open: true, mode: 'create', id: null, value: '' } }
const openRename = () => {
  if (!currentPlaylist.value) return
  dialog.value = { open: true, mode: 'rename', id: currentPlaylist.value.id, value: currentPlaylist.value.name }
}
const saveDialog = name => {
  if (dialog.value.mode === 'create') {
    const p = pl.create(name)
    if (p) view.value = 'playlist:' + p.id
  } else {
    pl.rename(dialog.value.id, name)
  }
  dialog.value.open = false
}
const removePlaylist = () => {
  const p = currentPlaylist.value
  if (!p) return
  pl.remove(p.id)
  view.value = 'playlists'
}
onMounted(load)
</script>

<template>
  <main class="page-main music-page">
    <header class="page-head music-head">
      <p class="section-kicker">Music / 04</p>
      <h1>音乐</h1>
      <p class="page-desc">正在听的歌，和反复回放的那几首。</p>
    </header>

    <div class="music-shell">
      <MusicSidebar :view="view" :playlists="pl.playlists.value" :counts="counts"
                     @select="v => (view = v)" @create="openCreate" />

      <section class="ms-main">
        <div class="ms-head">
          <div>
            <h2>{{ title }}</h2>
            <p class="sub">{{ subtitle }}</p>
          </div>
          <div class="ms-actions">
            <template v-if="view === 'playlists'">
              <button type="button" class="g-btn--sm g-btn--primary" @click="openCreate">新建歌单</button>
            </template>
            <template v-else-if="currentPlaylist">
              <button type="button" class="g-btn--sm g-btn--primary" :disabled="!listTracks.length" @click="playAll">播放全部</button>
              <button type="button" class="g-btn--sm" @click="openRename">重命名</button>
              <button type="button" class="g-btn--sm danger" @click="removePlaylist">删除歌单</button>
            </template>
            <template v-else>
              <button type="button" class="g-btn--sm g-btn--primary" :disabled="!listTracks.length" @click="playAll">播放全部</button>
            </template>
          </div>
        </div>

        <div class="ms-body">
          <p v-if="state === 'loading'" class="ms-empty">正在加载…</p>
          <p v-else-if="state === 'error'" class="ms-empty">
            曲库加载失败。<button type="button" class="g-btn--sm" @click="load">重试</button>
          </p>

          <PlaylistGrid v-else-if="view === 'playlists'" :playlists="pl.playlists.value" :counts="counts"
                        @open="id => (view = 'playlist:' + id)" @create="openCreate" />

          <template v-else-if="currentPlaylist">
            <div class="pd-head">
              <span class="pd-cover" :style="{ background: 'linear-gradient(135deg, hsl(212 62% 58%), hsl(262 58% 44%))' }">
                {{ currentPlaylist.name.slice(0, 1) }}
              </span>
              <div class="pd-info">
                <h3>{{ currentPlaylist.name }}</h3>
                <p class="sub">{{ listTracks.length }} 首 · 创建于 {{ new Date(currentPlaylist.createdAt).toLocaleDateString('zh-CN') }}</p>
                <button type="button" class="g-btn--sm g-btn--primary" :disabled="!listTracks.length" @click="playAll">播放全部</button>
              </div>
            </div>
            <TrackList :tracks="listTracks" :empty-text="emptyText" :playlists="pl.playlists.value" removable
                       @play="playTrack" @add="addToPlaylist" @remove="removeFromPlaylist" />
          </template>

          <TrackList v-else :tracks="listTracks" :empty-text="emptyText" :playlists="pl.playlists.value"
                     @play="playTrack" @add="addToPlaylist" />
        </div>
      </section>
    </div>

    <PlayerBar />

    <PlaylistDialog :open="dialog.open" :value="dialog.value"
                    :title="dialog.mode === 'create' ? '新建歌单' : '重命名歌单'"
                    :confirm-text="dialog.mode === 'create' ? '创建' : '保存'"
                    @save="saveDialog" @close="dialog.open = false" />
  </main>
</template>
