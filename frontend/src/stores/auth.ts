import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import { setAccessToken, setUnauthorizedHandler } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<authApi.User | null>(null)
  const isRestoring = ref(true)
  const isSubmitting = ref(false)
  const isAuthenticated = computed(() => user.value !== null)

  function applyAuth(data: { access_token: string; user: authApi.User }) {
    setAccessToken(data.access_token)
    user.value = data.user
  }

  function clearAuth() {
    setAccessToken(null)
    user.value = null
  }

  async function restore() {
    try {
      applyAuth(await authApi.refresh())
    } catch {
      clearAuth()
    } finally {
      isRestoring.value = false
    }
  }

  async function signIn(username: string, password: string) {
    isSubmitting.value = true
    try {
      applyAuth(await authApi.login(username, password))
    } finally {
      isSubmitting.value = false
    }
  }

  async function signUp(username: string, nickname: string, password: string) {
    isSubmitting.value = true
    try {
      applyAuth(await authApi.register(username, nickname, password))
    } finally {
      isSubmitting.value = false
    }
  }

  async function signOut() {
    try {
      if (user.value) await authApi.logout()
    } finally {
      clearAuth()
    }
  }

  setUnauthorizedHandler(clearAuth)
  return { user, isRestoring, isSubmitting, isAuthenticated, restore, signIn, signUp, signOut }
})
