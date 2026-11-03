<script setup>
/** 系统状态 —— 健康检查、内容规模、最近审计动作 */
import { ref, onMounted } from 'vue'
import { api, asList } from '../api/client'

const health = ref('检查中')
const stats = ref(null)
const audit = ref([])
const files = ref(0)
const notes = ref(0)
const todos = ref(0)

const load = async () => {
  const [h, s, a, f, n, t] = await Promise.all([
    api('/api/health'), api('/api/stats'), api('/api/admin/audit?limit=12'),
    api('/api/cloud/files?limit=1'), api('/api/workspace/notes?limit=1'), api('/api/workspace/todos?limit=1'),
  ])
  health.value = h.ok && h.data.status === 'ok' ? '正常' : '异常'
  stats.value = s.ok ? s.data : null
  audit.value = a.ok ? (a.data.items || []) : []
  files.value = f.ok ? asList(f.data).length : 0
  notes.value = n.ok ? (n.data.total ?? 0) : 0
  todos.value = t.ok ? (t.data.total ?? 0) : 0
}
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head"><div><h2>系统状态</h2><p class="hint">后端健康、内容规模与最近动作</p></div></header>

    <div class="kv card">
      <div><b :class="{ bad: health !== '正常' }">{{ health }}</b><span>后端健康</span></div>
      <div><b>{{ stats ? stats.articles : '—' }}</b><span>文章</span></div>
      <div><b>{{ stats ? stats.categories : '—' }}</b><span>分类</span></div>
      <div><b>{{ stats ? stats.messages : '—' }}</b><span>公开留言</span></div>
      <div><b>{{ stats ? stats.subscribers : '—' }}</b><span>订阅者</span></div>
      <div><b>{{ notes }}</b><span>笔记</span></div>
      <div><b>{{ todos }}</b><span>待办</span></div>
      <div><b>{{ files }}</b><span>云文件</span></div>
    </div>

    <h3 class="sub">最近动作</h3>
    <table class="admin-table card">
      <thead><tr><th>时间</th><th>动作</th><th>用户</th><th>IP</th><th>详情</th></tr></thead>
      <tbody>
        <tr v-for="a in audit" :key="a.id">
          <td class="muted">{{ (a.created_at || '').replace('T', ' ').slice(0, 19) }}</td>
          <td>{{ a.action }}</td><td>{{ a.user }}</td><td class="muted">{{ a.ip }}</td>
          <td class="muted">{{ a.detail }}</td>
        </tr>
        <tr v-if="!audit.length"><td colspan="5" class="muted">暂无记录。</td></tr>
      </tbody>
    </table>
  </section>
</template>
