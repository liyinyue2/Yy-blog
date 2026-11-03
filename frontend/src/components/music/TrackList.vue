<script setup>
/** 曲目列表：全部歌曲 / 歌单详情共用。行内点击即播放，悬停显示播放提示。 */
import { usePlayer } from '../../composables/usePlayer'

const props = defineProps({
  tracks: { type: Array, default: () => [] },
  emptyText: { type: String, default: '这里还没有歌曲。' },
})

const player = usePlayer()

const hueOf = id => (Math.abs(Number(id) * 47) % 360) || 210
const initial = t => (t.title || '?').trim().slice(0, 1).toUpperCase()
const fmt = s => {
  const n = Number(s) || 0
  return `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, '0')}`
}
const coverStyle = id => {
  const h = hueOf(id)
  return {
    background: `linear-gradient(145deg, hsl(${h} 70% 64%), hsl(${(h + 40) % 360} 66% 47%) 55%, hsl(${(h + 78) % 360} 60% 36%))`,
  }
}
const isOn = t => player.state.current && player.state.current.id === t.id && player.state.playing
</script>

<template>
  <div class="mt-list">
    <div v-if="!tracks.length" class="ms-empty">{{ emptyText }}</div>
    <template v-else>
      <div class="mt-head">
        <span class="h-idx">#</span><span class="h-cover"></span><span class="h-title">标题</span><span class="mt-album">专辑</span><span class="mt-dur">时长</span>
      </div>
      <div v-for="(t, i) in tracks" :key="t.id" class="mt-row" :class="{ 'is-on': isOn(t) }"
           :style="{ '--rh': hueOf(t.id) }"
           @click="$emit('play', t)">
        <span class="mt-idx">
          <span v-if="isOn(t)" class="mt-eq" aria-hidden="true"><i></i><i></i><i></i></span>
          <template v-else>
            <span class="num">{{ i + 1 }}</span>
            <svg class="hov" viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">
              <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z"
                    fill="currentColor" />
            </svg>
          </template>
        </span>
        <span class="mt-cover" :style="coverStyle(t.id)" aria-hidden="true">
          <span class="glyph">{{ initial(t) }}</span>
          <svg class="mt-cover__play" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z"
                  fill="currentColor" />
          </svg>
        </span>
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
