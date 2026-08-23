import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchHealth, type HealthResponse } from '@/api/health'

export type BackendStatus = 'idle' | 'loading' | 'success' | 'error'

export const useAppStore = defineStore('app', () => {
  const projectName = ref('AI 教学辅助平台')
  const teamName = ref('YWP Labs')

  const backendStatus = ref<BackendStatus>('idle')
  const health = ref<HealthResponse | null>(null)
  const errorMessage = ref('')

  async function checkBackend() {
    backendStatus.value = 'loading'
    errorMessage.value = ''
    health.value = null
    try {
      health.value = await fetchHealth()
      backendStatus.value = 'success'
    } catch (error) {
      backendStatus.value = 'error'
      errorMessage.value = error instanceof Error ? error.message : String(error)
    }
  }

  return {
    projectName,
    teamName,
    backendStatus,
    health,
    errorMessage,
    checkBackend,
  }
})
