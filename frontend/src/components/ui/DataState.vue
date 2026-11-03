<script setup>
/**
 * DataState —— 列表/面板的统一加载态
 * state: loading | error | empty | ok；非 ok 时渲染占位，ok 时渲染默认插槽。
 */
defineProps({
  state: { type: String, default: 'ok' },
  loadingText: { type: String, default: '正在加载…' },
  emptyText: { type: String, default: '这里还没有内容。' },
  errorText: { type: String, default: '加载失败，请重试。' },
})
const emit = defineEmits(['retry'])
</script>

<template>
  <div v-if="state === 'loading'" class="ds" aria-live="polite">
    <span class="spinner" aria-hidden="true"></span><span>{{ loadingText }}</span>
  </div>
  <div v-else-if="state === 'error'" class="ds is-error" role="alert">
    <span>{{ errorText }}</span>
    <button type="button" class="g-btn--sm" @click="emit('retry')">重试</button>
  </div>
  <div v-else-if="state === 'empty'" class="ds is-empty">{{ emptyText }}</div>
  <slot v-else />
</template>

<style scoped>
.ds {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  padding: 46px 20px; text-align: center; font-size: 13.5px; color: var(--ink-3);
}
.ds.is-empty { padding: 34px 20px; }
.ds.is-error { color: var(--danger); }
.spinner {
  width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid var(--hairline-strong); border-top-color: var(--accent);
  animation: ds-spin .7s linear infinite;
}
@keyframes ds-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2s; } }
</style>
