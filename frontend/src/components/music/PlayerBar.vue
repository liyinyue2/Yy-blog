<script setup>
/** 底部播放器：与 usePlayer 单例共享状态（与列表的播放态同源） */
import { computed, ref } from 'vue'
import { usePlayer } from '../../composables/usePlayer'

const player = usePlayer()
const s = player.state
const queueOpen = ref(false)

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
</script>

<template>
  <div class="mp-bar" data-ogui-design="liquid" data-ogui-appearance="light" data-ogui-glass="sheet" role="region" aria-label="播放控制">
    <div class="mp-now">
      <span v-if="s.current" class="cover" :style="coverStyle(s.current.id)" aria-hidden="true">
        {{ (s.current.title || '?').slice(0, 1) }}
      </span>
      <span v-else class="cover" style="background: var(--gbtn-bg-hover); color: var(--ink-3); box-shadow: inset 0 0 0 1px var(--hairline);" aria-hidden="true">♪</span>
      <div class="meta">
        <b>{{ s.current ? s.current.title : '未在播放' }}</b>
        <span>{{ s.current ? (s.current.artist || '未知艺术家') : '从列表里选一首开始' }}</span>
      </div>
    </div>

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
      <button type="button" class="mp-btn" aria-label="播放队列" @click="queueOpen = !queueOpen">☰</button>
    </div>

    <div v-if="queueOpen" class="mp-queue">
      <header>播放队列 · {{ s.queue.length }} 首</header>
      <ul>
        <li v-for="(t, i) in s.queue" :key="t.id">
          <button type="button" :class="{ 'is-on': s.current && s.current.id === t.id }"
                  @click="player.play(t, s.queue); queueOpen = false">
            <span>{{ String(i + 1).padStart(2, '0') }}</span>
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ t.title }}</span>
            <span style="color: var(--ink-3);">{{ fmt(t.duration) }}</span>
          </button>
        </li>
        <li v-if="!s.queue.length" style="padding: 12px; font-size: 12px; color: var(--ink-3);">队列是空的。</li>
      </ul>
    </div>
  </div>
</template>
