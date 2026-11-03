<script setup>
/** ConfirmDialog —— 全站唯一的确认模态（挂在 SpaceShell 上，Esc / 点遮罩取消） */
import { onMounted, onBeforeUnmount } from 'vue'
import { confirmState, settleConfirm } from '../../composables/useConfirm'

const onKey = e => { if (e.key === 'Escape' && confirmState.open) settleConfirm(false) }
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <transition name="modal">
    <div v-if="confirmState.open" class="modal-mask" @click.self="settleConfirm(false)">
      <div class="modal-card" role="dialog" aria-modal="true" :aria-label="confirmState.title">
        <h3>{{ confirmState.title }}</h3>
        <p class="mc-text">{{ confirmState.text }}</p>
        <p v-if="confirmState.detail" class="mc-detail">{{ confirmState.detail }}</p>
        <div class="mc-ops">
          <button type="button" @click="settleConfirm(false)">{{ confirmState.cancelLabel }}</button>
          <button type="button" :class="{ danger: confirmState.danger }"
                  :autofocus="confirmState.danger" @click="settleConfirm(true)">{{ confirmState.okLabel }}</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.modal-mask {
  position: fixed; inset: 0; z-index: 200; display: grid; place-items: center;
  padding: 24px; background: rgba(0,0,0,.22);
  -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
}
.modal-card {
  width: min(92vw, 420px); padding: 28px 30px; border-radius: var(--r-l);
  background: var(--glass-bg-strong);
  -webkit-backdrop-filter: var(--glass-blur); backdrop-filter: var(--glass-blur);
  box-shadow: var(--gbtn-rim-on), 0 32px 80px rgba(0,0,0,.22);
}
.modal-card h3 { font-size: 17px; font-weight: 600; letter-spacing: -.02em; color: var(--ink); margin-bottom: 10px; }
.mc-text { font-size: 14px; line-height: 1.7; color: var(--ink-2); }
.mc-detail { margin-top: 8px; font-size: 12.5px; color: var(--ink-3); word-break: break-all; }
.mc-ops { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
.mc-ops button { padding: 10px 22px; font-size: 13.5px; }
.modal-enter-active, .modal-leave-active { transition: opacity var(--t-fast) var(--ease); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
