import { apiRequest, authenticatedFetch } from './client'

export interface RagSource {
  source_id: string
  chunk_id: string
  document_id: string
  file_name: string
  chunk_index: number
  page_number: number | null
  title_path: string[]
  similarity: number
  excerpt: string
}

export interface RagAnswer {
  answer: string
  sources: RagSource[]
  model: string | null
  insufficient_context: boolean
}

export async function askKnowledgeBase(
  question: string,
  documentIds: string[],
  responseLanguage = 'zh-CN',
): Promise<RagAnswer> {
  return apiRequest<RagAnswer>('/api/v1/rag/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      response_language: responseLanguage,
      top_k: 5,
    }),
  })
}

export type RagPhase = 'authorizing' | 'retrieving' | 'generating' | 'validating'

/** Phase messages come from the backend operations, not a client-side timer. */
export async function askKnowledgeBaseWithProgress(
  question: string,
  documentIds: string[],
  responseLanguage: string,
  onPhase: (phase: RagPhase) => void,
  signal?: AbortSignal,
): Promise<RagAnswer> {
  const response = await authenticatedFetch('/api/v1/rag/ask/stream', {
    method: 'POST', signal,
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ question, document_ids: documentIds, response_language: responseLanguage, top_k: 5 }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  if (!response.body) throw new Error('Response stream unavailable')
  const reader = response.body.getReader(), decoder = new TextDecoder()
  let buffer = '', result: RagAnswer | undefined
  function frame(value: string) {
    const lines = value.split(/\r?\n/)
    const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
    const text = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
    if (!text) return
    const data = JSON.parse(text)
    if (event === 'phase' && ['authorizing', 'retrieving', 'generating', 'validating'].includes(data.phase)) onPhase(data.phase)
    else if (event === 'result') result = data as RagAnswer
    else if (event === 'error') throw new Error(data.message || 'AI service temporarily unavailable')
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''
      for (const value of frames) frame(value)
      if (result) return result
      if (done) { if (buffer.trim()) frame(buffer); break }
    }
    if (result) return result
    throw new Error('Response stream ended before completion')
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
