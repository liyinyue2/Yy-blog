<script setup>
/** MessagesView — 1:1 复刻原版留言板（Voices/02、三字段表单、博主回复展示） */
import { ref, onMounted } from 'vue'

const messages = ref([])
const state = ref('loading')
const name = ref('')
const contact = ref('')
const text = ref('')
const sending = ref(false)
const note = ref('')

const load = async () => {
  state.value = 'loading'
  try {
    const res = await fetch('/api/messages')
    const data = await res.json()
    messages.value = Array.isArray(data) ? data : (data.messages || [])
    state.value = 'ok'
  } catch { state.value = 'error' }
}

const send = async () => {
  if (!text.value.trim()) { note.value = '写点内容再发送吧。'; return }
  sending.value = true; note.value = '正在发送…'
  try {
    const res = await fetch('/api/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.value || '匿名', contact: contact.value, content: text.value }),
    })
    if (res.ok) {
      name.value = ''; contact.value = ''; text.value = ''
      note.value = '发送成功，感谢留言！'
      setTimeout(() => { note.value = '' }, 2500)
      load()
    } else note.value = '发送失败，请稍后再试。'
  } catch { note.value = '网络异常，请稍后再试。' }
  sending.value = false
}
onMounted(load)
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Voices / 02</p>
      <h1>留言板</h1>
      <p class="page-desc">说点什么吧——一个想法、一句问候，或者只是打个招呼，都会被认真读到。</p>
    </header>
    <form class="msg-form" @submit.prevent="send">
      <div class="msg-row">
        <input v-model="name" type="text" placeholder="你的昵称（可留空为匿名）" maxlength="30" />
        <input v-model="contact" type="text" placeholder="联系方式（选填，仅博主可见）" maxlength="100" />
      </div>
      <textarea v-model="text" placeholder="写下你的留言…" maxlength="1000" rows="4" required></textarea>
      <button type="submit" :disabled="sending">{{ sending ? '发送中…' : '发送' }}</button>
      <p v-if="note" class="form-note">{{ note }}</p>
    </form>
    <div class="msg-list">
      <article v-for="m in messages" :key="m.id" class="article-card msg-card">
        <div class="msg-head">
          <b>{{ m.name }}</b>
          <time>{{ (m.created_at || '').replace('T', ' ').slice(0, 16) }}</time>
        </div>
        <p>{{ m.content }}</p>
        <div v-if="m.reply" class="msg-reply"><b>博主回复</b>{{ m.reply }}</div>
      </article>
      <p v-if="state === 'ok' && !messages.length" class="list-empty">还没有留言，来做第一个说话的人吧。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    </div>
  </main>
</template>

<style scoped>
.msg-form { display: grid; gap: 12px; max-width: 720px; }
.msg-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.msg-form input, .msg-form textarea {
  padding: 15px 20px; border-radius: var(--r-m); border: 1px solid var(--hairline);
  outline: none; background: var(--glass-bg); color: var(--ink);
  font: inherit; font-size: 14px; resize: vertical;
  -webkit-backdrop-filter: var(--glass-blur-thin); backdrop-filter: var(--glass-blur-thin);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 2px 10px rgba(0,0,0,.05);
}
.msg-form input::placeholder, .msg-form textarea::placeholder { color: var(--ink-3); }
.msg-form input:focus, .msg-form textarea:focus { border-color: var(--accent); box-shadow: var(--focus-ring); }
.msg-form button {
  justify-self: start; padding: 13px 30px; border-radius: var(--r-pill);
  background: var(--ink); color: #fff; font-size: 13.5px; font-weight: 500;
  transition: transform var(--t-fast) var(--ease), box-shadow var(--t-fast) var(--ease);
}
.msg-form button:hover { transform: translateY(-2px); box-shadow: var(--shadow-2); }
.msg-form button:disabled { opacity: .5; }
.form-note { font-size: 12.5px; color: var(--ink-3); }
.msg-list { margin-top: 40px; display: grid; gap: 20px; }
.msg-card { padding: 24px 28px; }
.msg-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.msg-head b { font-size: 15px; color: var(--ink); }
.msg-head time { font-size: 12px; color: var(--ink-3); }
.msg-reply {
  margin-top: 16px; padding: 12px 16px; border-radius: var(--r-s);
  background: rgba(10,132,255,.06); border-left: 3px solid var(--accent);
  font-size: 13.5px; line-height: 1.7; color: var(--ink-2);
}
.msg-reply b { display: block; font-size: 12px; color: var(--accent); margin-bottom: 4px; }
@media (max-width: 760px) { .msg-row { grid-template-columns: 1fr; } }
</style>
