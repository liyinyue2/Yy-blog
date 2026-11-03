<script setup>
/** 曲目列表：全部歌曲 / 最近播放 / 歌单详情共用。行内 ⋯ 可加入歌单或从歌单移除。 */
import { usePlayer } from '../../composables/usePlayer'

const props = defineProps({
  tracks: { type: Array, default: () => [] },
  emptyText: { type: String, default: '这里还没有歌曲。' },
})

const player = usePlayer()

const initial = t => (t.title || '?').trim().slice(0, 1).toUpperCase()
const fmt = s => {
  const n = Number(s) || 0
  return `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, '0')}`
}
const coverStyle = id => {
  const h = Math.abs(Number(id) * 47) % 360
  return { background: `linear-gradient(135deg, hsl(${h} 62% 58%), hsl(${(h + 48) % 360} 60% 42%))` }
}
const isOn = t => player.state.current && player.state.current.id === t.id && player.state.playing

</script>

<template>
  <div class="mt-list">
    <div v-if="!tracks.length" class="ms-empty">{{ emptyText }}</div>
    <template v-else>
      <div class="mt-head">
        <span>#</span><span></span><span>标题</span><span class="mt-album">专辑</span><span class="mt-dur">时长</span>
      </div>
      <div v-for="(t, i) in tracks" :key="t.id" class="mt-row" :class="{ 'is-on': isOn(t) }"
           @click="$emit('play', t)">
        <span class="mt-idx">
          <span v-if="isOn(t)" class="mt-eq" aria-hidden="true"><i></i><i></i><i></i></span>
          <template v-else>{{ i + 1 }}</template>
        </span>
        <span class="mt-cover" :style="coverStyle(t.id)" aria-hidden="true">{{ initial(t) }}</span>
        <div class="mt-meta">
          <b>{{ t.title }}</b>
          <span>{{ t.artist || '未知艺术家' }}</span>
        </div>
        <span class="mt-album">{{ t.album || '—' }}</span>
        <span class="mt-dur">{{ fmt(t.duration) }}</span>
      </div>
    </template>
  </div>
</template>
