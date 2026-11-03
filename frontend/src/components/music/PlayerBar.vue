<script setup>
/** 底部播放器：与 usePlayer 单例共享状态；点条形区或右侧按钮展开「正在播放」大页 */
import { computed, ref } from 'vue'
import { usePlayer } from '../../composables/usePlayer'
import NowPlaying from './NowPlaying.vue'

const player = usePlayer()
const s = player.state
const expanded = ref(false)

const fmt = v => {
  const n = Math.max(0, Math.floor(Number(v) || 0))
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`
}
const max = computed(() => s.duration || Number(s.current && s.current.duration) || 0)
const coverStyle = id => {
  const h = Math.abs(Number(id) * 47) % 360
  return { background: `linear-gradient(135deg, hsl(${h} 62% 58%), hsl(${(h + 48) % 360} 60% 42%))` }
}
const onSeek = e => player.seek(Number(e.target.value))
const onVolume = e => player.setVolume(Number(e.target.value))
const open = () => { if (s.current || s.queue.length) expanded.value = true }
</script>

<template>
  <div class="mp-bar" data-ogui-design="liquid" data-ogui-appearance="light" data-ogui-glass="sheet" role="region" aria-label="播放控制">
    <button type="button" class="mp-now" aria-label="展开播放详情" @click="open">
      <span v-if="s.current" class="cover" :style="coverStyle(s.current.id)" aria-hidden="true">
        {{ (s.current.title || '?').slice(0, 1) }}
      </span>
      <span v-else class="cover" style="background: var(--gbtn-bg-hover); color: var(--ink-3); box-shadow: inset 0 0 0 1px var(--hairline);" aria-hidden="true">♪</span>
      <span class="meta">
        <b>{{ s.current ? s.current.title : '未在播放' }}</b>
        <span>{{ s.current ? (s.current.artist || '未知艺术家') : '从列表里选一首开始' }}</span>
      </span>
      <span class="mp-up" aria-hidden="true">⌃</span>
    </button>

    <div class="mp-mid">
      <div class="mp-ctrl">
        <button type="button" class="mp-btn" aria-label="上一首" :disabled="!s.queue.length" @click="player.prev()">⏮</button>
        <button type="button" class="mp-btn play" :aria-label="s.playing ? '暂停' : '播放'" @click="player.toggle()">
          {{ s.playing ? '❚❚' : '▶' }}
        </button>
        <button type="button" class="mp-btn" aria-label="下一首" :disabled="!s.queue.length" @click="player.next()">⏭</button>
      </div>
      <div class="mp-time">
        <span>{{ fmt(s.time) }}</span>
        <input class="mp-range" type="range" min="0" :max="max || 1" step="0.1"
               :value="s.time" :disabled="!s.current" aria-label="播放进度" @input="onSeek" />
        <span>{{ fmt(max) }}</span>
      </div>
      <p v-if="s.error" class="mp-err">{{ s.error }}</p>
    </div>

    <div class="mp-right">
      <span aria-hidden="true" style="color: var(--ink-3); font-size: 13px;">🔈</span>
      <input class="mp-range vol" type="range" min="0" max="1" step="0.01"
             :value="s.volume" aria-label="音量" @input="onVolume" />
      <button type="button" class="mp-btn" aria-label="播放队列" @click="open">☰</button>
    </div>

    <Teleport to="body">
      <NowPlaying v-if="expanded" @close="expanded = false" />
    </Teleport>
  </div>
</template>
