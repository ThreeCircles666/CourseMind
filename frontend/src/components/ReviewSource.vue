<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Evidence } from '@/api/review'
const props = defineProps<{ evidence: Evidence; name: string; image?: string }>()
const emit = defineEmits<{ open: []; preview: [] }>()
const { t } = useI18n()
const visible = ref(false)
function show() {
  // Small-screen source buttons open the full-page dialog; a hover card would cover the reader.
  if (window.matchMedia('(max-width: 700px)').matches) return
  visible.value = true; emit('preview')
}
function hide() { visible.value = false }
function focus(event: FocusEvent) { if ((event.target as HTMLElement).matches(':focus-visible')) show() }
onMounted(() => window.addEventListener('scroll', hide, { passive: true, capture: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', hide, true))
</script>
<template>
  <el-popover
    :visible="visible"
    :width="300"
    placement="top"
    :show-after="0"
    :hide-after="0"
  >
    <template #reference>
      <button
        class="source-tag"
        :aria-label="`${name}, p${evidence.page}`"
        @mouseenter="show"
        @mouseleave="visible = false"
        @focus="focus"
        @blur="visible = false"
        @keydown.esc="visible = false"
        @click="visible = false; emit('open')"
      >
        {{ name }} · p{{ evidence.page }}
      </button>
    </template>
    <div
      @mouseenter="visible = true"
      @mouseleave="visible = false"
    >
      <strong>{{ props.name }} · p{{ evidence.page }}</strong><small v-if="evidence.origin === 'vision'"> · {{ t('review.visualDescription') }}</small><img
        v-if="image"
        :src="image"
        :alt="`${name}, p${evidence.page}`"
      ><blockquote>{{ evidence.quote }}</blockquote><span>{{ t('review.openOriginal') }}</span>
    </div>
  </el-popover>
</template>
<style scoped>.source-tag { border: 1px solid var(--cm-border-light); color: var(--cm-primary); background: var(--cm-bg-secondary); padding: .2rem .45rem; border-radius: 5px; margin: .3rem .3rem .3rem 0; cursor: pointer; font-size: .75rem; } img { width: 100%; margin-top: .5rem; } blockquote { margin: .5rem 0; font-size: .85rem; max-height: 150px; overflow: auto; }</style>
