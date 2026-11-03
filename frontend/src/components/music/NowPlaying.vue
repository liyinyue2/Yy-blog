<script setup>
/**
 * NowPlaying —— 点开后的「正在播放」大页（类似网易云播放详情）。
 * 与底部播放栏共用 usePlayer 单例，状态完全同源。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { usePlayer } from '../../composables/usePlayer'

const emit = defineEmits(['close'])
const player = usePlayer()
const s = player.state
const queueEl = ref(null)

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
  <div class="np-overlay" data-ogui-design="liquid" data-ogui-appearance="light"
       role="dialog" aria-modal="true" aria-label="正在播放" @click.self="emit('close')">
    <div class="np-panel" data-ogui-design="liquid" data-ogui-appearance="light" data-ogui-glass="sheet">
      <header class="np-head">
        <span class="np-kicker">正在播放</span>
        <button type="button" class="np-close" aria-label="收起播放详情" @click="emit('close')">⌄</button>
      </header>

      <div class="np-body">
        <section class="np-main">
          <span v-if="s.current" class="np-cover" :style="coverStyle(s.current.id)" aria-hidden="true">
            {{ (s.current.title || '?').slice(0, 1) }}
          </span>
          <span v-else class="np-cover np-cover--empty" aria-hidden="true">♪</span>

          <h2>{{ s.current ? s.current.title : '未在播放' }}</h2>
          <p class="np-artist">{{ s.current ? (s.current.artist || '未知艺术家') : '从队列里选一首开始' }}</p>

          <div class="np-progress">
            <span>{{ fmt(s.time) }}</span>
            <input class="mp-range" type="range" min="0" :max="max || 1" step="0.1"
                   :value="s.time" :disabled="!s.current" aria-label="播放进度" @input="onSeek" />
            <span>{{ fmt(max) }}</span>
          </div>

          <div class="np-ctrl">
            <button type="button" class="mp-btn" aria-label="上一首" :disabled="!s.queue.length" @click="player.prev()">⏮</button>
            <button type="button" class="mp-btn play np-play" :aria-label="s.playing ? '暂停' : '播放'" @click="player.toggle()">
              {{ s.playing ? '❚❚' : '▶' }}
            </button>
            <button type="button" class="mp-btn" aria-label="下一首" :disabled="!s.queue.length" @click="player.next()">⏭</button>
          </div>

          <div class="np-vol">
            <span aria-hidden="true">🔈</span>
            <input class="mp-range" type="range" min="0" max="1" step="0.01"
                   :value="s.volume" aria-label="音量" @input="onVolume" />
          </div>
          <p v-if="s.error" class="mp-err">{{ s.error }}</p>
        </section>

        <aside class="np-queue">
          <h3>播放队列 <span class="hint">{{ s.queue.length }} 首</span></h3>
          <ul ref="queueEl">
            <li v-for="(t, i) in s.queue" :key="t.id">
              <button type="button" :class="{ 'is-on': s.current && s.current.id === t.id }"
                      @click="player.play(t, s.queue)">
                <span class="idx">{{ String(i + 1).padStart(2, '0') }}</span>
                <span class="ttl">{{ t.title }}</span>
                <span class="dur">{{ fmt(t.duration) }}</span>
              </button>
            </li>
            <li v-if="!s.queue.length" class="hint" style="padding: 14px 10px;">队列是空的，先去列表里点一首。</li>
          </ul>
        </aside>
      </div>
    </div>
  </div>
</template>
