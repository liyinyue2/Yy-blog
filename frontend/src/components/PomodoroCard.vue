<script setup>
/**
 * PomodoroCard —— 番茄钟（25 专注 / 5 休息），完成一段专注后写入 /api/space/pomodoro
 */
import { ref, computed, onBeforeUnmount } from 'vue'
import { api, errOf } from '../api/client'

const props = defineProps({
  focusMinutes: { type: Number, default: 25 },
  restMinutes: { type: Number, default: 5 },
})
const emit = defineEmits(['completed'])

const FOCUS = props.focusMinutes * 60
const REST = props.restMinutes * 60
const mode = ref('focus')
const left = ref(FOCUS)
const running = ref(false)
const note = ref('')
let tick = null

const fmt = s => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
const label = computed(() => (mode.value === 'focus' ? '专注' : '休息'))
const progress = computed(() => {
  const total = mode.value === 'focus' ? FOCUS : REST
  return Math.round((1 - left.value / total) * 100)
})

const pause = () => { running.value = false; clearInterval(tick) }
const start = () => {
  if (running.value) { pause(); return }
  running.value = true
  tick = setInterval(() => {
    left.value -= 1
    if (left.value <= 0) finish()
  }, 1000)
}
const reset = () => { pause(); left.value = mode.value === 'focus' ? FOCUS : REST }
const finish = async () => {
  pause()
  if (mode.value === 'focus') {
    const r = await api('/api/space/pomodoro', {
      method: 'POST',
      body: JSON.stringify({ label: '工作台番茄钟', minutes: props.focusMinutes, completed: true }),
    })
    if (!r.ok) note.value = errOf(r.data, '本次专注未记录到服务端')
    mode.value = 'rest'; left.value = REST
    emit('completed', props.focusMinutes)
  } else {
    mode.value = 'focus'; left.value = FOCUS
  }
}
onBeforeUnmount(() => clearInterval(tick))
</script>

<template>
  <div class="pomodoro">
    <div class="pomo-ring" :style="{ '--pomo': progress + '%' }">
      <b>{{ fmt(left) }}</b>
      <span>{{ label }}</span>
    </div>
    <div class="timer-ops">
      <button type="button" class="g-btn--primary" @click="start">{{ running ? '暂停' : '开始' }}</button>
      <button type="button" @click="reset">重置</button>
    </div>
    <p v-if="note" class="hint">{{ note }}</p>
  </div>
</template>
