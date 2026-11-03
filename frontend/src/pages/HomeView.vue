<script setup>
/**
 * HomeView —— 公开博客首页（单屏落地页）
 * 只有 Hero：标题 / 副题 / 阅读入口 / 社交 / 数字空间入口 / 可拖拽玻璃透镜。
 * 不再向下堆精选、最近更新、正在听、项目作品——那些各有独立页面。
 */
import { ref } from 'vue'
import DraggableLens from '../components/DraggableLens.vue'
import DotsCanvas from '../components/DotsCanvas.vue'
import SocialLinks from '../components/SocialLinks.vue'
import { useSettings } from '../composables/useSettings'

const { settings } = useSettings()
const copied = ref('')
const onCopied = label => {
  copied.value = `${label} 已复制到剪贴板`
  setTimeout(() => { copied.value = '' }, 2200)
}
</script>

<template>
  <div class="home">
  <section class="hero">
    <div class="hero-blobs" aria-hidden="true"></div>
    <DotsCanvas />
    <div class="copy">
      <h1><span class="muted">{{ settings.hero_muted }}</span><span>{{ settings.hero_main }}</span></h1>
      <p class="subline">{{ settings.hero_subline }}</p>
      <div class="cta"><router-link to="/articles">阅读最新文章</router-link></div>
    </div>
    <div class="socials-wrap">
      <SocialLinks @copied="onCopied" />
      <transition name="toast-in">
        <div v-if="copied" class="copy-toast">{{ copied }}</div>
      </transition>
    </div>
    <DraggableLens />
    <a class="space-entry" href="/space" aria-label="进入个人数字空间">数字空间 ↗</a>
  </section>

  </div>
</template>

<style scoped>
.hero {
  position: relative; height: 100vh; height: 100svh; min-height: min(600px, 100svh);
  overflow: hidden; isolation: isolate; background: var(--surface);
}
.hero-blobs { position: absolute; inset: -10%; z-index: 0; pointer-events: none; filter: blur(2px); }
.hero-blobs::before, .hero-blobs::after { content: ""; position: absolute; border-radius: 50%; }
.hero-blobs::before {
  width: 56vw; height: 56vw; min-width: 420px; min-height: 420px; top: -8%; right: -6%;
  background:
    radial-gradient(closest-side at 30% 35%, rgba(56,189,248,.85), transparent 70%),
    radial-gradient(closest-side at 70% 60%, rgba(232,121,249,.75), transparent 72%),
    radial-gradient(closest-side at 45% 80%, rgba(253,224,71,.65), transparent 70%);
}
.hero-blobs::after {
  width: 44vw; height: 44vw; min-width: 340px; min-height: 340px; bottom: -12%; left: -4%;
  background:
    radial-gradient(closest-side at 60% 40%, rgba(74,222,128,.7), transparent 70%),
    radial-gradient(closest-side at 30% 70%, rgba(96,165,250,.7), transparent 72%);
}
@media (prefers-reduced-transparency: reduce) { .hero-blobs { display: none; } }

.copy {
  position: absolute; z-index: 3; top: 22%; left: 50%;
  width: min(94vw, 1000px); transform: translateX(-50%); text-align: center;
}
.copy h1 {
  font-size: clamp(40px, 6.2vw, 82px); font-weight: 600;
  letter-spacing: -.045em; line-height: 1.05; color: var(--ink);
}
.copy h1 .muted { color: var(--ink-3); }
.subline {
  max-width: min(78vw, 470px); margin: 20px auto 0; color: var(--ink-2);
  font-size: clamp(13px, 1.02vw, 15.5px); line-height: 1.55;
}
.cta { margin-top: 36px; }
.cta a {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 13px 30px; border-radius: var(--r-pill);
  font-size: 14px; font-weight: 500; color: var(--ink);
  background: var(--gbtn-bg-hover);
  -webkit-backdrop-filter: var(--gbtn-blur); backdrop-filter: var(--gbtn-blur);
  box-shadow: var(--gbtn-rim-on), var(--gbtn-shadow);
  transition: background var(--t-fast) var(--ease), transform var(--t-fast) var(--ease),
              box-shadow var(--t-fast) var(--ease);
}
.cta a:hover { background: var(--gbtn-bg-on); transform: translateY(-2px); box-shadow: var(--gbtn-rim-on), var(--gbtn-shadow-on); }
.cta a:active { transform: translateY(0) scale(.985); }

.socials-wrap {
  position: absolute; z-index: 3; bottom: clamp(40px, 7vh, 72px);
  left: 0; right: 0; display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.copy-toast {
  padding: 10px 18px; border-radius: var(--r-pill);
  background: var(--glass-bg-dark); color: #fff; font-size: 12.5px;
  -webkit-backdrop-filter: var(--glass-blur-thin); backdrop-filter: var(--glass-blur-thin);
  box-shadow: var(--shadow-2);
}
.toast-in-enter-active, .toast-in-leave-active { transition: opacity var(--t-base) var(--ease), transform var(--t-base) var(--ease); }
.toast-in-enter-from, .toast-in-leave-to { opacity: 0; transform: translateY(8px); }

/* 数字空间入口：低调放在 Hero 右下角 */
.space-entry {
  position: absolute; z-index: 4; right: 22px; bottom: 20px;
  padding: 7px 14px; border-radius: var(--r-pill);
  font-size: 11.5px; color: var(--ink-3);
  background: var(--gbtn-bg); box-shadow: var(--gbtn-rim);
  -webkit-backdrop-filter: var(--gbtn-blur); backdrop-filter: var(--gbtn-blur);
  transition: color var(--t-fast) var(--ease), background var(--t-fast) var(--ease);
}
.space-entry:hover { color: var(--ink); background: var(--gbtn-bg-hover); }


/* 手机端：≤760px 时主导航变成底部固定 tab bar，社交行与空间入口须整体抬到其上方，
   否则三者叠在同一区域。 */
@media (max-width: 760px) {
  .socials-wrap { bottom: calc(116px + env(safe-area-inset-bottom)); }
  .space-entry { right: 14px; bottom: calc(78px + env(safe-area-inset-bottom)); }
}
</style>
