<script setup>
/** 番茄钟页 —— 计时组件 + 专注记录 */
import { ref, computed, onMounted } from 'vue'
import { api, asList } from '../api/client'
import PomodoroCard from '../components/PomodoroCard.vue'

const rows = ref([])
const load = async () => {
  const r = await api('/api/space/pomodoro?limit=50')
  if (r.ok) rows.value = asList(r.data)
}
const today = computed(() => {
  const d = new Date().toISOString().slice(0, 10)
  return rows.value.filter(x => String(x.started_at || '').slice(0, 10) === d)
})
const totalMinutes = computed(() => rows.value.reduce((n, x) => n + (x.minutes || 0), 0))
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>番茄钟</h2><p class="hint">累计 {{ totalMinutes }} 分钟 · 今日 {{ today.length }} 段</p></div>
    </header>

    <div class="pomo-layout">
      <div class="card"><PomodoroCard @completed="load" /></div>
      <div class="card">
        <h3>专注记录</h3>
        <ul class="pomo-rows">
          <li v-for="x in rows.slice(0, 12)" :key="x.id">
            <b>{{ x.minutes }} 分钟</b>
            <span>{{ x.label || '未命名' }}</span>
            <em>{{ (x.started_at || '').slice(5, 16).replace('T', ' ') }}</em>
          </li>
          <li v-if="!rows.length" class="hint">还没有记录，先跑一个番茄。</li>
        </ul>
      </div>
    </div>
  </section>
</template>
