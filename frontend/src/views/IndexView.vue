<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function goToChat() {
  router.push('/chat')
}

function goToAbout() {
  router.push('/about')
}

function handleLogout() {
  auth.signOut()
  router.push('/login')
}
</script>

<template>
  <div class="index-view">
    <el-container class="index-container">
      <el-header class="index-header">
        <div class="header-content">
          <h1 class="app-title">CourseMind</h1>
          <el-dropdown @command="handleLogout">
            <el-button text>
              <el-avatar :size="32" class="user-avatar">
                {{ auth.user?.nickname?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="username">{{ auth.user?.nickname }}</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="index-main">
        <div class="welcome-section">
          <div class="welcome-card">
            <el-icon :size="64" color="#409EFF" class="welcome-icon">
              <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/>
                <path fill="currentColor" d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z"/>
              </svg>
            </el-icon>
            <h2 class="welcome-title">欢迎回来，{{ auth.user?.nickname }}！</h2>
            <p class="welcome-subtitle">选择下方功能开始使用 CourseMind</p>
          </div>

          <div class="features-grid">
            <el-card shadow="hover" class="feature-card" @click="goToChat">
              <div class="feature-content">
                <el-icon :size="48" color="#409EFF" class="feature-icon">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M273.536 736H800a64 64 0 0 0 64-64V256a64 64 0 0 0-64-64H224a64 64 0 0 0-64 64v570.88L273.536 736zM296 800 147.968 918.4A32 32 0 0 1 96 893.44V256a128 128 0 0 1 128-128h576a128 128 0 0 1 128 128v416a128 128 0 0 1-128 128H296z"/>
                    <path fill="currentColor" d="M512 499.2a51.2 51.2 0 1 1 0-102.4 51.2 51.2 0 0 1 0 102.4zm192 0a51.2 51.2 0 1 1 0-102.4 51.2 51.2 0 0 1 0 102.4zm-384 0a51.2 51.2 0 1 1 0-102.4 51.2 51.2 0 0 1 0 102.4z"/>
                  </svg>
                </el-icon>
                <h3 class="feature-title">AI 对话</h3>
                <p class="feature-desc">与智能助手进行自然对话，获取学习辅导和问题解答</p>
                <el-button type="primary" class="feature-button">开始对话</el-button>
              </div>
            </el-card>

            <el-card shadow="hover" class="feature-card" @click="goToAbout">
              <div class="feature-content">
                <el-icon :size="48" color="#67C23A" class="feature-icon">
                  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/>
                    <path fill="currentColor" d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z"/>
                  </svg>
                </el-icon>
                <h3 class="feature-title">关于项目</h3>
                <p class="feature-desc">了解 CourseMind 的功能介绍和使用说明</p>
                <el-button type="success" class="feature-button">查看详情</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.index-view {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.index-container {
  height: 100%;
}

.index-header {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.app-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-avatar {
  margin-right: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.username {
  color: white;
  font-weight: 500;
  margin-left: 4px;
}

.index-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.welcome-section {
  max-width: 900px;
  width: 100%;
}

.welcome-card {
  text-align: center;
  margin-bottom: 48px;
  color: white;
}

.welcome-icon {
  margin-bottom: 20px;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 12px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.welcome-subtitle {
  font-size: 16px;
  margin: 0;
  opacity: 0.9;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.feature-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 16px;
  border: none;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.feature-content {
  text-align: center;
  padding: 20px;
}

.feature-icon {
  margin-bottom: 16px;
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
}

.feature-desc {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0 0 20px 0;
  line-height: 1.6;
}

.feature-button {
  width: 100%;
}
</style>
