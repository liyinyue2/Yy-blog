<script setup>
/**
 * GlassNav — 顶部导航：磨砂玻璃条 + Liquid Glass 选中小球
 * 小球随手势拖动（GlassBall 内建 rubber-band 回弹 + fling 吸附）
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LiquidGlass from '../glass/LiquidGlass.vue'
import GlassBall from './GlassBall.vue'

const route = useRoute()
const router = useRouter()
const navEl = ref(null)
const ball = ref(null)

const navItems = [
  { label: '首页', to: '/' },
  { label: '文章', to: '/articles' },
  { label: '项目', to: '/projects' },
  { label: '留言', to: '/messages' },
  { label: '音乐', to: '/music' },
  { label: '关于', to: '/about' },
]

const current = computed(() => route.path)
const isActive = to => to === '/' ? route.path === '/' : route.path.startsWith(to)

/* 收集真实 DOM 用于小球定位（子组件 mounted 先于父组件，故在父 onMounted 填充） */
const itemEls = new Array(navItems.length)
const setItemEl = (el, i) => { if (el) itemEls[i] = el }
const ballItems = ref([])
onMounted(() => {
  ballItems.value = navItems.map((n, i) => ({ el: itemEls[i], value: n.to }))
})

const go = to => { if (route.path !== to) router.push(to) }
</script>

<template>
  <LiquidGlass :radius="18" :bevel="12" :scale="36" tag="nav" class="glass-nav-wrap" aria-label="博客主导航">
    <nav ref="navEl" class="glass-nav">
      <GlassBall
        ref="ball"
        :container="navEl"
        :items="ballItems"
        :active="current"
        @select="go"
      />
      <a
        v-for="(n, i) in navItems"
        :key="n.to"
        :ref="el => setItemEl(el, i)"
        class="nav-item"
        :class="{ 'is-active': isActive(n.to) }"
        :href="n.to"
        @click.prevent="go(n.to)"
        @mouseenter="ball?.hoverTo(i)"
      >{{ n.label }}</a>
    </nav>
  </LiquidGlass>
</template>

<style scoped>
.glass-nav-wrap {
  position: fixed; top: 14px; left: 0; right: 0;
  margin-inline: auto; width: fit-content;
  z-index: 40; padding: 0;
}
.glass-nav { padding: 10px 18px; }
/* iOS 底部 tab bar 模式：全宽玻璃贴底 + 安全区 */
@media (max-width: 760px) {
  .glass-nav-wrap {
    top: auto;
    bottom: calc(10px + env(safe-area-inset-bottom));
    left: 12px; right: 12px;
    margin-inline: 0; width: auto;
  }
  .glass-nav { justify-content: space-around; padding: 10px 8px; }
}
</style>
