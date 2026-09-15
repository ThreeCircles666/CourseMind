<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

const store = useAppStore()
const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()
const { teamName, backendStatus, health, errorMessage } = storeToRefs(store)

async function handleSignOut() {
  await auth.signOut()
  await router.replace({ name: 'login' })
}

onMounted(() => {
  store.checkBackend()
})
</script>

<template>
  <div class="about-view">
    <div class="about-container cm-container">
      <!-- Header -->
      <header class="about-header">
        <div class="header-content">
          <div>
            <h1 class="about-title">{{ t('about.title') }}</h1>
            <p class="about-tagline">{{ t('about.tagline') }}</p>
          </div>
          <div class="header-actions">
            <LocaleSwitcher />
            <el-button
              link
              @click="handleSignOut"
            >
              {{ t('common.logout') }}
            </el-button>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <div class="about-content">
        <!-- Introduction -->
        <section class="about-section">
          <h2 class="section-title">{{ t('about.intro.title') }}</h2>
          <p class="section-text">
            {{ t('about.intro.description') }}
          </p>
        </section>

        <!-- Core Features -->
        <section class="about-section">
          <h2 class="section-title">{{ t('about.features.title') }}</h2>
          <div class="features-grid">
            <div class="feature-card cm-card">
              <div class="feature-icon">
                <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                  <path fill="currentColor" d="M832 384H576V128H192v768h640V384zm-26.496-64L640 154.496V320h165.504zM160 64h480l256 256v608a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32z"/>
                </svg>
              </div>
              <h3 class="feature-title">{{ t('about.features.documents.title') }}</h3>
              <p class="feature-desc">{{ t('about.features.documents.description') }}</p>
            </div>

            <div class="feature-card cm-card">
              <div class="feature-icon">
                <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                  <path fill="currentColor" d="m795.904 750.72 124.992 124.928a32 32 0 0 1-45.248 45.248L750.656 795.904a416 416 0 1 1 45.248-45.248zM480 832a352 352 0 1 0 0-704 352 352 0 0 0 0 704z"/>
                </svg>
              </div>
              <h3 class="feature-title">{{ t('about.features.knowledgeAsk.title') }}</h3>
              <p class="feature-desc">{{ t('about.features.knowledgeAsk.description') }}</p>
            </div>

            <div class="feature-card cm-card">
              <div class="feature-icon">
                <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                  <path fill="currentColor" d="M160 256h256a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V288a32 32 0 0 1 32-32zm0 384h256a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V672a32 32 0 0 1 32-32zm384-384h320a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H544a32 32 0 0 1-32-32V288a32 32 0 0 1 32-32zm0 384h320a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H544a32 32 0 0 1-32-32V672a32 32 0 0 1 32-32z"/>
                </svg>
              </div>
              <h3 class="feature-title">{{ t('about.features.learningCanvas.title') }}</h3>
              <p class="feature-desc">{{ t('about.features.learningCanvas.description') }}</p>
            </div>

            <div class="feature-card cm-card">
              <div class="feature-icon">
                <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                  <path fill="currentColor" d="M273.536 736H800a64 64 0 0 0 64-64V256a64 64 0 0 0-64-64H224a64 64 0 0 0-64 64v570.88L273.536 736zM296 800 147.968 918.4A32 32 0 0 1 96 893.44V256a128 128 0 0 1 128-128h576a128 128 0 0 1 128 128v416a128 128 0 0 1-128 128H296z"/>
                </svg>
              </div>
              <h3 class="feature-title">{{ t('about.features.aiChat.title') }}</h3>
              <p class="feature-desc">{{ t('about.features.aiChat.description') }}</p>
            </div>
          </div>
        </section>

        <!-- Tech Stack -->
        <section class="about-section">
          <h2 class="section-title">{{ t('about.techStack.title') }}</h2>
          <div class="tech-stack">
            <div class="tech-category">
              <h3 class="tech-category-title">{{ t('about.techStack.frontend') }}</h3>
              <div class="tech-tags">
                <el-tag>Vue 3</el-tag>
                <el-tag>TypeScript</el-tag>
                <el-tag>Element Plus</el-tag>
                <el-tag>Vite</el-tag>
                <el-tag>Pinia</el-tag>
              </div>
            </div>
            <div class="tech-category">
              <h3 class="tech-category-title">{{ t('about.techStack.backend') }}</h3>
              <div class="tech-tags">
                <el-tag>FastAPI</el-tag>
                <el-tag>Python</el-tag>
                <el-tag>PostgreSQL</el-tag>
                <el-tag>阿里云百炼</el-tag>
              </div>
            </div>
          </div>
        </section>

        <!-- System Status -->
        <section class="about-section">
          <h2 class="section-title">{{ t('about.systemStatus.title') }}</h2>
          <div class="status-grid">
            <div class="status-card cm-card">
              <div class="status-label">{{ t('about.systemStatus.frontendStatus') }}</div>
              <el-tag type="success" size="large">{{ t('about.systemStatus.running') }}</el-tag>
            </div>
            
            <div class="status-card cm-card">
              <div class="status-label">{{ t('about.systemStatus.backendConnection') }}</div>
              <el-tag
                v-if="backendStatus === 'loading'"
                type="warning"
                size="large"
              >
                {{ t('about.systemStatus.connecting') }}
              </el-tag>
              <el-tag
                v-else-if="backendStatus === 'success'"
                type="success"
                size="large"
              >
                {{ t('about.systemStatus.connected') }}
              </el-tag>
              <el-tag
                v-else-if="backendStatus === 'error'"
                type="danger"
                size="large"
              >
                {{ t('about.systemStatus.failed') }}
              </el-tag>
              <el-tag
                v-else
                type="info"
                size="large"
              >
                {{ t('about.systemStatus.untested') }}
              </el-tag>
            </div>

            <div
              v-if="backendStatus === 'success' && health"
              class="status-card cm-card"
            >
              <div class="status-label">{{ t('about.systemStatus.backendVersion') }}</div>
              <div class="status-value">{{ health.version }}</div>
            </div>
          </div>

          <div class="status-actions">
            <el-button
              type="primary"
              :loading="backendStatus === 'loading'"
              @click="store.checkBackend()"
            >
              {{ t('about.systemStatus.testConnection') }}
            </el-button>
          </div>

          <el-alert
            v-if="backendStatus === 'error'"
            class="status-error"
            type="error"
            :closable="false"
            show-icon
            :title="t('about.systemStatus.errorTitle')"
          >
            <p>{{ t('about.systemStatus.errorHints') }}</p>
            <ul>
              <li>{{ t('about.systemStatus.errorHint1') }}</li>
              <li>{{ t('about.systemStatus.errorHint2') }}</li>
            </ul>
            <p
              v-if="errorMessage"
              class="error-detail"
            >
              {{ t('about.systemStatus.errorDetail', { message: errorMessage }) }}
            </p>
          </el-alert>
        </section>

        <!-- Quick Actions -->
        <section class="about-section">
          <h2 class="section-title">{{ t('about.quickStart.title') }}</h2>
          <div class="quick-actions">
            <el-button
              type="primary"
              size="large"
              @click="$router.push('/documents')"
            >
              {{ t('about.quickStart.uploadDocuments') }}
            </el-button>
            <el-button
              size="large"
              @click="$router.push('/knowledge-ask')"
            >
              {{ t('about.quickStart.knowledgeAsk') }}
            </el-button>
            <el-button
              size="large"
              @click="$router.push('/canvas')"
            >
              {{ t('about.quickStart.learningCanvas') }}
            </el-button>
            <el-button
              size="large"
              @click="$router.push('/chat')"
            >
              {{ t('about.quickStart.aiChat') }}
            </el-button>
          </div>
        </section>

        <!-- Footer -->
        <footer class="about-footer">
          <p>{{ t('about.footer.version', { team: teamName }) }}</p>
          <p>{{ t('about.footer.welcome', { nickname: auth.user?.nickname }) }}</p>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.about-view {
  min-height: 100vh;
  background: var(--cm-bg-secondary);
  padding: var(--cm-space-8) 0;
}

.about-container {
  max-width: 1000px;
}

.about-header {
  background: var(--cm-bg-elevated);
  border-radius: var(--cm-radius-xl);
  padding: var(--cm-space-8);
  margin-bottom: var(--cm-space-8);
  box-shadow: var(--cm-shadow-md);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--cm-space-4);
}

.about-title {
  margin: 0 0 var(--cm-space-2) 0;
  font-size: var(--cm-text-4xl);
  font-weight: var(--cm-font-bold);
  color: var(--cm-primary);
}

.about-tagline {
  margin: 0;
  font-size: var(--cm-text-lg);
  color: var(--cm-text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--cm-space-3);
}

.about-content {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-8);
}

.about-section {
  background: var(--cm-bg-elevated);
  border-radius: var(--cm-radius-xl);
  padding: var(--cm-space-8);
  box-shadow: var(--cm-shadow-sm);
}

.section-title {
  margin: 0 0 var(--cm-space-6) 0;
  font-size: var(--cm-text-2xl);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
  border-bottom: 2px solid var(--cm-primary-light);
  padding-bottom: var(--cm-space-3);
}

.section-text {
  margin: 0;
  font-size: var(--cm-text-base);
  line-height: var(--cm-leading-relaxed);
  color: var(--cm-text-secondary);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--cm-space-5);
}

.feature-card {
  padding: var(--cm-space-6);
  text-align: center;
  transition: all var(--cm-transition-base);
  border: 1px solid var(--cm-border-light);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--cm-shadow-lg);
  border-color: var(--cm-primary-light);
}

.feature-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--cm-space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--cm-primary-light);
  border-radius: var(--cm-radius-full);
  color: var(--cm-primary);
}

.feature-icon svg {
  width: 32px;
  height: 32px;
}

.feature-title {
  margin: 0 0 var(--cm-space-2) 0;
  font-size: var(--cm-text-lg);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
}

.feature-desc {
  margin: 0;
  font-size: var(--cm-text-sm);
  color: var(--cm-text-secondary);
  line-height: var(--cm-leading-relaxed);
}

.tech-stack {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-6);
}

.tech-category {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-3);
}

.tech-category-title {
  margin: 0;
  font-size: var(--cm-text-lg);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cm-space-2);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--cm-space-4);
  margin-bottom: var(--cm-space-4);
}

.status-card {
  padding: var(--cm-space-5);
  text-align: center;
  border: 1px solid var(--cm-border-light);
}

.status-label {
  font-size: var(--cm-text-sm);
  color: var(--cm-text-tertiary);
  margin-bottom: var(--cm-space-2);
  font-weight: var(--cm-font-medium);
}

.status-value {
  font-size: var(--cm-text-xl);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
}

.status-actions {
  display: flex;
  justify-content: center;
  margin-bottom: var(--cm-space-4);
}

.status-error {
  margin-top: var(--cm-space-4);
}

.status-error ul {
  margin: var(--cm-space-2) 0;
  padding-left: var(--cm-space-5);
}

.status-error li {
  margin: var(--cm-space-1) 0;
}

.error-detail {
  margin-top: var(--cm-space-2);
  font-size: var(--cm-text-sm);
  word-break: break-all;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cm-space-3);
  justify-content: center;
}

.about-footer {
  text-align: center;
  padding: var(--cm-space-8) 0 var(--cm-space-4);
  color: var(--cm-text-tertiary);
  font-size: var(--cm-text-sm);
}

.about-footer p {
  margin: var(--cm-space-1) 0;
}

@media (max-width: 768px) {
  .about-view {
    padding: var(--cm-space-4) 0;
  }

  .about-header,
  .about-section {
    padding: var(--cm-space-5);
    border-radius: var(--cm-radius-lg);
  }

  .about-title {
    font-size: var(--cm-text-3xl);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .quick-actions {
    flex-direction: column;
  }

  .quick-actions .el-button {
    width: 100%;
  }
}
</style>
