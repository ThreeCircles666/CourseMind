<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useStreamChat } from '@/composables/useStreamChat'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const { messages, isLoading, error, sendMessage, cancelRequest, clearMessages } = useStreamChat()

const inputMessage = ref('')
const chatContainer = ref<HTMLElement>()

async function handleSend() {
  if (!inputMessage.value.trim()) {
    ElMessage.warning('请输入消息')
    return
  }

  const message = inputMessage.value
  inputMessage.value = ''
  
  await sendMessage(message)
  await scrollToBottom()
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

function handleClear() {
  clearMessages()
  ElMessage.success('已清空对话')
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
  <div class="chat">
    <el-card class="chat__card" shadow="never">
      <template #header>
        <div class="chat__header">
          <div>
            <h2 class="chat__title">AI 聊天助手</h2>
            <p class="chat__subtitle">{{ auth.user?.nickname }} · 基于阿里云百炼 Qwen 模型</p>
          </div>
          <el-button
            v-if="messages.length > 0"
            type="danger"
            plain
            size="small"
            :disabled="isLoading"
            @click="handleClear"
          >
            清空对话
          </el-button>
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
</template>

<style scoped>
.chat {
  display: flex;
  justify-content: center;
  padding: 24px 16px;
  height: 100vh;
  box-sizing: border-box;
}

.chat__card {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
  height: 100%;
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

.chat__title {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.chat__subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
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
