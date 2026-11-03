<script setup>
/** 404 —— 未匹配路由的兜底页（此前未知路径只剩导航条，正文空白） */
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <main class="page-main notfound">
    <p class="section-kicker">404 / Not found</p>
    <h1>这个地址下没有内容</h1>
    <p class="page-desc">
      路径 <code>{{ route.fullPath }}</code> 未匹配到任何页面。可能是旧链接失效，或地址输错了。
    </p>
    <div class="nf-links">
      <router-link class="chip" to="/">回首页</router-link>
      <router-link class="chip" to="/articles">看文章</router-link>
      <router-link class="chip" to="/articles">看看文章</router-link>
      <router-link class="chip" to="/space">进入数字空间</router-link>
    </div>
  </main>
</template>

<style scoped>
.notfound h1 { margin-bottom: 8px; }
code { padding: 2px 8px; border-radius: 6px; background: rgba(0,0,0,.06); font-size: 13px; }
.nf-links { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 32px; }
</style>
