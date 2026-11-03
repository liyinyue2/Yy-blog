<script setup>
/** 左栏：音乐库 / 全部歌曲 / 最近播放 / 我的歌单 */
const props = defineProps({
  view: { type: String, default: 'all' },
  playlists: { type: Array, default: () => [] },
  counts: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select'])
const coverStyle = id => {
  const h = Math.abs(String(id).split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 31) % 360
  return { background: `linear-gradient(135deg, hsl(${h} 60% 60%), hsl(${(h + 50) % 360} 58% 44%))` }
}
</script>

<template>
  <aside class="ms-side">
    <div class="ms-brand">
      <b>音乐库</b>
      <span>Library · {{ counts.all || 0 }} 首曲目</span>
    </div>

    <nav class="ms-nav" aria-label="音乐库导航">
      <button type="button" class="ms-item" :class="{ 'is-on': view === 'liked' }" @click="emit('select', 'liked')">
        <span class="ico">♥</span>喜欢音乐
      </button>
      <button type="button" class="ms-item" :class="{ 'is-on': view === 'playlists' }" @click="emit('select', 'playlists')">
        <span class="ico">▦</span>我的歌单
      </button>
    </nav>

    <p class="ms-sep">我的歌单</p>
    <div class="ms-pls">
      <button v-for="p in playlists" :key="p.id" type="button" class="ms-pl"
              :class="{ 'is-on': view === 'playlist:' + p.id }" @click="emit('select', 'playlist:' + p.id)">
        <span class="dot" :style="coverStyle(p.id)"></span>
        <span class="nm">{{ p.name }}</span>
      </button>
    </div>

    <p class="ms-note">歌单由博主在数字空间里维护；这里只负责播放与展示。</p>
  </aside>
</template>
