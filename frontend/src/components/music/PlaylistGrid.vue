<script setup>
/** 歌单网格：封面 / 名称 / 歌曲数量 + 新建入口 */
defineProps({
  playlists: { type: Array, default: () => [] },
  counts: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['open', 'create'])
const coverStyle = id => {
  const h = Math.abs(String(id).split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 31) % 360
  return { background: `linear-gradient(135deg, hsl(${h} 60% 60%), hsl(${(h + 50) % 360} 58% 44%))` }
}
</script>

<template>
  <div class="pl-grid">
    <button v-for="p in playlists" :key="p.id" type="button" class="pl-card" @click="emit('open', p.id)">
      <span class="cover" :style="coverStyle(p.id)">{{ p.name.slice(0, 1) }}</span>
      <b>{{ p.name }}</b>
      <span>{{ counts[p.id] || 0 }} 首</span>
    </button>
    <button type="button" class="pl-card" @click="emit('create')">
      <span class="cover" style="background: var(--gbtn-bg-hover); color: var(--ink-3); box-shadow: inset 0 0 0 1px var(--hairline);">＋</span>
      <b>新建歌单</b>
      <span>把喜欢的歌收在一起</span>
    </button>
  </div>
</template>
