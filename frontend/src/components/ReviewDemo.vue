<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Demo } from '@/api/review'
import ReviewMath from './ReviewMath.vue'
const props = defineProps<{ demo: Demo }>()
const { t } = useI18n()
const step = ref(0)
const x = ref(props.demo.minimum)
const y = computed(() => props.demo.a * x.value + props.demo.b)
const points = computed(() => {
  const { a, b, minimum, maximum } = props.demo
  const low = Math.min(a * minimum + b, a * maximum + b), high = Math.max(a * minimum + b, a * maximum + b)
  const py = (value: number) => 130 - (value - low) / (high - low || 1) * 100
  return { line: `30,${py(a * minimum + b)} 270,${py(a * maximum + b)}`, x: 30 + (x.value - minimum) / (maximum - minimum) * 240, y: py(y.value) }
})
</script>
<template>
  <div class="review-demo">
    <h4>{{ demo.title }}</h4>
    <p class="demo-note">
      {{ demo.illustrative ? t('review.illustrative') : t('review.sourceValues') }}
    </p>
    <template v-if="demo.kind === 'steps'">
      <p>{{ t('review.step') }} {{ step + 1 }} / {{ demo.steps.length }}</p>
      <ReviewMath :text="demo.steps[step]" />
      <div class="controls">
        <button
          :disabled="step === 0"
          @click="step--"
        >
          {{ t('review.previous') }}
        </button><button
          :disabled="step === demo.steps.length - 1"
          @click="step++"
        >
          {{ t('review.next') }}
        </button><button @click="step = 0">
          {{ t('review.reset') }}
        </button>
      </div>
    </template>
    <template v-else>
      <ReviewMath
        :text="`y = ${demo.a}x ${demo.b < 0 ? '-' : '+'} ${Math.abs(demo.b)}`"
        formula
      />
      <svg
        viewBox="0 0 300 160"
        role="img"
        :aria-label="`${demo.title}; x=${x}; y=${y}`"
      >
        <path
          d="M30 15V135H285"
          fill="none"
          stroke="currentColor"
        />
        <polyline
          :points="points.line"
          fill="none"
          stroke="var(--cm-primary, #6366f1)"
          stroke-width="2"
        />
        <circle
          :cx="points.x"
          :cy="points.y"
          r="5"
          fill="currentColor"
        /><text
          x="278"
          y="155"
        >x</text><text
          x="10"
          y="20"
        >y</text>
      </svg>
      <label>x = {{ x.toFixed(2) }}<input
        v-model.number="x"
        type="range"
        :min="demo.minimum"
        :max="demo.maximum"
        :step="(demo.maximum - demo.minimum) / 100"
      ></label>
      <output>y = {{ y.toFixed(4) }}</output><button @click="x = demo.minimum">
        {{ t('review.reset') }}
      </button>
    </template>
  </div>
</template>
<style scoped>.review-demo { border: 1px solid var(--cm-border-light); padding: 1rem; border-radius: 10px; margin: 1rem 0; } h4 { margin: 0 0 .5rem; } .demo-note { color: var(--cm-text-secondary); font-size: .85rem; } svg { display: block; width: min(100%, 360px); } input { width: 100%; } .controls { display: flex; gap: .5rem; margin-top: 1rem; } button { padding: .4rem .8rem; } output { margin-right: 1rem; }</style>
