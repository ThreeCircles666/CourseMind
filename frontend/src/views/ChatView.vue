<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useStreamChat } from '@/composables/useStreamChat'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as chatApi from '@/api/chat'
import type { SessionSummary } from '@/api/chat'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()
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
    ElMessage.error(t('chat.loadSessionFailed'))
  }
}

async function handleNewChat() {
  startNewSession()
  ElMessage.success(t('chat.newSessionSuccess'))
}

async function handleSend() {
  if (!inputMessage.value.trim()) {
    ElMessage.warning(t('chat.inputRequired'))
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
    const { value } = await ElMessageBox.prompt(t('chat.renamePrompt'), t('chat.renameSession'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      inputValue: session.title,
      inputPattern: /.+/,
      inputErrorMessage: t('chat.renamePlaceholder'),
    })
    
    if (value) {
      await chatApi.renameSession(session.id, value)
      ElMessage.success(t('chat.renameSuccess'))
      await refreshSessions()
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('chat.renameFailed'))
    }
  }
}

async function handleDeleteSession(session: SessionSummary) {
  try {
    await ElMessageBox.confirm(
      t('chat.deleteConfirm'),
      t('chat.deleteSession'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    
    await chatApi.deleteSession(session.id)
    ElMessage.success(t('chat.deleteSuccess'))
    
    if (currentSessionId.value === session.id) {
      startNewSession()
    }
    
    await refreshSessions()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('chat.deleteFailed'))
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
        <h3
          v-if="!sidebarCollapsed"
          class="chat-sidebar__title"
        >
          {{ t('chat.sessionHistory') }}
        </h3>
        <el-button 
          v-if="!sidebarCollapsed"
          type="primary" 
          size="small" 
          :disabled="isLoading"
          @click="handleNewChat"
        >
          {{ t('chat.newSession') }}
        </el-button>
        <el-tooltip
          v-else
          :content="t('chat.newSession')"
          placement="right"
        >
          <el-button 
            type="primary" 
            size="small"
            circle
            :disabled="isLoading"
            @click="handleNewChat"
          >
            <el-icon>
              <svg
                viewBox="0 0 1024 1024"
                xmlns="http://www.w3.org/2000/svg"
              ><path
                fill="currentColor"
                d="M480 480V128a32 32 0 0 1 64 0v352h352a32 32 0 1 1 0 64H544v352a32 32 0 1 1-64 0V544H128a32 32 0 0 1 0-64h352z"
              /></svg>
            </el-icon>
          </el-button>
        </el-tooltip>
      </div>
      
      <div
        v-if="!sidebarCollapsed"
        v-loading="loadingSessions"
        class="chat-sidebar__list"
      >
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
            <div class="chat-sidebar__item-title">
              {{ session.title }}
            </div>
            <div class="chat-sidebar__item-meta">
              {{ t('chat.messageCount', { count: session.message_count }) }} · 
              {{ new Date(session.updated_at).toLocaleDateString() }}
            </div>
          </div>
          <div class="chat-sidebar__item-actions">
            <el-button
              size="small"
              text
              @click.stop="handleRenameSession(session)"
            >
              {{ t('chat.renameButton') }}
            </el-button>
            <el-button
              size="small"
              text
              type="danger"
              @click.stop="handleDeleteSession(session)"
            >
              {{ t('chat.deleteButton') }}
            </el-button>
          </div>
        </div>
        
        <el-empty
          v-if="!loadingSessions && sessions.length === 0"
          :description="t('chat.emptyHistory')"
          :image-size="80"
        />
      </div>

      <div class="chat-sidebar__toggle">
        <el-button 
          text 
          :icon="sidebarCollapsed ? 'ArrowRight' : 'ArrowLeft'"
          @click="toggleSidebar"
        >
          {{ sidebarCollapsed ? '' : t('chat.collapse') }}
        </el-button>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <el-card
        class="chat__card"
        shadow="never"
      >
        <template #header>
          <div class="chat__header">
            <div class="chat__header-left">
              <el-button 
                text 
                class="chat__back-button"
                @click="handleBack"
              >
                <el-icon>
                  <svg
                    viewBox="0 0 1024 1024"
                    xmlns="http://www.w3.org/2000/svg"
                  ><path
                    fill="currentColor"
                    d="M224 480h640a32 32 0 1 1 0 64H224a32 32 0 0 1 0-64z"
                  /><path
                    fill="currentColor"
                    d="m237.248 512 265.408 265.344a32 32 0 0 1-45.312 45.312l-288-288a32 32 0 0 1 0-45.312l288-288a32 32 0 1 1 45.312 45.312L237.248 512z"
                  /></svg>
                </el-icon>
                {{ t('common.back') }}
              </el-button>
              <div>
                <h2 class="chat__title">
                  {{ t('chat.title') }}
                </h2>
                <p class="chat__subtitle">
                  {{ auth.user?.nickname }} · {{ t('chat.subtitle') }}
                  <span
                    v-if="currentSessionId"
                    class="chat__session-id"
                  >
                    · {{ t('chat.sessionHistory') }} #{{ currentSessionId }}
                  </span>
                </p>
              </div>
            </div>
            
            <LocaleSwitcher />
          </div>
        </template>

        <div
          ref="chatContainer"
          class="chat__container"
        >
          <div
            v-if="messages.length === 0"
            class="chat__empty"
          >
            <el-empty :description="t('chat.emptySession')" />
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['chat__message', `chat__message--${msg.role}`]"
          >
            <div class="chat__message-avatar">
              <el-avatar :size="36">
                {{ msg.role === 'user' ? t('chat.userAvatar') : t('chat.aiAvatar') }}
              </el-avatar>
            </div>
            <div class="chat__message-content">
              <div class="chat__message-role">
                {{ msg.role === 'user' ? t('chat.user') : t('chat.assistant') }}
                <span
                  v-if="msg.isStreaming"
                  class="chat__streaming-indicator"
                >{{ t('chat.streaming') }}</span>
              </div>
              <div class="chat__message-text">
                {{ msg.content }}
              </div>
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
              :placeholder="t('chat.inputPlaceholder')"
              :disabled="isLoading"
              @keydown.enter.ctrl="handleSend"
              @keydown.enter.meta="handleSend"
            />
            <div class="chat__actions">
              <el-text
                size="small"
                type="info"
              >
                {{ t('chat.inputHint') }}
              </el-text>
              <div class="chat__buttons">
                <el-button
                  v-if="isLoading"
                  type="warning"
                  @click="handleCancel"
                >
                  {{ t('chat.cancel') }}
                </el-button>
                <el-button
                  type="primary"
                  :loading="isLoading"
                  :disabled="!inputMessage.trim()"
                  @click="handleSend"
                >
                  {{ t('chat.send') }}
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
  background: var(--cm-bg-secondary);
}

.chat-sidebar {
  width: 280px;
  border-right: 1px solid var(--cm-border-light);
  display: flex;
  flex-direction: column;
  background: var(--cm-bg-elevated);
  transition: width var(--cm-transition-base);
  position: relative;
}

.chat-sidebar--collapsed {
  width: 60px;
}

.chat-sidebar__header {
  padding: var(--cm-space-5);
  border-bottom: 1px solid var(--cm-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--cm-space-3);
  min-height: 80px;
}

.chat-sidebar--collapsed .chat-sidebar__header {
  justify-content: center;
  padding: var(--cm-space-5) var(--cm-space-2);
}

.chat-sidebar__title {
  margin: 0;
  font-size: var(--cm-text-lg);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
}

.chat-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: var(--cm-space-2);
}

.chat-sidebar__toggle {
  padding: var(--cm-space-3);
  border-top: 1px solid var(--cm-border-light);
  text-align: center;
}

.chat-sidebar__item {
  padding: var(--cm-space-3);
  margin-bottom: var(--cm-space-1);
  border-radius: var(--cm-radius-md);
  cursor: pointer;
  transition: all var(--cm-transition-fast);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--cm-space-2);
  border: 1px solid transparent;
}

.chat-sidebar__item:hover {
  background: var(--cm-bg-tertiary);
  border-color: var(--cm-border-light);
}

.chat-sidebar__item--active {
  background: var(--cm-primary-light);
  border-color: var(--cm-primary);
  color: var(--cm-primary-dark);
}

.chat-sidebar__item-content {
  flex: 1;
  min-width: 0;
}

.chat-sidebar__item-title {
  font-size: var(--cm-text-sm);
  font-weight: var(--cm-font-medium);
  margin-bottom: var(--cm-space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--cm-text-primary);
}

.chat-sidebar__item-meta {
  font-size: var(--cm-text-xs);
  color: var(--cm-text-tertiary);
}

.chat-sidebar__item-actions {
  display: none;
  gap: var(--cm-space-1);
}

.chat-sidebar__item:hover .chat-sidebar__item-actions {
  display: flex;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--cm-bg-secondary);
}

.chat__card {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 0;
  border-radius: 0;
  border: none;
  background: var(--cm-bg-elevated);
}

.chat__card :deep(.el-card__header) {
  border-bottom: 1px solid var(--cm-border-light);
  background: var(--cm-bg-elevated);
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
  gap: var(--cm-space-4);
}

.chat__header-left {
  display: flex;
  align-items: center;
  gap: var(--cm-space-4);
}

.chat__back-button {
  font-size: var(--cm-text-sm);
  padding: var(--cm-space-2) var(--cm-space-3);
}

.chat__title {
  margin: 0 0 var(--cm-space-1) 0;
  font-size: var(--cm-text-xl);
  font-weight: var(--cm-font-semibold);
  color: var(--cm-text-primary);
}

.chat__subtitle {
  margin: 0;
  font-size: var(--cm-text-sm);
  color: var(--cm-text-secondary);
}

.chat__session-id {
  color: var(--cm-primary);
  font-weight: var(--cm-font-medium);
}

.chat__container {
  flex: 1;
  overflow-y: auto;
  padding: var(--cm-space-6);
  background: var(--cm-bg-secondary);
}

.chat__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.chat__message {
  display: flex;
  gap: var(--cm-space-3);
  margin-bottom: var(--cm-space-6);
}

.chat__message--user {
  flex-direction: row-reverse;
}

.chat__message-content {
  flex: 1;
  max-width: 75%;
}

.chat__message--user .chat__message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.chat__message-role {
  font-size: var(--cm-text-xs);
  color: var(--cm-text-tertiary);
  margin-bottom: var(--cm-space-2);
  display: flex;
  align-items: center;
  gap: var(--cm-space-2);
  font-weight: var(--cm-font-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chat__streaming-indicator {
  color: var(--cm-primary);
  font-weight: var(--cm-font-medium);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.chat__message-text {
  padding: var(--cm-space-4);
  border-radius: var(--cm-radius-lg);
  line-height: var(--cm-leading-relaxed);
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: var(--cm-shadow-sm);
}

.chat__message--user .chat__message-text {
  background: var(--cm-primary);
  color: white;
  border: none;
}

.chat__message--assistant .chat__message-text {
  background: var(--cm-bg-elevated);
  color: var(--cm-text-primary);
  border: 1px solid var(--cm-border-light);
}

.chat__input-area {
  padding: var(--cm-space-5);
  border-top: 1px solid var(--cm-border-light);
  background: var(--cm-bg-elevated);
}

.chat__error {
  margin-bottom: var(--cm-space-3);
}

.chat__input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-3);
}

.chat__input-wrapper :deep(.el-textarea__inner) {
  border-radius: var(--cm-radius-md);
  border: 1px solid var(--cm-border-light);
  padding: var(--cm-space-3);
  font-size: var(--cm-text-base);
  line-height: var(--cm-leading-relaxed);
}

.chat__input-wrapper :deep(.el-textarea__inner):focus {
  border-color: var(--cm-primary);
  box-shadow: 0 0 0 3px var(--cm-primary-light);
}

.chat__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat__buttons {
  display: flex;
  gap: var(--cm-space-2);
}

@media (max-width: 768px) {
  .chat-sidebar {
    width: 240px;
  }

  .chat-sidebar--collapsed {
    width: 0;
    border-right: none;
  }

  .chat-sidebar__header {
    padding: var(--cm-space-4);
  }

  .chat__message-content {
    max-width: 85%;
  }

  .chat__input-area {
    padding: var(--cm-space-4);
  }

  .chat__actions {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--cm-space-2);
  }

  .chat__buttons {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 480px) {
  .chat-sidebar {
    position: absolute;
    z-index: 100;
    height: 100%;
    width: 280px;
    transform: translateX(-100%);
    transition: transform var(--cm-transition-base);
  }

  .chat-sidebar:not(.chat-sidebar--collapsed) {
    transform: translateX(0);
    box-shadow: var(--cm-shadow-lg);
  }

  .chat__message-content {
    max-width: 90%;
  }

  .chat__header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--cm-space-2);
  }

  .chat__title {
    font-size: var(--cm-text-lg);
  }

  .chat__subtitle {
    font-size: var(--cm-text-xs);
  }
}
</style>
