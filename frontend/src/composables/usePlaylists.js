/**
 * usePlaylists —— 歌单与最近播放（localStorage 第一版）。
 *
 * 数据结构带版本号，后续迁到后端只需替换 read/write 的实现，页面与组件不受影响：
 *   { v: 1, items: [{ id, name, trackIds: [], createdAt }] }
 * 歌单只存曲目 id，删除歌单不会动到曲库本身。
 */
import { computed, ref, watch } from 'vue'

const KEY = 'ys-music-playlists-v1'
const RECENT_KEY = 'ys-music-recent-v1'
const SCHEMA = 1

const read = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch { return fallback }
}
const write = (key, value) => {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* 隐私模式忽略 */ }
}

const normalize = data => {
  const items = Array.isArray(data?.items) ? data.items : []
  return items
    .filter(p => p && typeof p.id === 'string' && typeof p.name === 'string')
    .map(p => ({ id: p.id, name: p.name, trackIds: Array.isArray(p.trackIds) ? p.trackIds.map(Number) : [], createdAt: p.createdAt || Date.now() }))
}

const playlists = ref(normalize(read(KEY, { v: SCHEMA, items: [] })))
const recent = ref((read(RECENT_KEY, []) || []).filter(x => x && Number.isFinite(x.id)))

watch(playlists, v => write(KEY, { v: SCHEMA, items: v }), { deep: true })
watch(recent, v => write(RECENT_KEY, v), { deep: true })

const uid = () => 'pl' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6)

const create = name => {
  const n = String(name || '').trim().slice(0, 40)
  if (!n) return null
  const p = { id: uid(), name: n, trackIds: [], createdAt: Date.now() }
  playlists.value = [...playlists.value, p]
  return p
}
const rename = (id, name) => {
  const n = String(name || '').trim().slice(0, 40)
  if (!n) return false
  playlists.value = playlists.value.map(p => (p.id === id ? { ...p, name: n } : p))
  return true
}
const remove = id => {
  playlists.value = playlists.value.filter(p => p.id !== id)
}
const addTrack = (id, trackId) => {
  playlists.value = playlists.value.map(p =>
    p.id === id && !p.trackIds.includes(Number(trackId))
      ? { ...p, trackIds: [...p.trackIds, Number(trackId)] } : p)
}
const removeTrack = (id, trackId) => {
  playlists.value = playlists.value.map(p =>
    p.id === id ? { ...p, trackIds: p.trackIds.filter(t => t !== Number(trackId)) } : p)
}
const get = id => playlists.value.find(p => p.id === id) || null

const pushRecent = trackId => {
  const id = Number(trackId)
  recent.value = [{ id, at: Date.now() }, ...recent.value.filter(x => x.id !== id)].slice(0, 24)
}

export const usePlaylists = () => ({
  playlists,
  recent,
  count: computed(() => playlists.value.length),
  create, rename, remove, addTrack, removeTrack, get, pushRecent,
})
