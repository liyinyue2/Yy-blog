import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './pages/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/articles', name: 'articles', component: () => import('./pages/ArticlesView.vue') },
    { path: '/projects', name: 'projects', component: () => import('./pages/ProjectsView.vue') },
    { path: '/messages', name: 'messages', component: () => import('./pages/MessagesView.vue') },
    { path: '/music', name: 'music', component: () => import('./pages/MusicView.vue') },
    { path: '/about', name: 'about', component: () => import('./pages/AboutView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
