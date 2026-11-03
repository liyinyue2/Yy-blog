<script setup>
/**
 * NowPlaying —— 点开后的「正在播放」沉浸页（类似网易云播放详情）。
 * 与底部播放栏共用 usePlayer 单例，状态完全同源；配色由当前曲目派生。
 */
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { usePlayer } from '../../composables/usePlayer'

const emit = defineEmits(['close'])
const player = usePlayer()
const s = player.state

const fmt = v => {
  const n = Math.max(0, Math.floor(Number(v) || 0))
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`
}
const hueOf = id => (Math.abs(Number(id) * 47) % 360) || 210
const hue = computed(() => hueOf(s.current && s.current.id))
const max = computed(() => s.duration || Number(s.current && s.current.duration) || 0)
const pct = computed(() => (!max.value ? 0 : Math.min(100, (s.time / max.value) * 100)))
const volumePct = computed(() => Math.min(100, Math.max(0, s.volume * 100)))
const initial = computed(() => ((s.current && s.current.title) || '?').trim().slice(0, 1))

const trackCover = id => {
  const h = hueOf(id)
  return {
    background: `linear-gradient(145deg, hsl(${h} 70% 64%), hsl(${(h + 40) % 360} 66% 47%) 55%, hsl(${(h + 78) % 360} 60% 36%))`,
  }
}
const coverStyle = computed(() => trackCover(s.current && s.current.id))
const backdropStyle = computed(() => {
  const h = hue.value
  const h2 = (h + 52) % 360
  return {
    '--np-h': h,
    background: [
      `radial-gradient(120% 90% at 16% 4%, hsl(${h} 62% 46% / .62), transparent 58%)`,
      `radial-gradient(90% 80% at 88% 96%, hsl(${h2} 58% 40% / .55), transparent 62%)`,
      'linear-gradient(168deg, #12161f 0%, #0a0d13 58%, #080a0f 100%)',
    ].join(','),
  }
})

const onSeek = e => player.seek(Number(e.target.value))
const onVolume = e => player.setVolume(Number(e.target.value))
const onKey = e => { if (e.key === 'Escape') emit('close') }

onMounted(() => {
  document.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="np-overlay" :style="backdropStyle"
       role="dialog" aria-modal="true" aria-label="正在播放" @click.self="emit('close')">
    <div class="np-panel">
      <header class="np-head">
        <button type="button" class="np-close" aria-label="收起播放详情" @click="emit('close')">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M6 9.5 12 15l6-5.5" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <span class="np-kicker">正在播放</span>
        <span class="np-count">队列 · {{ s.queue.length }} 首</span>
      </header>

      <div class="np-body">
        <div class="np-art">
          <span class="np-glow" :style="coverStyle" aria-hidden="true"></span>
          <span class="np-cover" :class="{ 'is-paused': !s.playing }" :style="s.current ? coverStyle : null"
                aria-hidden="true">
            <template v-if="s.current">{{ initial }}</template>
            <svg v-else viewBox="0 0 24 24" width="44" height="44">
              <path d="M9 18V6l10-2v12" fill="none" stroke="currentColor" stroke-width="1.6"
                    stroke-linecap="round" stroke-linejoin="round" />
              <circle cx="6.5" cy="18" r="2.5" fill="currentColor" />
              <circle cx="16.5" cy="16" r="2.5" fill="currentColor" />
            </svg>
            <span class="np-cover__sheen" aria-hidden="true"></span>
          </span>
        </div>

        <div class="np-side">
          <div class="np-meta">
            <h2>{{ s.current ? s.current.title : '未在播放' }}</h2>
            <p>
              {{ s.current ? (s.current.artist || '未知艺术家') : '从队列里选一首开始' }}
              <template v-if="s.current && s.current.album"> · {{ s.current.album }}</template>
            </p>
          </div>

          <div class="np-deck">
            <div class="np-progress">
              <span class="np-t">{{ fmt(s.time) }}</span>
              <input class="np-range" type="range" min="0" :max="max || 1" step="0.1"
                     :value="s.time" :disabled="!s.current" aria-label="播放进度"
                     :style="{ '--p': pct + '%' }" @input="onSeek" />
              <span class="np-t">{{ fmt(max) }}</span>
            </div>

            <div class="np-ctrl">
              <button type="button" class="np-step" aria-label="上一首" :disabled="!s.queue.length"
                      @click="player.prev()">
                <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                  <path d="M18.5 6.3v11.4c0 .8-.9 1.3-1.6.9l-8.6-5.7a1 1 0 0 1 0-1.7l8.6-5.7c.7-.5 1.6 0 1.6.8z"
                        fill="currentColor" />
                  <rect x="5" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor" />
                </svg>
              </button>

              <button type="button" class="np-play" :aria-label="s.playing ? '暂停' : '播放'" @click="player.toggle()">
                <svg v-if="s.playing" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
                  <rect x="7.4" y="5" width="3.5" height="14" rx="1.75" fill="currentColor" />
                  <rect x="13.1" y="5" width="3.5" height="14" rx="1.75" fill="currentColor" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
                  <path d="M8.4 5.3c0-.9 1-1.5 1.8-1l9.1 5.9c.7.5.7 1.5 0 2l-9.1 5.9c-.8.5-1.8-.1-1.8-1z"
                        fill="currentColor" />
                </svg>
              </button>

              <button type="button" class="np-step" aria-label="下一首" :disabled="!s.queue.length"
                      @click="player.next()">
                <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                  <path d="M5.5 6.3v11.4c0 .8.9 1.3 1.6.9l8.6-5.7a1 1 0 0 0 0-1.7L7.1 5.5c-.7-.5-1.6 0-1.6.8z"
                        fill="currentColor" />
                  <rect x="16.6" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor" />
                </svg>
              </button>
            </div>

            <div class="np-vol">
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path d="M4 9.5v5c0 .55.45 1 1 1h2.6l3.6 3c.66.55 1.8.08 1.8-.82V6.32c0-.9-1.14-1.37-1.8-.82l-3.6 3H5c-.55 0-1 .45-1 1z"
                      fill="currentColor" />
                <path d="M16.3 8.7a4.7 4.7 0 0 1 0 6.6M18.9 6.1a8.4 8.4 0 0 1 0 11.8" fill="none"
                      stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
              </svg>
              <input class="np-range np-range--vol" type="range" min="0" max="1" step="0.01"
                     :value="s.volume" aria-label="音量"
                     :style="{ '--p': volumePct + '%' }" @input="onVolume" />
            </div>

            <p v-if="s.error" class="np-err">{{ s.error }}</p>
          </div>

          <aside class="np-queue">
            <header class="np-queue__head">
              <h3>接下来播放</h3>
              <span>{{ s.queue.length }} 首</span>
            </header>
            <ul>
              <li v-for="(t, i) in s.queue" :key="t.id">
                <button type="button" :class="{ 'is-on': s.current && s.current.id === t.id }"
                        @click="player.play(t, s.queue)">
                  <span class="np-q-idx">
                    <span v-if="s.current && s.current.id === t.id" class="np-eq" :class="{ 'is-paused': !s.playing }"
                          aria-hidden="true"><i></i><i></i><i></i></span>
                    <template v-else>{{ String(i + 1).padStart(2, '0') }}</template>
                  </span>
                  <span class="np-q-cover" :style="trackCover(t.id)" aria-hidden="true">{{ (t.title || '?').trim().slice(0, 1) }}</span>
                  <span class="np-q-meta">
                    <b>{{ t.title }}</b>
                    <span>{{ t.artist || '未知艺术家' }}</span>
                  </span>
                  <span class="np-q-dur">{{ fmt(t.duration) }}</span>
                </button>
              </li>
              <li v-if="!s.queue.length" class="np-q-empty">队列是空的，去列表里点一首开始播放。</li>
            </ul>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>
