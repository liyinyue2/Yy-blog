<script setup>
/** 歌单新建 / 重命名弹窗（复用站点的玻璃模态语言） */
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '新建歌单' },
  value: { type: String, default: '' },
  confirmText: { type: String, default: '保存' },
})
const emit = defineEmits(['save', 'close'])
const name = ref('')
const input = ref(null)

watch(() => props.open, async v => {
  if (!v) return
  name.value = props.value
  await nextTick()
  input.value?.focus()
  input.value?.select()
})
const submit = () => {
  const n = name.value.trim()
  if (!n) return
  emit('save', n)
}
</script>

<template>
  <div v-if="open" class="pl-dialog" @click.self="emit('close')">
    <form class="card" @submit.prevent="submit">
      <h3>{{ title }}</h3>
      <input ref="input" v-model="name" maxlength="40" placeholder="歌单名称" aria-label="歌单名称" />
      <div class="row">
        <button type="button" class="g-btn--sm" @click="emit('close')">取消</button>
        <button type="submit" class="g-btn--sm g-btn--primary" :disabled="!name.trim()">{{ confirmText }}</button>
      </div>
    </form>
  </div>
</template>
