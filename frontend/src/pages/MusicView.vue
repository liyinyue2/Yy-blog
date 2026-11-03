<script setup>
import { ref, onMounted } from 'vue'

const tracks = ref([])
const state = ref('loading')
const playingId = ref(null)
const audio = ref(null)

const load = async () => {
  state.value = 'loading'
  try {
    const res = await fetch('/api/public/music/tracks')
    const data = await res.json()
    tracks.value = Array.isArray(data) ? data : (data.tracks || [])
    state.value = 'ok'
  } catch { state.value = 'error' }
}

const play = t => {
  if (playingId.value === t.id) { audio.value.pause(); playingId.value = null; return }
  audio.value.src = `/api/public/music/stream/${t.id}`
  audio.value.play()
  playingId.value = t.id
}
onMounted(load)
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Music / 04</p>
      <h1>音乐</h1>
      <p class="page-desc">正在听的歌，和反复回放的那几首。</p>
    </header>
    <div class="msg-list article-list">
      <article
        v-for="t in tracks" :key="t.id"
        class="article-card track" :class="{ 'is-playing': playingId === t.id }"
        @click="play(t)"
      >
        <h3>{{ t.title }}</h3>
        <p>{{ t.artist || '未知艺术家' }}</p>
        <span class="card-meta">{{ playingId === t.id ? '▶ 播放中' : '点击播放' }}</span>
      </article>
      <p v-if="state === 'ok' && !tracks.length" class="list-empty">曲库还是空的——等博主上传第一首歌。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    </div>
    <audio ref="audio" @ended="playingId = null"></audio>
  </main>
</template>

<style scoped>
.track { cursor: pointer; }
.track.is-playing { border-color: var(--accent); }
</style>
