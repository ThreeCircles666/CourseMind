<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const quickActions = [
  {
    icon: 'search',
    title: t('home.knowledgeAsk.title'),
    desc: t('home.knowledgeAsk.desc'),
    route: '/knowledge-ask',
    color: '#8B5CF6',
  },
  {
    icon: 'canvas',
    title: t('home.learningCanvas.title'),
    desc: t('home.learningCanvas.desc'),
    route: '/canvas',
    color: '#F59E0B',
  },
  {
    icon: 'chat',
    title: t('home.chat.title'),
    desc: t('home.chat.desc'),
    route: '/chat',
    color: '#3B82F6',
  },
  {
    icon: 'document',
    title: t('home.documents.title'),
    desc: t('home.documents.desc'),
    route: '/documents',
    color: '#10B981',
  },
]

function navigateTo(route: string) {
  router.push(route)
}

function handleCommand(command: string) {
  if (command === 'logout') {
    auth.signOut()
    router.push('/login')
  }
}
</script>

<template>
  <div class="index-view">
    <!-- Top Navigation -->
    <header class="index-header">
      <div class="cm-container">
        <div class="header-content">
          <div class="brand">
            <h1 class="brand-name">{{ t('common.appName') }}</h1>
          </div>
          
          <div class="header-actions">
            <LocaleSwitcher />
            
            <el-dropdown @command="handleCommand">
              <div class="user-menu">
                <el-avatar
                  :size="36"
                  class="user-avatar"
                >
                  {{ auth.user?.nickname?.charAt(0) || 'U' }}
                </el-avatar>
                <span class="user-name">{{ auth.user?.nickname }}</span>
                <el-icon class="dropdown-icon">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M831.872 340.864 512 652.672 192.128 340.864a30.592 30.592 0 0 0-42.752 0 29.12 29.12 0 0 0 0 41.6L489.664 714.24a32 32 0 0 0 44.672 0l340.288-331.712a29.12 29.12 0 0 0 0-41.728 30.592 30.592 0 0 0-42.752 0z"/>
                  </svg>
                </el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">
                    {{ t('common.logout') }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="index-main">
      <div class="cm-container">
        <!-- Welcome Section -->
        <section class="welcome-section">
          <h2 class="welcome-title">
            {{ t('common.welcome', { nickname: auth.user?.nickname }) }}
          </h2>
          <p class="welcome-subtitle">
            {{ t('common.tagline') }}
          </p>
        </section>

        <!-- Quick Actions Grid -->
        <section class="quick-actions">
          <div class="actions-grid">
            <div
              v-for="action in quickActions"
              :key="action.route"
              class="action-card cm-card"
              @click="navigateTo(action.route)"
            >
              <div class="action-icon" :style="{ color: action.color }">
                <el-icon :size="32">
                  <svg v-if="action.icon === 'search'" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="m795.904 750.72 124.992 124.928a32 32 0 0 1-45.248 45.248L750.656 795.904a416 416 0 1 1 45.248-45.248zM480 832a352 352 0 1 0 0-704 352 352 0 0 0 0 704z"/>
                  </svg>
                  <svg v-else-if="action.icon === 'canvas'" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M160 256h256a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V288a32 32 0 0 1 32-32zm0 384h256a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V672a32 32 0 0 1 32-32zm384-384h320a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H544a32 32 0 0 1-32-32V288a32 32 0 0 1 32-32zm0 384h320a32 32 0 0 1 32 32v256a32 32 0 0 1-32 32H544a32 32 0 0 1-32-32V672a32 32 0 0 1 32-32z"/>
                  </svg>
                  <svg v-else-if="action.icon === 'chat'" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M273.536 736H800a64 64 0 0 0 64-64V256a64 64 0 0 0-64-64H224a64 64 0 0 0-64 64v570.88L273.536 736zM296 800 147.968 918.4A32 32 0 0 1 96 893.44V256a128 128 0 0 1 128-128h576a128 128 0 0 1 128 128v416a128 128 0 0 1-128 128H296z"/>
                  </svg>
                  <svg v-else-if="action.icon === 'document'" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M832 384H576V128H192v768h640V384zm-26.496-64L640 154.496V320h165.504zM160 64h480l256 256v608a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32z"/>
                  </svg>
                </el-icon>
              </div>
              <div class="action-content">
                <h3 class="action-title">{{ action.title }}</h3>
                <p class="action-desc">{{ action.desc }}</p>
              </div>
              <div class="action-arrow">
                <el-icon>
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M340.864 149.312a30.592 30.592 0 0 0 0 42.752L652.736 512 340.864 831.872a30.592 30.592 0 0 0 0 42.752 29.12 29.12 0 0 0 41.728 0L714.24 534.336a32 32 0 0 0 0-44.672L382.592 149.376a29.12 29.12 0 0 0-41.728 0z"/>
                  </svg>
                </el-icon>
              </div>
            </div>
          </div>
        </section>

        <!-- Quick Link to About -->
        <section class="about-link">
          <div class="about-card cm-card" @click="navigateTo('/about')">
            <el-icon :size="24" color="var(--cm-gray-500)">
              <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/>
                <path fill="currentColor" d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z"/>
              </svg>
            </el-icon>
            <span class="about-text">{{ t('home.about.title') }}</span>
            <el-icon class="about-arrow">
              <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path fill="currentColor" d="M340.864 149.312a30.592 30.592 0 0 0 0 42.752L652.736 512 340.864 831.872a30.592 30.592 0 0 0 0 42.752 29.12 29.12 0 0 0 41.728 0L714.24 534.336a32 32 0 0 0 0-44.672L382.592 149.376a29.12 29.12 0 0 0-41.728 0z"/>
              </svg>
            </el-icon>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.index-view {
  min-height: 100vh;
  background: var(--cm-bg-secondary);
}

/* Header */
.index-header {
  background: var(--cm-bg-elevated);
  border-bottom: 1px solid var(--cm-border-light);
  padding: var(--cm-space-5) 0;
  position: sticky;
  top: 0;
  z-index: var(--cm-z-sticky);
  backdrop-filter: blur(8px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  flex: 1;
}

.brand-name {
  font-size: var(--cm-text-2xl);
  font-weight: var(--cm-font-bold);
  color: var(--cm-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--cm-space-4);
}

.user-menu {
  display: flex;
  align-items: center;
  gap: var(--cm-space-3);
  padding: var(--cm-space-2) var(--cm-space-3);
  border-radius: var(--cm-radius-md);
  cursor: pointer;
  transition: background var(--cm-transition-fast);
}

.user-menu:hover {
  background: var(--cm-bg-tertiary);
}

.user-avatar {
  background: linear-gradient(135deg, var(--cm-primary-light), var(--cm-primary));
  color: var(--cm-text-inverse);
  font-weight: var(--cm-font-semibold);
}

.user-name {
  font-size: var(--cm-text-sm);
  font-weight: var(--cm-font-medium);
  color: var(--cm-text-primary);
}

.dropdown-icon {
  color: var(--cm-text-tertiary);
  font-size: var(--cm-text-sm);
}

/* Main Content */
.index-main {
  padding: var(--cm-space-12) 0 var(--cm-space-16);
}

.welcome-section {
  text-align: center;
  margin-bottom: var(--cm-space-12);
}

.welcome-title {
  font-size: var(--cm-text-4xl);
  font-weight: var(--cm-font-bold);
  color: var(--cm-text-primary);
  margin: 0 0 var(--cm-space-3) 0;
}

.welcome-subtitle {
  font-size: var(--cm-text-lg);
  color: var(--cm-text-secondary);
  margin: 0;
}

/* Quick Actions */
.quick-actions {
  margin-bottom: var(--cm-space-12);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--cm-space-6);
}

.action-card {
  padding: var(--cm-space-6);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-4);
  position: relative;
  transition: all var(--cm-transition-base);
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--cm-shadow-lg);
}

.action-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--cm-radius-lg);
  background: var(--cm-bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-content {
  flex: 1;
}

.action-title {
  font-size: var(--cm-text-xl);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
  margin: 0 0 var(--cm-space-2) 0;
}

.action-desc {
  font-size: var(--cm-text-sm);
  color: var(--cm-text-secondary);
  line-height: var(--cm-leading-relaxed);
  margin: 0;
}

.action-arrow {
  position: absolute;
  top: var(--cm-space-6);
  right: var(--cm-space-6);
  color: var(--cm-text-tertiary);
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--cm-transition-base);
}

.action-card:hover .action-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* About Link */
.about-link {
  max-width: 600px;
  margin: 0 auto;
}

.about-card {
  padding: var(--cm-space-4) var(--cm-space-5);
  display: flex;
  align-items: center;
  gap: var(--cm-space-4);
  cursor: pointer;
  transition: all var(--cm-transition-base);
}

.about-card:hover {
  box-shadow: var(--cm-shadow-md);
}

.about-text {
  flex: 1;
  font-size: var(--cm-text-base);
  color: var(--cm-text-secondary);
  font-weight: var(--cm-font-medium);
}

.about-arrow {
  color: var(--cm-text-tertiary);
  font-size: var(--cm-text-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .index-header {
    padding: var(--cm-space-4) 0;
  }

  .brand-tagline {
    display: none;
  }

  .user-name {
    display: none;
  }

  .index-main {
    padding: var(--cm-space-8) 0 var(--cm-space-12);
  }

  .welcome-title {
    font-size: var(--cm-text-3xl);
  }

  .welcome-subtitle {
    font-size: var(--cm-text-base);
  }

  .actions-grid {
    grid-template-columns: 1fr;
    gap: var(--cm-space-4);
  }
}
</style>
