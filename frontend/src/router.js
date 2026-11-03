import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './pages/HomeView.vue'
import SpaceShell from './space/SpaceShell.vue'
import SiteManager from './admin/SiteManager.vue'

/* 目标结构中尚未实装的分区：写明后端已有能力与缺口，而不是空壳占位 */
const plan = (label, phase, has, todo) => ({ component: () => import('./space/SpacePlanned.vue'), meta: { plan: { label, phase, has, todo } } })

const routes = [
  /* ---------- 公开个人博客：访客无需登录 ---------- */
  { path: '/', name: 'home', component: HomeView },
  { path: '/articles', name: 'articles', component: () => import('./pages/ArticlesView.vue') },
  { path: '/post/:slug', name: 'post', component: () => import('./pages/PostView.vue') },
  { path: '/library', name: 'library', component: () => import('./pages/LibraryView.vue') },
  { path: '/messages', name: 'messages', component: () => import('./pages/MessagesView.vue') },
  { path: '/music', name: 'music', component: () => import('./pages/MusicView.vue') },
  { path: '/about', name: 'about', component: () => import('./pages/AboutView.vue') },

  /* ---------- 个人数字空间：登录后使用与管理 ---------- */
  {
    path: '/space', component: SpaceShell,
    children: [
      { path: '', redirect: '/space/dashboard' },
      { path: 'dashboard', name: 'space-dashboard', component: () => import('./space/SpaceDashboard.vue') },

      // 网站管理（write 直接进文章面板并自动开编辑器；其余具体子项先于 :panel 匹配）
      { path: 'site/pages', ...plan('页面管理', 'S3',
        ['settings 表 key-value（已驱动首页/关于页文案）'],
        ['自定义页面表与路由', '页面排序与可见性']) },
      { path: 'site/links', ...plan('友链管理', 'S3',
        ['统一标签体系 taggables 可复用', 'settings 表可存开关'],
        ['friends 表与 CRUD 接口', '前台友链页与申请入口']) },
      { path: 'site/media', ...plan('媒体资源', 'S3',
        ['上传五层校验与 UUID 落盘（云盘/音乐已用）', 'Range 流媒体'],
        ['统一媒体库表', '图片缩略与在编辑器中选取']) },
      { path: 'site/:panel', name: 'space-site', component: SiteManager, props: true },

      // 个人空间
      { path: 'notes', name: 'space-notes', component: () => import('./space/SpaceNotes.vue') },
      { path: 'files', name: 'space-files', component: () => import('./space/SpaceFiles.vue') },
      { path: 'projects-manage', ...plan('项目中心', 'S2',
        ['projects / project_logs 表与全套管理接口', '公开项目页与详情页'],
        ['空间内项目列表与开发日志编辑界面']) },
      { path: 'learning', ...plan('学习记录', 'S3', ['知识库笔记（notes）可承载内容'], ['学习记录表与统计视图']) },

      // 效率工具
      { path: 'todos', name: 'space-todos', component: () => import('./space/SpaceTodos.vue') },
      { path: 'pomodoro', name: 'space-pomodoro', component: () => import('./space/SpacePomodoro.vue') },
      { path: 'bookmarks', ...plan('书签', 'S2', ['GET/POST/DELETE /api/workspace/bookmarks（URL 仅 http/https）'], ['空间内书签列表面板']) },
      { path: 'calendar', ...plan('日程', 'S3', ['待办的 due 日期字段'], ['日程表、重复规则与月视图']) },

      // AI 中心
      { path: 'ai/chat', ...plan('AI 对话', 'S2',
        ['/api/space/ai/* 会话与消息表、SSE 流式转发', '密钥仅服务端 env，限流 60s/10'],
        ['对话界面与流式渲染（需配置 AI_API_KEY 才能实测）']) },
      { path: 'ai/agents', ...plan('智能体', 'S4', ['AI 对话底座'], ['角色设定与工具调用']) },
      { path: 'ai/flows', ...plan('工作流', 'S4', ['AI 对话底座'], ['多步编排与定时触发']) },

      // 系统设置
      { path: 'profile', ...plan('个人资料', 'S2', ['settings 已含 about_intro / about_content / social_*', '本轮新增 home_avatar / home_bio / site_announcement / home_featured'], ['独立的个人资料分区与头像上传']) },
      { path: 'account', ...plan('账号与安全', 'S2', ['users 表 + bcrypt + JWT 双令牌 + require_role', '登录失败限流与审计'], ['改密码界面', '多管理员与角色管理']) },
      { path: 'appearance', ...plan('界面设置', 'S2', ['tokens.css 亮暗双套已就绪（data-theme="dark" 预留）'], ['主题切换开关与持久化']) },
      { path: 'system', name: 'space-system', component: () => import('./space/SpaceSystem.vue') },
    ],
  },

  /* 旧后台入口：保持隐匿路径可用，落进数字空间的网站管理 */
  { path: '/yy-AviuuP3r', redirect: '/space/site/workspace' },
  { path: '/yy-AviuuP3r/:rest*', redirect: '/space/site/workspace' },

  /* 兜底 404 */
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('./pages/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

/* 旧 v2 静态地址兼容：文章详情按 slug 还原，其余页面回到对应 SPA 路由，
   避免历史外链与书签落到 404。 */
const LEGACY_PAGES = {
  '/index.html': '/',
  '/articles.html': '/articles',
  '/messages.html': '/messages',
  '/music.html': '/music',
  '/about.html': '/about',
  '/projects.html': '/library',
  '/subscribe.html': '/messages',
  '/space.html': '/space/dashboard',
}
router.beforeEach(to => {
  if (!to.path.endsWith('.html')) return true
  const post = to.path.match(/^\/post-(.+)\.html$/)
  if (post) return { path: '/post/' + post[1], replace: true }
  return { path: LEGACY_PAGES[to.path] || '/', replace: true }
})

/* 记录最近访问（工作台「最近访问」组件读取） */
const TITLES = {
  dashboard: '工作台', notes: '知识库', files: '云文件', todos: '待办事项', pomodoro: '番茄钟', system: '系统状态',
  workspace: '网站概览', articles: '文章列表', categories: '分类管理', tags: '标签管理', messages: '留言管理',
  subscribers: '订阅者', music: '音乐管理', projects: '项目', cloud: '云盘', settings: '站点设置',
  audit: '审计日志', admins: '管理员', write: '写文章',
}
router.afterEach(to => {
  if (!to.path.startsWith('/space/')) return
  const key = to.params.panel || to.path.split('/')[2] || 'dashboard'
  const label = TITLES[key] || key
  const at = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const list = JSON.parse(localStorage.getItem('space-recent') || '[]')
    .filter(x => x.to !== to.path)
  list.unshift({ to: to.path, label, at })
  localStorage.setItem('space-recent', JSON.stringify(list.slice(0, 8)))
})

export default router
