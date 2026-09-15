<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES, LOCALE_NAMES, setLocale, type SupportedLocale } from '@/i18n'

const { locale } = useI18n()

function handleLocaleChange(newLocale: SupportedLocale) {
  setLocale(newLocale)
}
</script>

<template>
  <el-select
    :model-value="locale"
    size="small"
    class="locale-switcher"
    @change="handleLocaleChange"
  >
    <el-option
      v-for="loc in SUPPORTED_LOCALES"
      :key="loc"
      :label="LOCALE_NAMES[loc]"
      :value="loc"
    />
  </el-select>
</template>

<style scoped>
.locale-switcher {
  width: 110px;
}

.locale-switcher :deep(.el-input__wrapper) {
  background: var(--cm-bg-elevated);
  box-shadow: var(--cm-shadow-sm);
  border: 1px solid var(--cm-border-light);
  transition: all var(--cm-transition-fast);
}

.locale-switcher :deep(.el-input__wrapper):hover {
  border-color: var(--cm-primary-light);
  box-shadow: var(--cm-shadow-md);
}
</style>
