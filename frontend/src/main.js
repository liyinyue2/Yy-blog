import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/glass.css'
import './styles/page.css'
import './styles/admin.css'
import './styles/space.css'
import './styles/music.css'

/* 启动即应用主题偏好（界面设置里写入），避免首帧闪白 */
try {
  const mode = localStorage.getItem('theme') || 'auto'
  const dark = mode === 'dark' ||
    (mode === 'auto' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
  if (dark) document.documentElement.dataset.theme = 'dark'
} catch { /* 隐私模式忽略 */ }

const app = createApp(App)
app.use(router)
app.mount('#app')
