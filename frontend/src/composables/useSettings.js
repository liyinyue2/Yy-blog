/**
 * useSettings —— 站点设置单例
 * 后台改一次，前台所有引用处即生效（站名 / Hero / 首页头像简介公告）。
 * 各字段取不到时回落到 DEFAULT_SETTINGS 同值的兜底文案。
 */
import { ref, computed } from 'vue'

export const FALLBACK = {
  site_name: "Y's Blog",
  hero_muted: '记录思考，',
  hero_main: '分享创造。',
  hero_subline: '这是一个关于前端开发、UI设计与个人成长的自留地。',
  home_avatar: '',
  home_bio: '',
  site_announcement: '',
  home_featured: '',
}

const data = ref({ ...FALLBACK })
let pending = null

export const loadSettings = () => {
  if (pending) return pending
  pending = fetch('/api/settings')
    .then(r => (r.ok ? r.json() : {}))
    .then(s => {
      /* 库里存着空串的历史行会让文案整体消失；与 v2 的 data-setting 行为一致：
         空值不覆盖已有文案，只有真正写了内容才生效。 */
      const usable = Object.fromEntries(Object.entries(s).filter(([, v]) => v !== '' && v != null))
      data.value = { ...FALLBACK, ...usable }
      return data.value
    })
    .catch(() => data.value)
  return pending
}

export const useSettings = () => ({
  settings: data,
  siteName: computed(() => data.value.site_name || FALLBACK.site_name),
  /** 精选文章 slug 列表（后台逗号分隔） */
  featured: computed(() => (data.value.home_featured || '').split(',').map(s => s.trim()).filter(Boolean)),
  hasAnnouncement: computed(() => !!(data.value.site_announcement || '').trim()),
})
