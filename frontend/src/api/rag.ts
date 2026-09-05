import { apiRequest } from './client'

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
): Promise<RagAnswer> {
  return apiRequest<RagAnswer>('/api/v1/rag/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      top_k: 5,
    }),
  })
}
