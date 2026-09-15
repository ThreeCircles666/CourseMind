<script setup lang="ts">
import { watch } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

watch(
  () => auth.isAuthenticated,
  (isAuthenticated) => {
    if (!isAuthenticated && route.meta.requiresAuth) {
      router.replace({ name: 'login', query: { redirect: route.fullPath } })
    }
  },
)
</script>

<template>
  <div class="app-shell">
    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--cm-bg-secondary);
}
</style>
