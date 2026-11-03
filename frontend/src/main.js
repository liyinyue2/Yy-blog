import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/glass.css'
import './styles/page.css'
import './styles/admin.css'
import './styles/space.css'

createApp(App).use(router).mount('#app')
