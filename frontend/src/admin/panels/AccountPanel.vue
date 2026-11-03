<script setup>
/**
 * 账号与安全 —— 当前账号信息 + 修改密码
 * 此前该面板只有一句「将在后续版本提供」的占位文案。
 */
import { ref, onMounted } from 'vue'
import { api, errOf, clearTokens } from '../../api/client'
import { confirmAsk } from '../../composables/useConfirm'

const me = ref(null)
const form = ref({ old_password: '', new_password: '', repeat: '' })
const note = ref('')
const bad = ref(false)
const saving = ref(false)

const load = async () => {
  const r = await api('/api/auth/me')
  if (r.ok) me.value = r.data
}
const submit = async () => {
  const f = form.value
  note.value = ''
  bad.value = false
  if (!f.old_password) { note.value = '请输入旧密码。'; bad.value = true; return }
  if (f.new_password.length < 8) { note.value = '新密码至少 8 位。'; bad.value = true; return }
  if (f.new_password !== f.repeat) { note.value = '两次输入的新密码不一致。'; bad.value = true; return }
  if (!(await confirmAsk({
    title: '修改密码', text: '修改成功后当前会话会失效，需要用新密码重新登录。', ok: '确认修改',
  }))) return
  saving.value = true
  const r = await api('/api/auth/password', {
    method: 'POST', body: JSON.stringify({ old_password: f.old_password, new_password: f.new_password }),
  })
  saving.value = false
  if (!r.ok) { note.value = errOf(r.data, '修改失败'); bad.value = true; return }
  clearTokens()
  location.href = '/space'
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>账号与安全</h2><p class="hint">单管理员账号；多管理员与角色管理在 S3</p></div>
    </header>

    <div class="card acct-card">
      <h3>当前账号</h3>
      <dl class="acct">
        <div><dt>用户名</dt><dd>{{ me ? me.username : '—' }}</dd></div>
        <div><dt>角色</dt><dd>{{ me ? (me.role === 'admin' ? '管理员' : me.role) : '—' }}</dd></div>
        <div><dt>会话</dt><dd>访问令牌 15 分钟自动续期，刷新令牌 7 天</dd></div>
      </dl>
    </div>

    <form class="card set-group" @submit.prevent="submit">
      <h3>修改密码</h3>
      <div class="field-grid">
        <div class="field"><label for="pw-old">旧密码</label>
          <input id="pw-old" v-model="form.old_password" type="password" autocomplete="current-password" /></div>
        <div class="field"><label for="pw-new">新密码（至少 8 位）</label>
          <input id="pw-new" v-model="form.new_password" type="password" autocomplete="new-password" /></div>
        <div class="field"><label for="pw-rep">确认新密码</label>
          <input id="pw-rep" v-model="form.repeat" type="password" autocomplete="new-password" /></div>
      </div>
      <div class="set-foot">
        <button type="submit" class="g-btn--sm g-btn--primary" :disabled="saving">{{ saving ? '提交中…' : '修改密码' }}</button>
        <span class="hint" :class="{ danger: bad }">{{ note }}</span>
      </div>
    </form>
  </section>
</template>

<style scoped>
.acct { display: grid; gap: 10px; }
.acct > div { display: flex; gap: 12px; font-size: 13.5px; }
.acct dt { color: var(--ink-3); min-width: 72px; }
.acct dd { color: var(--ink-2); }
.set-group { margin-top: 18px; }
.set-foot { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.hint.danger { color: var(--danger); }
</style>
