<script setup>
import { ref, onMounted } from 'vue'

const messages = ref([])
const state = ref('loading')
const name = ref('')
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
  if (!name.value.trim() || !text.value.trim()) { note.value = '昵称和内容都要填哦。'; return }
  sending.value = true; note.value = '正在发送…'
  try {
    const res = await fetch('/api/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.value, content: text.value }),
    })
    if (res.ok) { name.value = ''; text.value = ''; note.value = ''; load() }
    else note.value = '发送失败，请稍后再试。'
  } catch { note.value = '网络异常，请稍后再试。' }
  sending.value = false
}
onMounted(load)
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Guestbook / 03</p>
      <h1>留言</h1>
      <p class="page-desc">路过就留句话吧，匿名也欢迎。</p>
    </header>
    <form class="msg-form" @submit.prevent="send">
      <input v-model="name" placeholder="昵称" maxlength="24" />
      <textarea v-model="text" placeholder="想说的话…" maxlength="600" rows="4"></textarea>
      <button type="submit" :disabled="sending">{{ sending ? '发送中…' : '发送' }}</button>
      <p v-if="note" class="form-note">{{ note }}</p>
    </form>
    <div class="msg-list">
      <article v-for="m in messages" :key="m.id" class="article-card">
        <h3>{{ m.name }}</h3>
        <p>{{ m.content }}</p>
        <span class="card-meta">{{ m.created_at || '' }}</span>
      </article>
      <p v-if="state === 'ok' && !messages.length" class="list-empty">还没有人留言，来做第一个吧。</p>
      <p v-if="state === 'loading'" class="list-loading">正在加载…</p>
    </div>
  </main>
</template>

<style scoped>
.msg-form { display: grid; gap: 12px; max-width: 640px; }
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
.msg-list { margin-top: 40px; }
</style>
