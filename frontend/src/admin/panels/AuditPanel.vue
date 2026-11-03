<script setup>
/** 审计日志 —— 进入即加载，支持动作/用户/IP/详情搜索与增量加载 */
import { ref, onMounted } from 'vue'
import { api } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'

const rows = ref([])
const state = ref('loading')
const query = ref('')
const limit = ref(100)
const more = ref(false)

const load = async () => {
  state.value = rows.value.length ? state.value : 'loading'
  const q = query.value.trim()
  const r = await api('/api/admin/audit?limit=' + limit.value + (q ? '&q=' + encodeURIComponent(q) : ''))
  if (!r.ok) { state.value = 'error'; return }
  rows.value = r.data.items || []
  more.value = rows.value.length >= limit.value
  state.value = 'ok'
}
const loadMore = () => { limit.value += 100; load() }
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>审计日志</h2><p class="hint">后台敏感操作与登录失败记录</p></div>
      <button type="button" class="g-btn" @click="load">刷新</button>
    </header>
    <div class="toolbar">
      <input v-model="query" type="search" placeholder="搜索动作 / 用户 / IP / 详情…" @keyup.enter="load" />
      <button type="button" class="g-btn--sm" @click="load">搜索</button>
    </div>

    <DataState :state="state" empty-text="没有匹配的审计记录。" @retry="load">
      <table class="admin-table">
        <thead><tr><th>时间</th><th>动作</th><th>用户</th><th>IP</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="a in rows" :key="a.id">
            <td class="muted">{{ (a.created_at || '').replace('T', ' ').slice(0, 19) }}</td>
            <td><code>{{ a.action }}</code></td><td>{{ a.user }}</td>
            <td class="muted">{{ a.ip }}</td><td class="muted">{{ a.detail }}</td>
          </tr>
        </tbody>
      </table>
      <button v-if="more" type="button" class="g-btn load-more" @click="loadMore">加载更多</button>
    </DataState>
  </section>
</template>

<style scoped>
code { padding: 2px 7px; border-radius: 6px; background: rgba(0,0,0,.05); font-size: 12px; }
.load-more { margin: 14px auto 0; display: block; }
</style>
