<script setup>
/** 个人资料 —— 关于页文案与社交链接（读写 /api/settings 与 /api/admin/settings） */
import { onMounted, ref } from 'vue'
import { api, errOf } from '../api/client'
import DataState from '../components/ui/DataState.vue'

const form = ref({ about_intro: '', about_content: '', social_github: '', social_wechat: '', social_qq: '', social_douyin: '' })
const state = ref('loading')
const note = ref({})
const saving = ref('')

const load = async () => {
  const r = await api('/api/settings')
  if (!r.ok) { state.value = 'error'; return }
  const s = r.data || {}
  form.value = Object.fromEntries(Object.keys(form.value).map(k => [k, s[k] || '']))
  state.value = 'ok'
}
const save = async key => {
  saving.value = key
  const keys = key === 'about' ? ['about_intro', 'about_content']
    : ['social_github', 'social_wechat', 'social_qq', 'social_douyin']
  const payload = Object.fromEntries(keys.map(k => [k, form.value[k] || '']))
  const r = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify(payload) })
  saving.value = ''
  note.value = { ...note.value, [key]: r.ok ? '已保存。' : errOf(r.data, '保存失败') }
  setTimeout(() => { note.value = { ...note.value, [key]: '' } }, 2600)
  if (r.ok) load()
}
onMounted(load)
</script>

<template>
  <section class="space-page">
    <header class="sp-head">
      <div><h2>个人资料</h2><p class="hint">关于页的引言、正文与社交链接，改完即生效</p></div>
    </header>

    <DataState :state="state" @retry="load">
      <div class="card set-group">
        <h3>关于页</h3>
        <div class="field"><label for="p-intro">引言</label>
          <input id="p-intro" v-model="form.about_intro" maxlength="200" /></div>
        <div class="field"><label for="p-content">正文（HTML，入库前服务端白名单清洗）</label>
          <textarea id="p-content" v-model="form.about_content" rows="8"></textarea></div>
        <div class="set-foot">
          <button type="button" class="g-btn--sm g-btn--primary" :disabled="saving === 'about'" @click="save('about')">
            {{ saving === 'about' ? '保存中…' : '保存' }}
          </button>
          <span class="hint">{{ note.about }}</span>
        </div>
      </div>

      <div class="card set-group">
        <h3>社交链接 <span class="hint">（填链接则跳转，填账号则点击复制）</span></h3>
        <div class="field-grid">
          <div class="field"><label for="p-gh">GitHub</label><input id="p-gh" v-model="form.social_github" /></div>
          <div class="field"><label for="p-wx">微信</label><input id="p-wx" v-model="form.social_wechat" /></div>
          <div class="field"><label for="p-qq">QQ</label><input id="p-qq" v-model="form.social_qq" /></div>
          <div class="field"><label for="p-dy">抖音</label><input id="p-dy" v-model="form.social_douyin" /></div>
        </div>
        <div class="set-foot">
          <button type="button" class="g-btn--sm g-btn--primary" :disabled="saving === 'social'" @click="save('social')">
            {{ saving === 'social' ? '保存中…' : '保存' }}
          </button>
          <span class="hint">{{ note.social }}</span>
        </div>
      </div>
    </DataState>
  </section>
</template>
