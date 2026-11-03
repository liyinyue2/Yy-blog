<script setup>
/**
 * 规划中页面 —— 目标结构里尚未实装的分区。
 * 每页说明「后端已具备什么 / 还缺什么 / 落在哪个阶段」，避免空壳占位。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const plan = computed(() => route.meta.plan || { label: '该功能', phase: '待定', has: [], todo: [] })
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div>
        <h2>{{ plan.label }}</h2>
        <p class="hint">目标结构中的第 {{ plan.phase }} 阶段，尚未实装。</p>
      </div>
      <span class="g-tag accent">{{ plan.phase }}</span>
    </header>

    <div class="card plan-block">
      <h3>后端已具备</h3>
      <ul><li v-for="(h, i) in plan.has" :key="i"><code>{{ h }}</code></li></ul>
      <h3 class="mt">还缺</h3>
      <ul><li v-for="(t, i) in plan.todo" :key="i">{{ t }}</li></ul>
    </div>
  </section>
</template>
