<script setup>
import PageList from '../components/PageList.vue'
</script>

<template>
  <main class="page-main">
    <header class="page-head">
      <p class="section-kicker">All notes / 01</p>
      <h1>文章</h1>
      <p class="page-desc">把技术、设计与生活里的小发现，整理成可以反复阅读的片段。</p>
    </header>
    <PageList kind="article" />
  </main>
</template>
