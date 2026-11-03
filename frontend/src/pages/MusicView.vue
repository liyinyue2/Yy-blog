<script setup>
/**
 * MusicView —— 音乐中心（公开面只负责播放与展示）
 * 曲库来自 /api/public/music/tracks，歌单来自 /api/public/music/playlists（由后台维护）。
 */
import { computed, onMounted, ref } from 'vue'
import { usePlayer } from '../composables/usePlayer'
import MusicSidebar from '../components/music/MusicSidebar.vue'
import TrackList from '../components/music/TrackList.vue'
import PlaylistGrid from '../components/music/PlaylistGrid.vue'
import PlayerBar from '../components/music/PlayerBar.vue'

const tracks = ref([])
const playlists = ref([])
const state = ref('loading')
const view = ref('liked')

const player = usePlayer()

const currentPlaylist = computed(() =>
  view.value.startsWith('playlist:')
    ? playlists.value.find(p => 'playlist:' + p.id === view.value)
    : null)
const listTracks = computed(() => (currentPlaylist.value ? currentPlaylist.value.tracks || [] : tracks.value))
const counts = computed(() => ({
  ...Object.fromEntries(playlists.value.map(p => [p.id, p.count])),
  all: tracks.value.length,
}))
const plCover = id => {
  const h = Math.abs(String(id).split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 31) % 360
  return { background: `linear-gradient(145deg, hsl(${h} 62% 62%), hsl(${(h + 50) % 360} 58% 44%))` }
}

const title = computed(() => {
  if (currentPlaylist.value) return currentPlaylist.value.name
  return { liked: '喜欢音乐', playlists: '我的歌单' }[view.value] || '喜欢音乐'
})
const subtitle = computed(() => {
  if (currentPlaylist.value) return `${listTracks.value.length} 首`
  if (view.value === 'playlists') return `${playlists.value.length} 个歌单`
  return `${tracks.value.length} 首公开曲目`
})
const emptyText = computed(() => {
  if (view.value === 'playlists') return '博主还没有创建歌单。'
  if (currentPlaylist.value) return '这个歌单还没有公开曲目。'
  return '曲库还是空的——等博主上传第一首歌。'
})

const load = async () => {
  state.value = 'loading'
  try {
    const [t, p] = await Promise.all([
      fetch('/api/public/music/tracks').then(r => r.json()),
      fetch('/api/public/music/playlists').then(r => r.json()),
    ])
    tracks.value = Array.isArray(t) ? t : (t.tracks || [])
    playlists.value = Array.isArray(p) ? p : (p.items || [])
    state.value = 'ok'
  } catch { state.value = 'error' }
}
const playTrack = t => player.play(t, listTracks.value)
const playAll = () => {
  if (listTracks.value.length) player.playQueue(listTracks.value)
}
onMounted(load)
</script>

<template>
  <main class="page-main music-page" data-ogui-design="liquid" data-ogui-appearance="light">
    <div class="music-shell" data-ogui-design="liquid" data-ogui-appearance="light" data-ogui-glass="sheet">
      <MusicSidebar :view="view" :playlists="playlists" :counts="counts"
                     @select="v => (view = v)" />

      <section class="ms-main">
        <div class="ms-head">
          <div>
            <h2>{{ title }}</h2>
            <p class="sub">{{ subtitle }}</p>
          </div>
          <div class="ms-actions">
            <button v-if="view !== 'playlists'" type="button" class="g-btn--sm g-btn--primary"
                    :disabled="!listTracks.length || state !== 'ok'" @click="playAll">
              <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z" fill="currentColor" />
              </svg>播放全部
            </button>
          </div>
        </div>

        <div class="ms-body">
          <p v-if="state === 'loading'" class="ms-empty">正在加载…</p>
          <p v-else-if="state === 'error'" class="ms-empty">
            曲库加载失败。<button type="button" class="g-btn--sm" @click="load">重试</button>
          </p>

          <PlaylistGrid v-else-if="view === 'playlists'" :playlists="playlists" :counts="counts"
                        @open="id => (view = 'playlist:' + id)" />

          <template v-else-if="currentPlaylist">
            <div class="pd-head">
              <span class="pd-cover" :style="plCover(currentPlaylist.id)">
                {{ currentPlaylist.name.slice(0, 1) }}
              </span>
              <div class="pd-info">
                <h3>{{ currentPlaylist.name }}</h3>
                <p class="sub">{{ listTracks.length }} 首</p>
                <button type="button" class="g-btn--sm g-btn--primary" :disabled="!listTracks.length" @click="playAll">
                  <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                    <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z" fill="currentColor" />
                  </svg>播放全部
                </button>
              </div>
            </div>
            <TrackList :tracks="listTracks" :empty-text="emptyText" @play="playTrack" />
          </template>

          <TrackList v-else :tracks="listTracks" :empty-text="emptyText" @play="playTrack" />
        </div>
      </section>
    </div>

    <PlayerBar />
  </main>
</template>
