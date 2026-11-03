<script setup>
import PageList from '../components/PageList.vue'
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">Articles / 01</p>
      <h1>文章</h1>
      <p class="page-desc">技术、设计与日常的笔记，按时间倒序排列。</p>
    </header>
    <PageList kind="article" />
  </main>
</template>
