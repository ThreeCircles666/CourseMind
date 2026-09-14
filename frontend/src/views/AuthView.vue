<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()

const mode = computed(() => (route.name === 'register' ? 'register' : 'login'))
const isLogin = computed(() => mode.value === 'login')

const username = ref('')
const nickname = ref('')
const password = ref('')
const errorMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''
  if (!username.value.trim() || !password.value) {
    errorMessage.value = t('auth.fillAllFields')
    return
  }
  if (!isLogin.value && !nickname.value.trim()) {
    errorMessage.value = t('auth.fillNickname')
    return
  }
  if (password.value.length < 8) {
    errorMessage.value = t('auth.passwordTooShort')
    return
  }
  try {
    if (isLogin.value) {
      await auth.signIn(username.value, password.value)
      ElMessage.success(t('auth.loginSuccess'))
    } else {
      await auth.signUp(username.value, nickname.value, password.value)
      ElMessage.success(t('auth.registerSuccess'))
    }
    const redirect = (route.query.redirect as string) || '/'
    if (redirect.startsWith('/') && !redirect.startsWith('//')) {
      await router.replace(redirect)
    } else {
      await router.replace('/')
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('auth.operationFailed')
  }
}

function switchMode() {
  errorMessage.value = ''
  router.push({ name: isLogin.value ? 'register' : 'login', query: route.query })
}
</script>

<template>
  <div class="auth">
    <el-card
      class="auth__card"
      shadow="hover"
    >
      <template #header>
        <h2 class="auth__title">
          {{ isLogin ? t('auth.login') : t('auth.register') }}
        </h2>
      </template>

      <el-form
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item
          :label="t('auth.username')"
          required
        >
          <el-input
            v-model="username"
            :placeholder="t('auth.usernamePlaceholder')"
            :disabled="auth.isSubmitting"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item
          v-if="!isLogin"
          :label="t('auth.nickname')"
          required
        >
          <el-input
            v-model="nickname"
            :placeholder="t('auth.nicknamePlaceholder')"
            :disabled="auth.isSubmitting"
            autocomplete="nickname"
          />
        </el-form-item>

        <el-form-item
          :label="t('auth.password')"
          required
        >
          <el-input
            v-model="password"
            type="password"
            :placeholder="t('auth.passwordPlaceholder')"
            :disabled="auth.isSubmitting"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
            show-password
          />
        </el-form-item>

        <el-alert
          v-if="errorMessage"
          type="error"
          :closable="false"
          show-icon
          class="auth__error"
        >
          {{ errorMessage }}
        </el-alert>

        <el-button
          type="primary"
          native-type="submit"
          :loading="auth.isSubmitting"
          class="auth__submit"
        >
          {{ isLogin ? t('auth.loginButton') : t('auth.registerButton') }}
        </el-button>

        <div class="auth__switch">
          <el-button
            link
            @click="switchMode"
          >
            {{ isLogin ? t('auth.switchToRegister') : t('auth.switchToLogin') }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.auth {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth__card {
  width: 100%;
  max-width: 400px;
}

.auth__title {
  margin: 0;
  font-size: 24px;
  text-align: center;
}

.auth__error {
  margin-bottom: 16px;
}

.auth__submit {
  width: 100%;
}

.auth__switch {
  margin-top: 16px;
  text-align: center;
}
</style>
