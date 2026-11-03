<script setup>
/** 曲目列表：全部歌曲 / 最近播放 / 歌单详情共用。行内 ⋯ 可加入歌单或从歌单移除。 */
import { computed, ref } from 'vue'
import { usePlayer } from '../../composables/usePlayer'

const props = defineProps({
  tracks: { type: Array, default: () => [] },
  emptyText: { type: String, default: '这里还没有歌曲。' },
  playlists: { type: Array, default: () => [] },
  removable: { type: Boolean, default: false },
})
const emit = defineEmits(['play', 'add', 'remove'])

const player = usePlayer()
const menuFor = ref(null)

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
const toggleMenu = id => { menuFor.value = menuFor.value === id ? null : id }
const doAdd = (pid, t) => { emit('add', { playlistId: pid, track: t }); menuFor.value = null }
const doRemove = t => { emit('remove', t); menuFor.value = null }
const visiblePlaylists = computed(() => props.playlists)
</script>

<template>
  <div class="mt-list" @click="menuFor = null">
    <div v-if="!tracks.length" class="ms-empty">{{ emptyText }}</div>
    <template v-else>
      <div class="mt-head">
        <span>#</span><span></span><span>标题</span><span class="mt-album">专辑</span><span class="mt-dur">时长</span><span></span>
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
        <button type="button" class="mt-more" :aria-label="'更多操作：' + t.title"
                @click.stop="toggleMenu(t.id)">⋯</button>

        <div v-if="menuFor === t.id" class="mt-menu" @click.stop>
          <template v-if="visiblePlaylists.length">
            <p>添加到歌单</p>
            <button v-for="p in visiblePlaylists" :key="p.id" type="button" @click="doAdd(p.id, t)">
              {{ p.name }}
            </button>
          </template>
          <p v-else>还没有歌单</p>
          <button v-if="removable" type="button" class="danger" @click="doRemove(t)">从歌单移除</button>
        </div>
      </div>
    </template>
  </div>
</template>
