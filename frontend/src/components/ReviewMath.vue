<script setup lang="ts">
import { computed } from 'vue'
import { mathHtml } from '@/utils/reviewText'
const props = defineProps<{ text: string; formula?: boolean }>()
const html = computed(() => mathHtml(props.text, props.formula))
</script>
<template>
  <!-- Prose is escaped; the only markup emitted is KaTeX with trust:false. -->
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="review-math"
    v-html="html"
  />
</template>
<style scoped>.review-math { overflow-wrap: anywhere; line-height: 1.85; } .review-math :deep(.katex-display) { overflow-x: auto; overflow-y: hidden; padding: .5rem 0; }</style>
