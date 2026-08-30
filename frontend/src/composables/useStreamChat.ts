import { ref, onUnmounted } from 'vue'

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export function useStreamChat() {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)

  let messageIdCounter = 0

  const sendMessage = async (userMessage: string) => {
    if (isLoading.value) {
      return
    }

    error.value = null
    isLoading.value = true
    abortController.value = new AbortController()

    messages.value.push({
      id: messageIdCounter++,
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
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
      const response = await fetch(`${apiBaseUrl}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = `HTTP ${response.status}`
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.detail || errorMessage
        } catch {
          errorMessage = errorText || errorMessage
        }
        throw new Error(errorMessage)
      }

      if (!response.body) {
        throw new Error('响应体为空')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) {
            continue
          }

          if (line.startsWith('data:')) {
            const data = line.substring(5).trim()

            try {
              const event = JSON.parse(data)
              const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
              
              if (event.type === 'content' && event.content) {
                if (assistantMessage) {
                  assistantMessage.content += event.content
                }
              } else if (event.type === 'done') {
                if (assistantMessage) {
                  assistantMessage.isStreaming = false
                }
                break
              } else if (event.type === 'error') {
                throw new Error(event.error || '服务器返回错误')
              }
            } catch (parseError) {
              if (parseError instanceof SyntaxError) {
                continue
              }
              throw parseError
            }
          }
        }
      }

      const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
      if (assistantMessage) {
        assistantMessage.isStreaming = false
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        error.value = '请求已取消'
      } else {
        error.value = err.message || '未知错误'
      }

      const assistantMessage = messages.value.find((m) => m.id === assistantMessageId)
      if (assistantMessage && !assistantMessage.content) {
        assistantMessage.content = `[错误] ${error.value}`
        assistantMessage.isStreaming = false
      }
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  const cancelRequest = () => {
    if (abortController.value) {
      abortController.value.abort()
    }
  }

  const clearMessages = () => {
    messages.value = []
    error.value = null
  }

  onUnmounted(() => {
    cancelRequest()
  })

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    cancelRequest,
    clearMessages,
  }
}
