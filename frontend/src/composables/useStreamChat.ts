import { ref, onUnmounted } from 'vue'
import { authenticatedFetch } from '@/api/client'
import * as chatApi from '@/api/chat'

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export function useStreamChat() {
  const messages = ref<Message[]>([])
  const currentSessionId = ref<number | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)

  let messageIdCounter = 0

  const loadSession = async (sessionId: number) => {
    try {
      const session = await chatApi.getSession(sessionId)
      currentSessionId.value = session.id
      messages.value = session.messages.map((msg) => ({
        id: messageIdCounter++,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
      }))
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载会话失败'
      throw err
    }
  }

  const sendMessage = async (userMessage: string) => {
    if (isLoading.value) return

    error.value = null
    isLoading.value = true
    abortController.value = new AbortController()

    const userMsgId = messageIdCounter++
    messages.value.push({
      id: userMsgId,
      role: 'user',
      content: userMessage,
    })

    const assistantMessageId = messageIdCounter++
    messages.value.push({
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    })

    try {
      const response = await authenticatedFetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          session_id: currentSessionId.value,
        }),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          const data = line.slice(6).trim()
          if (!data) continue

          try {
            const event = JSON.parse(data)

            if (event.type === 'session' && event.session_id) {
              currentSessionId.value = event.session_id
            } else if (event.type === 'content' && event.content) {
              const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
              if (assistantMessage) {
                assistantMessage.content += event.content
              }
            } else if (event.type === 'done') {
              const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
              if (assistantMessage) {
                assistantMessage.isStreaming = false
              }
            } else if (event.type === 'error') {
              throw new Error(event.error || '未知错误')
            }
          } catch (parseError) {
            console.error('Failed to parse SSE event:', parseError)
            throw parseError
          }
        }
      }

      const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
      if (assistantMessage) {
        assistantMessage.isStreaming = false
      }
    } catch (err: any) {
      console.error('Chat stream error:', err)
      
      if (err.name === 'AbortError') {
        error.value = '请求已取消'
      } else {
        error.value = err.message || '发送消息失败'
      }

      const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
      if (assistantMessage) {
        if (!assistantMessage.content) {
          assistantMessage.content = `❌ ${error.value}`
        }
        assistantMessage.isStreaming = false
      }
      
      throw err
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  const cancelRequest = () => {
    abortController.value?.abort()
  }

  const clearMessages = () => {
    messages.value = []
    currentSessionId.value = null
    error.value = null
  }

  const startNewSession = () => {
    clearMessages()
  }

  onUnmounted(() => {
    cancelRequest()
  })

  return {
    messages,
    currentSessionId,
    isLoading,
    error,
    loadSession,
    sendMessage,
    cancelRequest,
    clearMessages,
    startNewSession,
  }
}
