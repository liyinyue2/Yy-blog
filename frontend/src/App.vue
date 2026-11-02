<script setup>
import GlassNav from './components/GlassNav.vue'
</script>

<template>
  <GlassNav />
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
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
