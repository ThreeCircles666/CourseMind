<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useStreamChat } from '@/composables/useStreamChat'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as chatApi from '@/api/chat'
import type { SessionSummary } from '@/api/chat'

const auth = useAuthStore()
const router = useRouter()
const { 
  messages, 
  currentSessionId, 
  isLoading, 
  error, 
  loadSession, 
  sendMessage, 
  cancelRequest, 
  startNewSession 
} = useStreamChat()

const inputMessage = ref('')
const chatContainer = ref<HTMLElement>()
const sessions = ref<SessionSummary[]>([])
const loadingSessions = ref(false)
const sidebarCollapsed = ref(false)

// Load session list on mount
onMounted(async () => {
  await refreshSessions()
})

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function handleBack() {
  router.push('/')
}

async function refreshSessions() {
  try {
    loadingSessions.value = true
    sessions.value = await chatApi.getSessions()
  } catch (err) {
    console.error('Failed to load sessions:', err)
  } finally {
    loadingSessions.value = false
  }
}

async function handleSessionClick(sessionId: number) {
  if (currentSessionId.value === sessionId) return
  
  try {
    await loadSession(sessionId)
    await scrollToBottom()
  } catch (err) {
    ElMessage.error('加载会话失败')
  }
}

async function handleNewChat() {
  startNewSession()
  ElMessage.success('已开始新对话')
}

async function handleSend() {
  if (!inputMessage.value.trim()) {
    ElMessage.warning('请输入消息')
    return
  }

  const message = inputMessage.value
  inputMessage.value = ''
  
  try {
    await sendMessage(message)
    await scrollToBottom()
    await refreshSessions()
  } catch (err) {
    // Error already handled in useStreamChat
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function handleCancel() {
  cancelRequest()
}

async function handleRenameSession(session: SessionSummary) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话标题', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: session.title,
      inputPattern: /.+/,
      inputErrorMessage: '标题不能为空',
    })
    
    if (value) {
      await chatApi.renameSession(session.id, value)
      ElMessage.success('重命名成功')
      await refreshSessions()
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('重命名失败')
    }
  }
}

async function handleDeleteSession(session: SessionSummary) {
  try {
    await ElMessageBox.confirm(
      `确定要删除会话「${session.title}」吗？`,
      '删除会话',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await chatApi.deleteSession(session.id)
    ElMessage.success('删除成功')
    
    if (currentSessionId.value === session.id) {
      startNewSession()
    }
    
    await refreshSessions()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => messages.value[messages.value.length - 1]?.content,
  () => {
    scrollToBottom()
  }
)
</script>

<template>
  <div class="chat-layout">
    <!-- Sidebar -->
    <div :class="['chat-sidebar', { 'chat-sidebar--collapsed': sidebarCollapsed }]">
      <div class="chat-sidebar__header">
        <h3 v-if="!sidebarCollapsed" class="chat-sidebar__title">会话历史</h3>
        <el-button 
          v-if="!sidebarCollapsed"
          type="primary" 
          size="small" 
          @click="handleNewChat"
          :disabled="isLoading"
        >
          新建会话
        </el-button>
        <el-tooltip v-else content="新建会话" placement="right">
          <el-button 
            type="primary" 
            size="small"
            circle
            @click="handleNewChat"
            :disabled="isLoading"
          >
            <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M480 480V128a32 32 0 0 1 64 0v352h352a32 32 0 1 1 0 64H544v352a32 32 0 1 1-64 0V544H128a32 32 0 0 1 0-64h352z"/></svg></el-icon>
          </el-button>
        </el-tooltip>
      </div>
      
      <div v-if="!sidebarCollapsed" class="chat-sidebar__list" v-loading="loadingSessions">
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="[
            'chat-sidebar__item',
            { 'chat-sidebar__item--active': session.id === currentSessionId }
          ]"
          @click="handleSessionClick(session.id)"
        >
          <div class="chat-sidebar__item-content">
            <div class="chat-sidebar__item-title">{{ session.title }}</div>
            <div class="chat-sidebar__item-meta">
              {{ session.message_count }} 条消息 · 
              {{ new Date(session.updated_at).toLocaleDateString() }}
            </div>
          </div>
          <div class="chat-sidebar__item-actions">
            <el-button
              size="small"
              text
              @click.stop="handleRenameSession(session)"
            >
              重命名
            </el-button>
            <el-button
              size="small"
              text
              type="danger"
              @click.stop="handleDeleteSession(session)"
            >
              删除
            </el-button>
          </div>
        </div>
        
        <el-empty
          v-if="!loadingSessions && sessions.length === 0"
          description="还没有历史会话"
          :image-size="80"
        />
      </div>

      <div class="chat-sidebar__toggle">
        <el-button 
          text 
          @click="toggleSidebar"
          :icon="sidebarCollapsed ? 'ArrowRight' : 'ArrowLeft'"
        >
          {{ sidebarCollapsed ? '' : '收起' }}
        </el-button>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <el-card class="chat__card" shadow="never">
        <template #header>
          <div class="chat__header">
            <div class="chat__header-left">
              <el-button 
                text 
                @click="handleBack"
                class="chat__back-button"
              >
                <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M224 480h640a32 32 0 1 1 0 64H224a32 32 0 0 1 0-64z"/><path fill="currentColor" d="m237.248 512 265.408 265.344a32 32 0 0 1-45.312 45.312l-288-288a32 32 0 0 1 0-45.312l288-288a32 32 0 1 1 45.312 45.312L237.248 512z"/></svg></el-icon>
                返回
              </el-button>
              <div>
                <h2 class="chat__title">AI 聊天助手</h2>
                <p class="chat__subtitle">
                  {{ auth.user?.nickname }} · 基于阿里云百炼 Qwen 模型
                  <span v-if="currentSessionId" class="chat__session-id">
                    · 会话 #{{ currentSessionId }}
                  </span>
                </p>
              </div>
            </div>
          </div>
        </template>

        <div class="chat__container" ref="chatContainer">
          <div v-if="messages.length === 0" class="chat__empty">
            <el-empty description="还没有消息，开始对话吧" />
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['chat__message', `chat__message--${msg.role}`]"
          >
            <div class="chat__message-avatar">
              <el-avatar :size="36">
                {{ msg.role === 'user' ? '我' : 'AI' }}
              </el-avatar>
            </div>
            <div class="chat__message-content">
              <div class="chat__message-role">
                {{ msg.role === 'user' ? '用户' : 'AI 助手' }}
                <span v-if="msg.isStreaming" class="chat__streaming-indicator">正在输入...</span>
              </div>
              <div class="chat__message-text">{{ msg.content }}</div>
            </div>
          </div>
        </div>

        <div class="chat__input-area">
          <el-alert
            v-if="error"
            type="error"
            :closable="false"
            show-icon
            class="chat__error"
          >
            {{ error }}
          </el-alert>

          <div class="chat__input-wrapper">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="输入您的消息..."
              :disabled="isLoading"
              @keydown.enter.ctrl="handleSend"
              @keydown.enter.meta="handleSend"
            />
            <div class="chat__actions">
              <el-text size="small" type="info">
                按 Ctrl+Enter 或 Command+Enter 发送
              </el-text>
              <div class="chat__buttons">
                <el-button
                  v-if="isLoading"
                  type="warning"
                  @click="handleCancel"
                >
                  取消
                </el-button>
                <el-button
                  type="primary"
                  :loading="isLoading"
                  :disabled="!inputMessage.trim()"
                  @click="handleSend"
                >
                  发送
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.chat-sidebar {
  width: 300px;
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  transition: width 0.3s ease;
  position: relative;
}

.chat-sidebar--collapsed {
  width: 60px;
}

.chat-sidebar__header {
  padding: 20px;
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 80px;
}

.chat-sidebar--collapsed .chat-sidebar__header {
  justify-content: center;
  padding: 20px 10px;
}

.chat-sidebar__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.chat-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chat-sidebar__toggle {
  padding: 12px;
  border-top: 1px solid var(--el-border-color);
  text-align: center;
}

.chat-sidebar__item {
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chat-sidebar__item:hover {
  background-color: var(--el-fill-color-light);
}

.chat-sidebar__item--active {
  background-color: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
}

.chat-sidebar__item-content {
  flex: 1;
  min-width: 0;
}

.chat-sidebar__item-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sidebar__item-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.chat-sidebar__item-actions {
  display: none;
  gap: 4px;
}

.chat-sidebar__item:hover .chat-sidebar__item-actions {
  display: flex;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat__card {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 0;
  border-radius: 0;
  border: none;
}

.chat__card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.chat__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat__header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat__back-button {
  font-size: 14px;
  padding: 8px 12px;
}

.chat__title {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.chat__subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.chat__session-id {
  color: var(--el-color-primary);
}

.chat__container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: var(--el-fill-color-light);
}

.chat__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.chat__message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.chat__message--user {
  flex-direction: row-reverse;
}

.chat__message-content {
  flex: 1;
  max-width: 70%;
}

.chat__message--user .chat__message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.chat__message-role {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat__streaming-indicator {
  color: var(--el-color-primary);
  font-weight: 500;
}

.chat__message-text {
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat__message--user .chat__message-text {
  background-color: var(--el-color-primary);
  color: white;
}

.chat__message--assistant .chat__message-text {
  background-color: white;
  border: 1px solid var(--el-border-color);
}

.chat__input-area {
  padding: 20px;
  border-top: 1px solid var(--el-border-color);
  background-color: white;
}

.chat__error {
  margin-bottom: 12px;
}

.chat__input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat__buttons {
  display: flex;
  gap: 8px;
}
</style>
