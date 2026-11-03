<script setup>
/** 左栏：音乐库 / 喜欢音乐 / 我的歌单 / 歌单列表 */
const props = defineProps({
  view: { type: String, default: 'all' },
  playlists: { type: Array, default: () => [] },
  counts: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select'])
const coverStyle = id => {
  const h = Math.abs(String(id).split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 31) % 360
  return { background: `linear-gradient(145deg, hsl(${h} 62% 62%), hsl(${(h + 50) % 360} 58% 44%))` }
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
        <span class="tico tico--heart" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path d="M12 20.3 4.9 13.4a4.6 4.6 0 0 1 0-6.6 4.8 4.8 0 0 1 6.7 0l.4.4.4-.4a4.8 4.8 0 0 1 6.7 0 4.6 4.6 0 0 1 0 6.6z"
                  fill="currentColor" />
          </svg>
        </span>喜欢音乐
      </button>
      <button type="button" class="ms-item" :class="{ 'is-on': view === 'playlists' }" @click="emit('select', 'playlists')">
        <span class="tico tico--grid" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <rect x="4" y="4" width="7" height="7" rx="2" fill="currentColor" />
            <rect x="13" y="4" width="7" height="7" rx="2" fill="currentColor" opacity=".55" />
            <rect x="4" y="13" width="7" height="7" rx="2" fill="currentColor" opacity=".55" />
            <rect x="13" y="13" width="7" height="7" rx="2" fill="currentColor" />
          </svg>
        </span>我的歌单
      </button>
    </nav>

    <p class="ms-sep">我的歌单</p>
    <div class="ms-pls">
      <button v-for="p in playlists" :key="p.id" type="button" class="ms-pl"
              :class="{ 'is-on': view === 'playlist:' + p.id }" @click="emit('select', 'playlist:' + p.id)">
        <span class="dot" :style="coverStyle(p.id)"></span>
        <span class="nm">{{ p.name }}</span>
        <span class="cnt">{{ counts[p.id] ?? 0 }}</span>
      </button>
    </div>

    <p class="ms-note">歌单由博主在数字空间里维护；这里只负责播放与展示。</p>
  </aside>
</template>
