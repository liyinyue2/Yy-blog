/**
 * usePlayer —— 全站唯一的音频实例与播放状态（模块级单例）。
 * 页面切换时不重建 Audio，仅播放栏组件挂载/卸载，音乐不断。
 */
import { computed, reactive, readonly } from 'vue'

const state = reactive({
  queue: [],        // 当前播放队列（曲目对象数组）
  index: -1,        // 队列中的位置
  current: null,    // 当前曲目
  playing: false,
  time: 0,
  duration: 0,
  volume: 0.8,
  error: '',        // 无法播放时的原因（不伪造播放状态）
})

let audio = null

const ensureAudio = () => {
  if (audio) return audio
  audio = new Audio()
  audio.preload = 'metadata'
  audio.volume = state.volume

  audio.addEventListener('timeupdate', () => { state.time = audio.currentTime || 0 })
  audio.addEventListener('durationchange', () => { state.duration = Number.isFinite(audio.duration) ? audio.duration : 0 })
  audio.addEventListener('play', () => { state.playing = true })
  audio.addEventListener('pause', () => { state.playing = false })
  audio.addEventListener('ended', () => { state.playing = false; next(true) })
  audio.addEventListener('error', () => {
    state.playing = false
    state.error = '该曲目无法播放（音频地址不可用）'
  })
  return audio
}

const streamUrl = t => `/api/public/music/stream/${t.id}`

const load = async (track) => {
  const a = ensureAudio()
  state.error = ''
  state.current = track
  state.time = 0
  state.duration = Number(track.duration) || 0
  a.src = streamUrl(track)
  try {
    await a.play()
  } catch {
    /* 浏览器阻止自动播放或文件不可用：保持暂停态，由 UI 显示原因 */
    state.playing = false
  }
}

const play = async (track, list) => {
  const queue = Array.isArray(list) && list.length ? list : [track]
  state.queue = queue
  state.index = Math.max(0, queue.findIndex(t => t.id === track.id))
  await load(track)
}

const toggle = async () => {
  const a = ensureAudio()
  if (!state.current) {
    if (state.queue.length) await play(state.queue[0], state.queue)
    return
  }
  if (a.paused) {
    try { await a.play() } catch { state.error = '浏览器阻止了自动播放，请再点一次'; }
  } else {
    a.pause()
  }
}

const next = async (auto = false) => {
  if (!state.queue.length) return
  const n = state.index + 1
  if (n >= state.queue.length) {
    // 队列播完：自动结束时停在最后一首，手动点下一首回到第一首
    if (auto) return
    state.index = 0
  } else {
    state.index = n
  }
  await load(state.queue[state.index])
}

const prev = async () => {
  if (!state.queue.length) return
  if (state.time > 3) { seek(0); return }   // 播过 3 秒，上一首先回开头
  state.index = (state.index - 1 + state.queue.length) % state.queue.length
  await load(state.queue[state.index])
}

const seek = t => {
  if (!audio || !Number.isFinite(t)) return
  audio.currentTime = Math.max(0, Math.min(t, state.duration || t))
  state.time = audio.currentTime
}

const setVolume = v => {
  const vol = Math.max(0, Math.min(1, Number(v) || 0))
  state.volume = vol
  if (audio) audio.volume = vol
}

const toggleById = (track, list) => {
  if (state.current && state.current.id === track.id) return toggle()
  return play(track, list)
}

export const usePlayer = () => ({
  state: readonly(state),
  progress: computed(() => (state.duration ? state.time / state.duration : 0)),
  play, toggle, next, prev, seek, setVolume, toggleById,
  playQueue: list => (list.length ? play(list[0], list) : null),
  isCurrent: id => state.current && state.current.id === id,
})
