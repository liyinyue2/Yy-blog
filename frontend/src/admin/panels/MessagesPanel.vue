<script setup>
/**
 * 留言管理 —— 审核工作流
 * 待审核 / 已发布 / 垃圾三态 + 批量处理 + 博主回复；访客提交的留言默认进待审队列。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, asList, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { confirmAsk } from '../../composables/useConfirm'
import { vSlideBall } from '../../directives/slideBall'

const route = useRoute()
const VALID = ['pending', 'approved', 'spam', 'all']
const rows = ref([])
const state = ref('loading')
const tab = ref(VALID.includes(route.query.tab) ? route.query.tab : 'pending')
const picked = ref([])
const note = ref('')
const replying = ref(null)
const replyText = ref('')

/* 侧栏「待审核 / 已发布 / 垃圾」经 ?tab= 直达 */
watch(() => route.query.tab, v => { if (VALID.includes(v)) tab.value = v })

const load = async () => {
  const r = await api('/api/admin/messages')
  if (!r.ok) { state.value = 'error'; return }
  rows.value = asList(r.data)
  state.value = 'ok'
  picked.value = picked.value.filter(id => rows.value.some(m => m.id === id))
}

const counts = computed(() => ({
  pending: rows.value.filter(m => m.status === 'pending').length,
  approved: rows.value.filter(m => m.status === 'approved').length,
  spam: rows.value.filter(m => m.status === 'spam').length,
}))
const TABS = computed(() => [
  { value: 'pending', label: '待审核', n: counts.value.pending },
  { value: 'approved', label: '已发布', n: counts.value.approved },
  { value: 'spam', label: '垃圾', n: counts.value.spam },
  { value: 'all', label: '全部', n: rows.value.length },
])
const shown = computed(() => tab.value === 'all' ? rows.value : rows.value.filter(m => m.status === tab.value))

const togglePick = id => {
  picked.value = picked.value.includes(id) ? picked.value.filter(x => x !== id) : [...picked.value, id]
}
const pickAll = () => {
  const ids = shown.value.map(m => m.id)
  picked.value = picked.value.length === ids.length ? [] : ids
}

const moderate = async (ids, status) => {
  const r = await api('/api/admin/messages/moderate', {
    method: 'POST', body: JSON.stringify({ ids, status }),
  })
  note.value = r.ok ? r.data.message : errOf(r.data, '操作失败')
  if (r.ok) load()
}
const setStatus = async (m, status) => {
  const r = await api('/api/admin/messages/' + m.id, { method: 'PUT', body: JSON.stringify({ status }) })
  note.value = r.ok ? '' : errOf(r.data, '操作失败')
  if (r.ok) load()
}
const bulk = async status => {
  if (!picked.value.length) return
  if (status === 'spam' && !(await confirmAsk({ title: '标记为垃圾', text: `将 ${picked.value.length} 条留言标为垃圾留言。`, ok: '标记' }))) return
  moderate(picked.value, status)
  picked.value = []
}

const openReply = m => {
  replying.value = m.id
  replyText.value = m.reply || ''
}
const saveReply = async m => {
  const r = await api('/api/admin/messages/' + m.id, { method: 'PUT', body: JSON.stringify({ reply: replyText.value }) })
  if (!r.ok) { note.value = errOf(r.data, '回复失败'); return }
  note.value = '回复已保存。'
  replying.value = null
  load()
}
const remove = async m => {
  if (!(await confirmAsk({ title: '删除留言', text: '删除后不可恢复。', detail: `${m.name}：${(m.content || '').slice(0, 40)}`, ok: '删除' }))) return
  await api('/api/admin/messages/' + m.id, { method: 'DELETE' })
  load()
}
const statusLabel = s => ({ pending: '待审核', approved: '已发布', spam: '垃圾' }[s] || s)
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>留言</h2><p class="hint">访客提交后先进待审队列，通过后才对外显示</p></div>
      <div class="panel-ops">
        <button type="button" class="g-btn" @click="load">刷新</button>
      </div>
    </header>

    <div class="toolbar">
      <div class="seg" v-slide-ball>
        <button v-for="t in TABS" :key="t.value" type="button" class="chip"
                :class="{ 'is-active': tab === t.value }" @click="tab = t.value">
          {{ t.label }}<em v-if="t.n" class="chip-n">{{ t.n }}</em>
        </button>
      </div>
      <div v-if="picked.length" class="bulk-bar">
        <span>已选 {{ picked.length }} 条</span>
        <button type="button" class="g-btn--sm" @click="pickAll">取消选择</button>
        <button type="button" class="g-btn--sm g-btn--primary" @click="bulk('approved')">批量通过</button>
        <button type="button" class="danger g-btn--sm" @click="bulk('spam')">标为垃圾</button>
      </div>
    </div>
    <p v-if="note" class="hint inline-note">{{ note }}</p>

    <DataState :state="state" empty-text="这个队列里没有留言。" @retry="load">
      <ul class="msg-rows">
        <li v-for="m in shown" :key="m.id" class="msg-row" :class="{ 'is-spam': m.status === 'spam' }">
          <label class="pick">
            <input type="checkbox" :checked="picked.includes(m.id)" @change="togglePick(m.id)" :aria-label="'选择这条留言'" />
          </label>
          <div class="msg-body">
            <div class="msg-head">
              <b>{{ m.name }}</b>
              <em class="g-tag" :class="{ accent: m.status === 'pending', danger: m.status === 'spam' }">{{ statusLabel(m.status) }}</em>
              <span>{{ (m.created_at || '').replace('T', ' ').slice(0, 16) }}<template v-if="m.contact"> · {{ m.contact }}</template></span>
            </div>
            <p class="msg-text">{{ m.content }}</p>
            <div v-if="m.reply && replying !== m.id" class="msg-reply"><b>博主回复</b>{{ m.reply }}</div>
            <div v-if="replying === m.id" class="reply-row">
              <input v-model="replyText" placeholder="写下回复…" maxlength="500" @keyup.enter="saveReply(m)" />
              <button type="button" class="g-btn--sm g-btn--primary" @click="saveReply(m)">保存</button>
              <button type="button" class="g-btn--sm" @click="replying = null">取消</button>
            </div>
            <div class="msg-ops">
              <button v-if="m.status !== 'approved'" type="button" class="g-btn--sm g-btn--primary" @click="setStatus(m, 'approved')">通过</button>
              <button v-if="m.status !== 'pending'" type="button" class="g-btn--sm" @click="setStatus(m, 'pending')">退回待审</button>
              <button v-if="m.status !== 'spam'" type="button" class="g-btn--sm" @click="setStatus(m, 'spam')">标为垃圾</button>
              <button type="button" class="g-btn--sm" @click="openReply(m)">{{ m.reply ? '改回复' : '回复' }}</button>
              <span class="ops-spacer"></span>
              <button type="button" class="ghost-danger" @click="remove(m)">删除</button>
            </div>
          </div>
        </li>
      </ul>
    </DataState>
  </section>
</template>
