<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const store = useAppStore()
const auth = useAuthStore()
const router = useRouter()
const { projectName, teamName, backendStatus, health, errorMessage } = storeToRefs(store)

async function handleSignOut() {
  await auth.signOut()
  await router.replace({ name: 'login' })
}

onMounted(() => {
  store.checkBackend()
})
</script>

<template>
  <div class="home">
    <el-card class="home__card" shadow="never">
      <template #header>
        <div class="home__header">
          <div>
            <h1 class="home__title">{{ projectName }}</h1>
            <p class="home__welcome">欢迎，{{ auth.user?.nickname }}</p>
          </div>
          <div class="home__header-actions">
            <el-tag type="info" effect="plain">{{ teamName }}</el-tag>
            <el-button link @click="handleSignOut">退出登录</el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="前端运行状态">
          <el-tag type="success">运行中</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="后端连接状态">
          <el-tag v-if="backendStatus === 'loading'" type="warning">连接中…</el-tag>
          <el-tag v-else-if="backendStatus === 'success'" type="success">后端连接成功</el-tag>
          <el-tag v-else-if="backendStatus === 'error'" type="danger">后端连接失败</el-tag>
          <el-tag v-else type="info">未测试</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div class="home__actions">
        <el-button
          type="primary"
          :loading="backendStatus === 'loading'"
          @click="store.checkBackend()"
        >
          重新测试后端连接
        </el-button>
        <el-button type="success" @click="$router.push('/chat')">
          进入聊天界面
        </el-button>
      </div>

      <el-descriptions
        v-if="backendStatus === 'success' && health"
        class="home__result"
        :column="1"
        border
      >
        <el-descriptions-item label="Service">{{ health.service }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ health.status }}</el-descriptions-item>
        <el-descriptions-item label="Version">{{ health.version }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-else-if="backendStatus === 'error'"
        class="home__result"
        type="error"
        :closable="false"
        show-icon
        title="后端连接失败"
      >
        <template #default>
          <p>请检查以下几点：</p>
          <ul>
            <li>后端服务是否已启动（默认 http://127.0.0.1:8000）。</li>
            <li>端口是否正确，接口路径为 /api/v1/health。</li>
            <li>后端 CORS 是否允许当前前端来源。</li>
          </ul>
          <p v-if="errorMessage" class="home__error-detail">错误详情：{{ errorMessage }}</p>
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  justify-content: center;
  padding: 48px 16px;
}

.home__card {
  width: 100%;
  max-width: 640px;
}

.home__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.home__header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.home__welcome {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}

.home__title {
  margin: 0;
  font-size: 20px;
}

.home__actions {
  margin: 20px 0;
  display: flex;
  gap: 12px;
}

.home__result {
  margin-top: 8px;
}

.home__error-detail {
  margin-top: 8px;
  color: var(--el-color-danger);
  word-break: break-all;
}
</style>
