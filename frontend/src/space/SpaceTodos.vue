<script setup>
/** 待办事项 —— /api/workspace/todos（content / done / due / priority） */
import { ref, computed, onMounted } from 'vue'
import { api, asList, errOf } from '../api/client'
import { vSlideBall } from '../directives/slideBall'

const items = ref([])
const text = ref('')
const due = ref('')
const priority = ref(0)
const filter = ref('all')
const note = ref('')
const loading = ref(true)

const load = async () => {
  const r = await api('/api/workspace/todos?limit=100')
  if (r.ok) items.value = asList(r.data)
  loading.value = false
}
const shown = computed(() => filter.value === 'all' ? items.value
  : filter.value === 'open' ? items.value.filter(t => !t.done)
  : items.value.filter(t => t.done))

const add = async () => {
  const content = text.value.trim()
  if (!content) { note.value = '先写点什么。'; return }
  const r = await api('/api/workspace/todos', {
    method: 'POST', body: JSON.stringify({ content, done: false, due: due.value, priority: priority.value }),
  })
  if (r.ok) { text.value = ''; due.value = ''; priority.value = 0; note.value = ''; load() }
  else note.value = errOf(r.data, '添加失败')
}
const toggle = async t => {
  await api('/api/workspace/todos/' + t.id, {
    method: 'PUT', body: JSON.stringify({ content: t.content, done: !t.done, due: t.due || '', priority: t.priority || 0 }),
  })
  load()
}
const del = async t => {
  await api('/api/workspace/todos/' + t.id, { method: 'DELETE' })
  load()
}
const overdue = t => t.due && !t.done && t.due < new Date().toISOString().slice(0, 10)
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>待办事项</h2><p class="hint">未完成 {{ items.filter(t => !t.done).length }} 项 · 共 {{ items.length }} 项</p></div>
      <div class="seg" v-slide-ball>
        <button type="button" class="chip" :class="{ 'is-active': filter === 'all' }" @click="filter = 'all'">全部</button>
        <button type="button" class="chip" :class="{ 'is-active': filter === 'open' }" @click="filter = 'open'">未完成</button>
        <button type="button" class="chip" :class="{ 'is-active': filter === 'done' }" @click="filter = 'done'">已完成</button>
      </div>
    </header>

    <form class="card add-row" @submit.prevent="add">
      <input v-model="text" placeholder="要做什么？" maxlength="500" />
      <input v-model="due" type="date" aria-label="截止日期" />
      <select v-model.number="priority" aria-label="优先级">
        <option :value="0">普通</option><option :value="1">重要</option><option :value="2">紧急</option>
      </select>
      <button type="submit" class="g-btn--primary">添加</button>
      <span v-if="note" class="hint">{{ note }}</span>
    </form>

    <ul class="card todo-full">
      <li v-for="t in shown" :key="t.id">
        <button type="button" class="tick" :class="{ on: t.done }" @click="toggle(t)"
                :aria-label="t.done ? '标记未完成' : '标记完成'">✓</button>
        <div class="body">
          <span :class="{ done: t.done }">{{ t.content }}</span>
          <em v-if="t.priority" class="g-tag danger">{{ t.priority === 2 ? '紧急' : '重要' }}</em>
          <em v-if="t.due" class="g-tag" :class="{ danger: overdue(t) }">{{ overdue(t) ? '逾期 ' : '' }}{{ t.due }}</em>
        </div>
        <button type="button" class="danger g-btn--sm" @click="del(t)">删除</button>
      </li>
      <li v-if="!shown.length && !loading" class="hint pad">这里空空如也。</li>
    </ul>
  </section>
</template>
