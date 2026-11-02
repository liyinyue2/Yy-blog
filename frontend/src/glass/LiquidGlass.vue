<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { createGlass, supportsRefraction } from '../glass/engine'

const props = defineProps({
  radius: { type: Number, default: 16 },
  bevel: { type: Number, default: 10 },
  scale: { type: Number, default: 32 },
  aberration: { type: Number, default: 0 },
  frost: { type: Number, default: 0 },
  tag: { type: String, default: 'div' },
})

const el = ref(null)
let ctrl = null

onMounted(() => {
  if (supportsRefraction()) {
    ctrl = createGlass(el.value, {
      radius: props.radius, bevelDepth: props.bevel, scale: props.scale,
      aberration: props.aberration, frost: props.frost,
    })
  } else {
    el.value.classList.add('lg-fallback')
  }
})
onBeforeUnmount(() => ctrl?.destroy())
</script>

<template>
  <component :is="tag" ref="el" class="lg-surface" :style="{ borderRadius: radius + 'px' }">
    <slot />
  </component>
</template>
