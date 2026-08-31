import { authenticatedFetch, type RequestOptions } from './client'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface ChatRequest {
  message: string
  session_id?: number | null
}

export interface ChatStreamEvent {
  type: 'session' | 'content' | 'done' | 'error'
  session_id?: number
  content?: string
  error?: string
}

export interface MessageResponse {
  role: string
  content: string
  created_at: string
}

export interface SessionSummary {
  id: number
  title: string
  message_count: number
  updated_at: string
}

export interface SessionDetail {
  id: number
  title: string
  model: string
  messages: MessageResponse[]
}

export interface SessionRenameRequest {
  title: string
}

// Get user's session list
export async function getSessions(limit = 50, offset = 0): Promise<SessionSummary[]> {
  const response = await authenticatedFetch(
    `/api/v1/chat/sessions?limit=${limit}&offset=${offset}`
  )
  if (!response.ok) {
    throw new Error(`获取会话列表失败: HTTP ${response.status}`)
  }
  return response.json()
}

// Get session detail with messages
export async function getSession(sessionId: number): Promise<SessionDetail> {
  const response = await authenticatedFetch(`/api/v1/chat/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error(`获取会话详情失败: HTTP ${response.status}`)
  }
  return response.json()
}

// Rename session
export async function renameSession(
  sessionId: number,
  title: string
): Promise<void> {
  const response = await authenticatedFetch(`/api/v1/chat/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  if (!response.ok) {
    throw new Error(`重命名会话失败: HTTP ${response.status}`)
  }
}

// Delete session
export async function deleteSession(sessionId: number): Promise<void> {
  const response = await authenticatedFetch(`/api/v1/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`删除会话失败: HTTP ${response.status}`)
  }
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
