<script setup>
/**
 * SiteManager —— 网站管理面板路由
 * 只负责按 panel 选组件；数据加载下沉到各面板自身（切面板只拉这一份）。
 */
import { computed } from 'vue'
import OverviewPanel from './panels/OverviewPanel.vue'
import ArticlesPanel from './panels/ArticlesPanel.vue'
import CategoriesPanel from './panels/CategoriesPanel.vue'
import TagsPanel from './panels/TagsPanel.vue'
import MessagesPanel from './panels/MessagesPanel.vue'
import SubscribersPanel from './panels/SubscribersPanel.vue'
import MusicPanel from './panels/MusicPanel.vue'
import ProjectsPanel from './panels/ProjectsPanel.vue'
import SettingsPanel from './panels/SettingsPanel.vue'
import AuditPanel from './panels/AuditPanel.vue'
import AccountPanel from './panels/AccountPanel.vue'
import FileBrowser from '../components/FileBrowser.vue'

const props = defineProps({ panel: { type: String, default: 'workspace' } })

/* 值可以是组件，或 [组件, 附加 props] */
const PANELS = {
  workspace: OverviewPanel,
  articles: ArticlesPanel,
  write: ArticlesPanel,
  categories: CategoriesPanel,
  tags: TagsPanel,
  messages: MessagesPanel,
  subscribers: SubscribersPanel,
  music: MusicPanel,
  projects: ProjectsPanel,
  cloud: [FileBrowser, { title: '云盘' }],
  settings: SettingsPanel,
  audit: AuditPanel,
  admins: AccountPanel,
}

const current = computed(() => {
  const hit = PANELS[props.panel] || OverviewPanel
  const extra = Array.isArray(hit) ? { ...hit[1] } : {}
  // 侧栏「写文章」= 文章面板并自动展开编辑器
  if (props.panel === 'write') extra.autoOpen = true
  return { is: Array.isArray(hit) ? hit[0] : hit, extra }
})
</script>

<template>
  <div class="admin-content">
    <component :is="current.is" v-bind="current.extra" />
  </div>
</template>
