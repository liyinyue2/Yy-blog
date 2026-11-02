<script setup>
import DraggableLens from '../components/DraggableLens.vue'
</script>

<template>
  <section class="hero">
    <div class="hero-blobs" aria-hidden="true"></div>
    <div class="copy">
      <h1><span class="muted">记录思考，</span><span>分享创造。</span></h1>
      <p class="subline">这是一个关于前端开发、UI设计与个人成长的自留地。</p>
      <div class="cta"><router-link to="/articles">阅读最新文章</router-link></div>
    </div>
    <DraggableLens />
  </section>
</template>

<style scoped>
.hero {
  position: relative; height: 100vh; min-height: 640px;
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
  position: absolute; z-index: 3; top: 24.5%; left: 50%;
  width: min(92vw, 760px); transform: translateX(-50%); text-align: center;
}
.copy h1 {
  font-size: clamp(44px, 7.4vw, 92px); font-weight: 600;
  letter-spacing: -.045em; line-height: 1.05; color: var(--ink);
}
.copy h1 .muted { color: var(--ink-3); }
.subline {
  max-width: 350px; margin: 20px auto 0; color: var(--ink-2);
  font-size: clamp(13px, 1.02vw, 15.5px); line-height: 1.55;
}
.cta { margin-top: 36px; }
.cta a {
  display: inline-block; padding: 13px 30px; border-radius: var(--r-pill);
  background: var(--ink); color: #fff; font-size: 14px; font-weight: 500;
  transition: transform var(--t-fast) var(--ease), box-shadow var(--t-fast) var(--ease);
  box-shadow: var(--shadow-1);
}
.cta a:hover { transform: translateY(-2px); box-shadow: var(--shadow-2); }
</style>
