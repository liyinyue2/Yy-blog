<script setup>
/**
 * GlassNav — 顶部导航：折射玻璃条 + 选中项白玻璃小球
 * 小球由 CSS 定位在选中项自身，不依赖 JS 测量，因此不会有位置偏移或拖拽重影。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LiquidGlass from '../glass/LiquidGlass.vue'
import { useSettings } from '../composables/useSettings'
import { vSlideBall } from '../directives/slideBall'

const { siteName } = useSettings()
const route = useRoute()
const router = useRouter()

const navItems = [
  { label: '首页', to: '/' },
  { label: '文章', to: '/articles' },
  { label: '资源库', to: '/library' },
  { label: '留言', to: '/messages' },
  { label: '音乐', to: '/music' },
  { label: '关于', to: '/about' },
]

/* 文章详情页 /post/xxx 归属「文章」，否则阅读时导航没有任何选中项 */
const isActive = to => to === '/'
  ? route.path === '/'
  : route.path.startsWith(to) || (to === '/articles' && route.path.startsWith('/post/'))
const go = to => { if (route.path !== to) router.push(to) }
</script>

<template>
  <LiquidGlass :radius="18" :bevel="12" :scale="36" tag="nav" class="glass-nav-wrap" aria-label="博客主导航">
    <nav class="glass-nav" v-slide-ball="{ active: '.is-active' }">
      <a class="brand" href="/" @click.prevent="go('/')" :aria-label="siteName + ' 首页'">
        <svg viewBox="0 0 16 18" aria-hidden="true"><path fill="none" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" d="M3.2 1.8Q6.4 5.4 8 8.6M12.8 1.8Q9.6 5.4 8 8.6Q8.35 13 8 16.4"/></svg>
        <span>{{ siteName }}</span>
      </a>
      <router-link
        v-for="n in navItems" :key="n.to"
        class="nav-item" :to="n.to" custom v-slot="{ navigate }"
      >
        <a :class="{ 'is-active': isActive(n.to) }" :href="n.to" @click.prevent="navigate()">{{ n.label }}</a>
      </router-link>
    </nav>
  </LiquidGlass>
</template>

<style scoped>
.glass-nav-wrap {
  position: fixed; top: 14px; left: 0; right: 0;
  margin-inline: auto; width: fit-content;
  z-index: 40; padding: 0;
}
.brand {
  display: inline-flex; align-items: center; gap: 8px;
  margin-right: 6px; color: var(--ink);
  font-size: 15px; font-weight: 600; letter-spacing: -.01em; white-space: nowrap;
}
.brand svg { width: 16px; height: 18px; fill: none; stroke: currentColor; }
/* 手机底部 tab bar 不放 brand（纯导航项） */
@media (max-width: 760px) {
  .brand { display: none; }
  .glass-nav-wrap {
    top: auto;
    bottom: calc(10px + env(safe-area-inset-bottom));
    left: 12px; right: 12px;
    margin-inline: 0; width: auto;
  }
}
</style>
