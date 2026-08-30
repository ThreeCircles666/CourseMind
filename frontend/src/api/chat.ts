import { type RequestOptions } from './client'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface ChatRequest {
  message: string
}

export interface ChatStreamEvent {
  type: 'content' | 'done' | 'error'
  content?: string
  error?: string
}

export async function* streamChat(
  request: ChatRequest,
  options: RequestOptions = {}
): AsyncGenerator<ChatStreamEvent, void, undefined> {
  const url = `${API_BASE_URL}/api/v1/chat/stream`
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(request),
    signal: options.signal,
  })

  if (!response.ok) {
    throw new Error(`请求失败：HTTP ${response.status}`)
  }

  if (!response.body) {
    throw new Error('响应体为空')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          try {
            const event = JSON.parse(dataStr) as ChatStreamEvent
            yield event
            
            if (event.type === 'done' || event.type === 'error') {
              return
            }
          } catch (e) {
            console.warn('Failed to parse SSE event:', dataStr)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
