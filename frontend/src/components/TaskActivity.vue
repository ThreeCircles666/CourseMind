<script setup lang="ts">
defineProps<{ label: string; elapsed: string }>()
</script>

<template>
  <div class="task-activity">
    <span
      class="task-activity__indicator"
      aria-hidden="true"
    />
    <span
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >{{ label }}</span>
    <small
      class="task-activity__elapsed"
      aria-live="off"
    >{{ elapsed }}</small>
  </div>
</template>

<style scoped>
.task-activity { display: flex; align-items: center; flex-wrap: wrap; gap: .7rem; padding: .3rem 0 1rem; line-height: 1.7; color: var(--cm-text-primary); }
.task-activity__indicator { width: .6rem; height: .6rem; flex: 0 0 auto; border-radius: 50%; background: var(--cm-primary); animation: activity-pulse 1.4s ease-in-out infinite; }
.task-activity__elapsed { color: var(--cm-text-secondary); margin-left: auto; white-space: nowrap; }
@keyframes activity-pulse { 50% { opacity: .3; } }
@media(prefers-reduced-motion:reduce) { .task-activity__indicator { animation: none; } }
</style>
