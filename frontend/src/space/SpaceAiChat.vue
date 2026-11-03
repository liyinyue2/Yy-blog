<script setup>
/** AI 对话 —— /api/space/ai/*（会话 CRUD + SSE 流式回复；密钥只在服务端 .env） */
import { nextTick, onMounted, ref } from 'vue'
import { api, asList, errOf } from '../api/client'

const convs = ref([])
const current = ref(null)
const messages = ref([])
const input = ref('')
const note = ref('')
const sending = ref(false)
const listEl = ref(null)

const loadConvs = async () => {
  const r = await api('/api/space/ai/conversations')
  if (!r.ok) { note.value = errOf(r.data, '读取会话失败'); return }
  convs.value = asList(r.data)
  if (!current.value && convs.value.length) await open(convs.value[0])
}
const open = async c => {
  current.value = c
  const r = await api(`/api/space/ai/conversations/${c.id}/messages`)
  messages.value = r.ok ? asList(r.data) : []
  await scroll()
}
const create = async () => {
  const r = await api('/api/space/ai/conversations', { method: 'POST', body: JSON.stringify({ title: '新的对话' }) })
  if (!r.ok) { note.value = errOf(r.data, '新建会话失败'); return }
  await loadConvs()
  const made = convs.value.find(c => c.id === r.data.id)
  if (made) await open(made)
}
const remove = async c => {
  const r = await api('/api/space/ai/conversations/' + c.id, { method: 'DELETE' })
  if (!r.ok) { note.value = errOf(r.data, '删除失败'); return }
  if (current.value && current.value.id === c.id) { current.value = null; messages.value = [] }
  await loadConvs()
}
const scroll = async () => {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

/* SSE：逐行读 data: {...}，delta 追加到当前助手气泡 */
const send = async () => {
  const text = input.value.trim()
  if (!text || sending.value) return
  if (!current.value) await create()
  if (!current.value) return
  sending.value = true
  note.value = ''
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  const reply = { role: 'assistant', content: '' }
  messages.value.push(reply)
  await scroll()
  try {
    const res = await fetch('/api/space/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (sessionStorage.getItem('admin-access') || '') },
      body: JSON.stringify({ conversation_id: current.value.id, content: text }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      reply.content = data.detail || data.error || `请求失败（${res.status}）`
      return
    }
    const reader = res.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') continue
        try {
          const evt = JSON.parse(raw)
          if (evt.delta) { reply.content += evt.delta; await scroll() }
        } catch { /* 忽略非 JSON 心跳 */ }
      }
    }
  } catch (e) {
    reply.content = reply.content || '网络异常，请稍后再试。'
  } finally {
    sending.value = false
    loadConvs()
  }
}
onMounted(loadConvs)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>AI 对话</h2><p class="hint">密钥只存在服务端 .env（AI_API_KEY / AI_BASE_URL / AI_MODEL）</p></div>
      <button type="button" class="g-btn--sm g-btn--primary" @click="create">新建对话</button>
    </header>

    <div class="ai-layout">
      <aside class="card ai-side">
        <ul class="rows">
          <li v-for="c in convs" :key="c.id" class="row" :class="{ 'is-active': current && current.id === c.id }"
              @click="open(c)">
            <div class="row-main"><b>{{ c.title || '未命名' }}</b>
              <span class="hint">{{ (c.updated_at || '').slice(5, 16).replace('T', ' ') }}</span></div>
            <div class="row-ops">
              <button type="button" class="danger g-btn--sm" @click.stop="remove(c)">删除</button>
            </div>
          </li>
          <li v-if="!convs.length" class="hint">还没有对话，点右上新建。</li>
        </ul>
      </aside>

      <div class="card ai-main">
        <div ref="listEl" class="ai-msgs">
          <div v-for="(m, i) in messages" :key="i" class="ai-msg" :class="m.role">
            <em>{{ m.role === 'user' ? '我' : 'AI' }}</em>
            <p>{{ m.content }}</p>
          </div>
          <p v-if="!messages.length" class="hint">新建一个对话，然后说点什么。</p>
        </div>
        <form class="ai-input" @submit.prevent="send">
          <input v-model="input" placeholder="输入消息，回车发送…" :disabled="sending" />
          <button type="submit" class="g-btn--sm g-btn--primary" :disabled="sending || !input.trim()">
            {{ sending ? '回复中…' : '发送' }}
          </button>
        </form>
        <p v-if="note" class="hint">{{ note }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ai-layout { display: grid; grid-template-columns: minmax(180px, 240px) minmax(0, 1fr); gap: 16px; align-items: start; }
.ai-side .row { cursor: pointer; }
.ai-side .row.is-active { background: var(--gbtn-bg-hover); }
.ai-main { display: flex; flex-direction: column; min-height: 420px; }
.ai-msgs { flex: 1; overflow-y: auto; max-height: 460px; display: flex; flex-direction: column; gap: 10px; padding-right: 4px; }
.ai-msg { display: flex; gap: 10px; font-size: 13.5px; line-height: 1.7; }
.ai-msg em { flex-shrink: 0; font-style: normal; color: var(--ink-3); width: 22px; }
.ai-msg p { white-space: pre-wrap; word-break: break-word; }
.ai-msg.user p { color: var(--ink); }
.ai-input { display: flex; gap: 8px; margin-top: 14px; }
.ai-input input { flex: 1; }
@media (max-width: 900px) { .ai-layout { grid-template-columns: minmax(0, 1fr); } }
</style>
