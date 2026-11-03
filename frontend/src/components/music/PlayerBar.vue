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
const pct = computed(() => (!max.value ? 0 : Math.min(100, (s.time / max.value) * 100)))
const volPct = computed(() => Math.min(100, Math.max(0, s.volume * 100)))
const coverStyle = id => {
  const h = (Math.abs(Number(id) * 47) % 360) || 210
  return {
    background: `linear-gradient(145deg, hsl(${h} 70% 64%), hsl(${(h + 40) % 360} 66% 47%) 55%, hsl(${(h + 78) % 360} 60% 36%))`,
  }
}
const onSeek = e => player.seek(Number(e.target.value))
const onVolume = e => player.setVolume(Number(e.target.value))
const open = () => { if (s.current || s.queue.length) expanded.value = true }
</script>

<template>
  <div class="mp-bar" data-ogui-design="liquid" data-ogui-appearance="light" data-ogui-glass="sheet" role="region" aria-label="播放控制">
    <input class="mp-edge" type="range" min="0" :max="max || 1" step="0.1"
           :value="s.time" :disabled="!s.current" aria-label="播放进度"
           :style="{ '--p': pct + '%' }" @input="onSeek" />

    <button type="button" class="mp-now" aria-label="展开播放详情" @click="open">
      <span v-if="s.current" class="cover" :style="coverStyle(s.current.id)" aria-hidden="true">
        {{ (s.current.title || '?').slice(0, 1) }}
      </span>
      <span v-else class="cover" style="background: var(--gbtn-bg-hover); color: var(--ink-3); box-shadow: inset 0 0 0 1px var(--hairline);" aria-hidden="true">♪</span>
      <span class="meta">
        <b>{{ s.current ? s.current.title : '未在播放' }}</b>
        <span :class="{ 'is-err': s.error }">
          {{ s.error || (s.current ? (s.current.artist || '未知艺术家') : '从列表里选一首开始') }}
        </span>
      </span>
      <span class="mp-up" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path d="M6 14.5 12 9l6 5.5" fill="none" stroke="currentColor" stroke-width="2.2"
                stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
    </button>

    <div class="mp-ctrl">
      <button type="button" class="mp-btn" aria-label="上一首" :disabled="!s.queue.length" @click="player.prev()">
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <path d="M18.5 6.3v11.4c0 .8-.9 1.3-1.6.9l-8.6-5.7a1 1 0 0 1 0-1.7l8.6-5.7c.7-.5 1.6 0 1.6.8z"
                fill="currentColor" />
          <rect x="5" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor" />
        </svg>
      </button>
      <button type="button" class="mp-btn play" :aria-label="s.playing ? '暂停' : '播放'" @click="player.toggle()">
        <svg v-if="s.playing" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <rect x="7.4" y="5" width="3.5" height="14" rx="1.75" fill="currentColor" />
          <rect x="13.1" y="5" width="3.5" height="14" rx="1.75" fill="currentColor" />
        </svg>
        <svg v-else viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z"
                fill="currentColor" />
        </svg>
      </button>
      <button type="button" class="mp-btn" aria-label="下一首" :disabled="!s.queue.length" @click="player.next()">
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <path d="M5.5 6.3v11.4c0 .8.9 1.3 1.6.9l8.6-5.7a1 1 0 0 0 0-1.7L7.1 5.5c-.7-.5-1.6 0-1.6.8z"
                fill="currentColor" />
          <rect x="16.6" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor" />
        </svg>
      </button>
    </div>

    <div class="mp-right">
      <span class="mp-time">{{ fmt(s.time) }} / {{ fmt(max) }}</span>
      <span class="mp-vol" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="15" height="15">
          <path d="M4 9.5v5c0 .55.45 1 1 1h2.6l3.6 3c.66.55 1.8.08 1.8-.82V6.32c0-.9-1.14-1.37-1.8-.82l-3.6 3H5c-.55 0-1 .45-1 1z"
                fill="currentColor" />
          <path d="M16.3 8.7a4.7 4.7 0 0 1 0 6.6M18.9 6.1a8.4 8.4 0 0 1 0 11.8" fill="none"
                stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
      </span>
      <input class="mp-range vol" type="range" min="0" max="1" step="0.01"
             :value="s.volume" aria-label="音量"
             :style="{ '--p': volPct + '%' }" @input="onVolume" />
      <button type="button" class="mp-btn" aria-label="播放队列" @click="open">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path d="M4 7h11M4 12h11M4 17h7" fill="none" stroke="currentColor" stroke-width="1.8"
                stroke-linecap="round" />
          <circle cx="19" cy="7" r="1.4" fill="currentColor" />
          <circle cx="19" cy="12" r="1.4" fill="currentColor" />
          <circle cx="19" cy="17" r="1.4" fill="currentColor" />
        </svg>
      </button>
    </div>

    <Teleport to="body">
      <NowPlaying v-if="expanded" @close="expanded = false" />
    </Teleport>
  </div>
</template>
