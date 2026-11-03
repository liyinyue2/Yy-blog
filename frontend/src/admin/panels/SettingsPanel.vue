<script setup>
/**
 * 站点设置 —— 分组保存
 * 首页已收为单屏落地页（只有 Hero），公告 / 精选 / 头像 / 简介不再有承载位置，
 * 因此从表单移除；后端键保留，历史数据不丢，将来恢复区块可直接复用。
 */
import { ref, onMounted } from 'vue'
import { api, errOf } from '../../api/client'
import DataState from '../../components/ui/DataState.vue'
import { FALLBACK } from '../../composables/useSettings'

const settings = ref({})
const state = ref('loading')
const saved = ref({})

const load = async () => {
  const s = await api('/api/settings')
  if (!s.ok) { state.value = 'error'; return }
  settings.value = s.data || {}
  state.value = 'ok'
}

/** 按分组提交：只带上该组的键，避免整份覆盖 */
const GROUPS = {
  brand: ['site_name', 'hero_muted', 'hero_main', 'hero_subline'],
  about: ['about_intro', 'about_content'],
  social: ['social_github', 'social_wechat', 'social_qq', 'social_douyin'],
}
const save = async key => {
  const payload = Object.fromEntries(GROUPS[key].map(k => [k, settings.value[k] ?? '']))
  const r = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify(payload) })
  saved.value = { ...saved.value, [key]: r.ok ? '已保存。' : errOf(r.data, '保存失败') }
  setTimeout(() => { saved.value = { ...saved.value, [key]: '' } }, 2600)
  if (r.ok) load()
}
/* 库里没存过的键显示前台实际生效的兜底文案，避免"后台空白、前台有字"。
   保存即把这份文案落库，从此以库为准。 */
const f = k => ({ value: settings.value[k] || FALLBACK[k] || '', input: e => { settings.value = { ...settings.value, [k]: e.target.value } } })
onMounted(load)
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div><h2>站点设置</h2><p class="hint">改完即生效于公开面，无需重新发布</p></div>
    </header>

    <DataState :state="state" @retry="load">
      <div class="card set-group">
        <h3>品牌与首页</h3>
        <div class="field-grid">
          <div class="field"><label for="s-name">站点名称</label><input id="s-name" v-bind="f('site_name')" maxlength="60" /></div>
          <div class="field"><label for="s-hm1">首页主标题（灰色部分）</label><input id="s-hm1" v-bind="f('hero_muted')" maxlength="40" /></div>
          <div class="field"><label for="s-hm2">首页主标题（主体）</label><input id="s-hm2" v-bind="f('hero_main')" maxlength="40" /></div>
          <div class="field"><label for="s-sub">首页副标题</label><input id="s-sub" v-bind="f('hero_subline')" maxlength="120" /></div>
        </div>
        <div class="set-foot"><button type="button" class="g-btn--sm g-btn--primary" @click="save('brand')">保存这一组</button><span class="hint">{{ saved.brand }}</span></div>
      </div>

      <div class="card set-group">
        <h3>关于页</h3>
        <div class="field"><label for="s-intro">引言</label><input id="s-intro" v-bind="f('about_intro')" maxlength="200" /></div>
        <div class="field"><label for="s-content">正文（HTML，入库前服务端白名单清洗）</label>
          <textarea id="s-content" v-bind="f('about_content')" rows="6"></textarea></div>
        <div class="set-foot"><button type="button" class="g-btn--sm g-btn--primary" @click="save('about')">保存这一组</button><span class="hint">{{ saved.about }}</span></div>
      </div>

      <div class="card set-group">
        <h3>社交链接 <span class="hint">（填链接则跳转，填账号则点击复制）</span></h3>
        <div class="field-grid">
          <div class="field"><label for="s-gh">GitHub</label><input id="s-gh" v-bind="f('social_github')" /></div>
          <div class="field"><label for="s-wx">微信</label><input id="s-wx" v-bind="f('social_wechat')" /></div>
          <div class="field"><label for="s-qq">QQ</label><input id="s-qq" v-bind="f('social_qq')" /></div>
          <div class="field"><label for="s-dy">抖音</label><input id="s-dy" v-bind="f('social_douyin')" /></div>
        </div>
        <div class="set-foot"><button type="button" class="g-btn--sm g-btn--primary" @click="save('social')">保存这一组</button><span class="hint">{{ saved.social }}</span></div>
      </div>
    </DataState>
  </section>
</template>

<style scoped>
.set-group { margin-bottom: 18px; }
.set-group h3 { margin-bottom: 14px; }
.set-foot { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.avatar-row { display: flex; align-items: center; gap: 12px; }
.avatar-row input { flex: 1; }
.avatar-prev { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; box-shadow: var(--gbtn-rim); }
.pick-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; }
.pick-item {
  display: flex; align-items: center; gap: 9px; padding: 9px 12px; cursor: pointer;
  border-radius: var(--r-m); font-size: 13px; color: var(--ink-2);
  background: var(--gbtn-bg); box-shadow: var(--gbtn-rim);
}
.pick-item:hover { background: var(--gbtn-bg-hover); }
.pick-item span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pick-item em { font-style: normal; font-size: 11.5px; color: var(--ink-3); }
.pick-item input { width: 16px; height: 16px; accent-color: var(--accent); }
</style>
