<script setup>
import { computed, onBeforeUnmount, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import GlassNav from './components/GlassNav.vue'
import { useSettings, loadSettings } from './composables/useSettings'

const route = useRoute()
const { siteName } = useSettings()
loadSettings()

/* 公开导航只在博客面出现；数字空间自带侧栏 */
const showPublicNav = computed(() =>
  !route.path.startsWith('/space') && !route.path.startsWith('/yy-AviuuP3r'))

/* Vue 的 <transition> 离场走双 requestAnimationFrame，标签页不可见时 rAF 不推进，
   out-in 会永远等不到结束回调而卡在旧页面（改 duration 或空 name 都救不了）。
   因此仅在页面可见时套过渡，不可见时直接换组件。 */
const useTransition = ref(!document.hidden)
const syncTransition = () => { useTransition.value = !document.hidden }
document.addEventListener('visibilitychange', syncTransition)
onBeforeUnmount(() => document.removeEventListener('visibilitychange', syncTransition))

watchEffect(() => { document.title = `${siteName.value} — 记录思考，分享创造` })
</script>

<template>
  <GlassNav v-if="showPublicNav" />
  <router-view v-slot="{ Component }">
    <component :is="Component" v-if="!useTransition" />
    <transition v-else name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
#app { min-height: 100%; }
/* 路由切换过渡 */
.page-enter-active, .page-leave-active { transition: opacity var(--t-base) var(--ease), transform var(--t-base) var(--ease); }
.page-enter-from { opacity: 0; transform: translateY(12px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
