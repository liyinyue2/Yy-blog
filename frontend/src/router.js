import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './pages/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/articles', name: 'articles', component: () => import('./pages/ArticlesView.vue') },
    { path: '/post/:slug', name: 'post', component: () => import('./pages/PostView.vue') },
    { path: '/projects', name: 'projects', component: () => import('./pages/ProjectsView.vue') },
    { path: '/projects/:slug', name: 'project', component: () => import('./pages/ProjectView.vue') },
    { path: '/messages', name: 'messages', component: () => import('./pages/MessagesView.vue') },
    { path: '/music', name: 'music', component: () => import('./pages/MusicView.vue') },
    { path: '/about', name: 'about', component: () => import('./pages/AboutView.vue') },
    { path: '/yy-AviuuP3r', name: 'admin', component: () => import('./admin/AdminView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
