<script setup lang="ts">
import { watch } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { SUPPORTED_LOCALES, LOCALE_NAMES, setLocale, type SupportedLocale } from '@/i18n'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { locale } = useI18n()

function handleLocaleChange(newLocale: SupportedLocale) {
  setLocale(newLocale)
}

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
    <div class="global-locale-switcher">
      <el-select
        :model-value="locale"
        size="small"
        @change="handleLocaleChange"
      >
        <el-option
          v-for="loc in SUPPORTED_LOCALES"
          :key="loc"
          :label="LOCALE_NAMES[loc]"
          :value="loc"
        />
      </el-select>
    </div>
    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.global-locale-switcher {
  position: fixed;
  top: 16px;
  right: 24px;
  z-index: 3000;
  width: 132px;
}

.global-locale-switcher :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(8px);
}

@media (max-width: 768px) {
  .global-locale-switcher {
    top: 10px;
    right: 12px;
    width: 118px;
  }
}
</style>
