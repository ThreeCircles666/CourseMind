<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

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
  username.value = ''
  nickname.value = ''
  password.value = ''
  router.push({ name: isLogin.value ? 'register' : 'login', query: route.query })
}
</script>

<template>
  <div class="auth-view">
    <!-- Language Switcher for Auth Pages -->
    <div class="auth-locale-switcher">
      <LocaleSwitcher />
    </div>
    
    <div class="auth-container">
      <!-- Left Panel - Branding -->
      <div class="auth-brand">
        <div class="brand-content">
          <div class="brand-logo">
            <div class="logo-icon">
              <el-icon :size="48">
                <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                  <path fill="currentColor" d="M832 384H576V128H192v768h640V384zm-26.496-64L640 154.496V320h165.504zM160 64h480l256 256v608a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32z"/>
                </svg>
              </el-icon>
            </div>
            <h1 class="brand-name">{{ t('common.appName') }}</h1>
            <p class="brand-tagline">{{ t('common.tagline') }}</p>
          </div>
          
          <div class="brand-features">
            <h2 class="features-title">{{ t('auth.brandTitle') }}</h2>
            <ul class="features-list">
              <li class="feature-item">
                <el-icon class="feature-icon" :size="20">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M406.656 706.944 195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.592 706.944z"/>
                  </svg>
                </el-icon>
                <span>{{ t('auth.feature1') }}</span>
              </li>
              <li class="feature-item">
                <el-icon class="feature-icon" :size="20">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M406.656 706.944 195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.592 706.944z"/>
                  </svg>
                </el-icon>
                <span>{{ t('auth.feature2') }}</span>
              </li>
              <li class="feature-item">
                <el-icon class="feature-icon" :size="20">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M406.656 706.944 195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.592 706.944z"/>
                  </svg>
                </el-icon>
                <span>{{ t('auth.feature3') }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Right Panel - Auth Form -->
      <div class="auth-form-panel">
        <div class="form-container">
          <div class="form-header">
            <h2 class="form-title">
              {{ isLogin ? t('auth.login') : t('auth.register') }}
            </h2>
            <p class="form-subtitle">
              {{ isLogin ? t('auth.loginSubtitle') : t('auth.registerSubtitle') }}
            </p>
          </div>

          <el-form
            class="auth-form"
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
                size="large"
                autocomplete="username"
              >
                <template #prefix>
                  <el-icon>
                    <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                      <path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384zm0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512zm320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0z"/>
                    </svg>
                  </el-icon>
                </template>
              </el-input>
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
                size="large"
                autocomplete="nickname"
              >
                <template #prefix>
                  <el-icon>
                    <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                      <path fill="currentColor" d="M288 320a224 224 0 1 0 448 0 224 224 0 1 0-448 0zm544 608H160a32 32 0 0 1-32-32v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 0 1-32 32z"/>
                    </svg>
                  </el-icon>
                </template>
              </el-input>
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
                size="large"
                :autocomplete="isLogin ? 'current-password' : 'new-password'"
                show-password
              >
                <template #prefix>
                  <el-icon>
                    <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                      <path fill="currentColor" d="M224 448a32 32 0 0 0-32 32v384a32 32 0 0 0 32 32h576a32 32 0 0 0 32-32V480a32 32 0 0 0-32-32H224zm0-64h576a96 96 0 0 1 96 96v384a96 96 0 0 1-96 96H224a96 96 0 0 1-96-96V480a96 96 0 0 1 96-96z"/>
                      <path fill="currentColor" d="M512 544a32 32 0 0 1 32 32v192a32 32 0 1 1-64 0V576a32 32 0 0 1 32-32zm192-160v-64a192 192 0 1 0-384 0v64h384zM512 64a256 256 0 0 1 256 256v128H256V320A256 256 0 0 1 512 64z"/>
                    </svg>
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-alert
              v-if="errorMessage"
              :title="errorMessage"
              type="error"
              :closable="false"
              style="margin-bottom: var(--cm-space-4)"
            />

            <el-button
              type="primary"
              size="large"
              :loading="auth.isSubmitting"
              native-type="submit"
              class="submit-button"
            >
              {{ isLogin ? t('auth.loginButton') : t('auth.registerButton') }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <p class="switch-mode">
              {{ isLogin ? t('auth.noAccount') : t('auth.hasAccount') }}
              <el-button
                text
                type="primary"
                @click="switchMode"
                :disabled="auth.isSubmitting"
              >
                {{ isLogin ? t('auth.goRegister') : t('auth.goLogin') }}
              </el-button>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-view {
  min-height: 100vh;
  background: var(--cm-bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--cm-space-6);
  position: relative;
}

.auth-locale-switcher {
  position: absolute;
  top: var(--cm-space-6);
  right: var(--cm-space-6);
  z-index: 10;
}

.auth-container {
  width: 100%;
  max-width: 1100px;
  min-height: 650px;
  background: var(--cm-bg-elevated);
  border-radius: var(--cm-radius-xl);
  box-shadow: var(--cm-shadow-xl);
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
}

/* Brand Panel */
.auth-brand {
  background: linear-gradient(135deg, var(--cm-primary) 0%, var(--cm-primary-dark) 100%);
  padding: var(--cm-space-12) var(--cm-space-10);
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: var(--cm-text-inverse);
}

.brand-content {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-12);
}

.brand-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--cm-space-4);
  text-align: center;
}

.logo-icon {
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--cm-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--cm-text-inverse);
}

.brand-name {
  font-size: var(--cm-text-4xl);
  font-weight: var(--cm-font-bold);
  margin: 0;
  color: var(--cm-text-inverse);
}

.brand-tagline {
  max-width: 360px;
  margin: var(--cm-space-3) auto 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--cm-text-base);
  line-height: var(--cm-leading-relaxed);
}

.brand-features {
  padding-top: var(--cm-space-8);
}

.features-title {
  font-size: var(--cm-text-2xl);
  font-weight: var(--cm-font-semibold);
  margin: 0 0 var(--cm-space-6) 0;
  color: var(--cm-text-inverse);
}

.features-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-4);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--cm-space-3);
  font-size: var(--cm-text-base);
  color: rgba(255, 255, 255, 0.95);
}

.feature-icon {
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.9);
}

/* Form Panel */
.auth-form-panel {
  padding: var(--cm-space-12) var(--cm-space-10);
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 400px;
}

.form-header {
  margin-bottom: var(--cm-space-8);
  text-align: center;
}

.form-title {
  font-size: var(--cm-text-3xl);
  font-weight: var(--cm-font-bold);
  color: var(--cm-text-primary);
  margin: 0 0 var(--cm-space-2) 0;
}

.form-subtitle {
  font-size: var(--cm-text-sm);
  color: var(--cm-text-secondary);
  margin: 0;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-1);
}

.auth-form :deep(.el-form-item__label) {
  font-weight: var(--cm-font-medium);
  color: var(--cm-text-primary);
  margin-bottom: var(--cm-space-2);
}

.auth-form :deep(.el-input__wrapper) {
  padding: var(--cm-space-3) var(--cm-space-4);
}

.submit-button {
  width: 100%;
  margin-top: var(--cm-space-4);
  font-weight: var(--cm-font-semibold);
}

.form-footer {
  margin-top: var(--cm-space-8);
  text-align: center;
}

.switch-mode {
  font-size: var(--cm-text-sm);
  color: var(--cm-text-secondary);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--cm-space-2);
}

/* Responsive */
@media (max-width: 968px) {
  .auth-locale-switcher {
    top: var(--cm-space-4);
    right: var(--cm-space-4);
  }

  .auth-container {
    grid-template-columns: 1fr;
    max-width: 480px;
  }

  .auth-brand {
    display: none;
  }

  .auth-form-panel {
    padding: var(--cm-space-8) var(--cm-space-6);
  }
}

@media (max-width: 480px) {
  .auth-view {
    padding: var(--cm-space-4);
  }

  .auth-form-panel {
    padding: var(--cm-space-6) var(--cm-space-4);
  }

  .form-title {
    font-size: var(--cm-text-2xl);
  }
}
</style>
