import { apiRequest, authenticatedFetch } from './client'

export interface Evidence { page: number; quote: string; origin?: 'text' | 'vision' }
export interface ReviewBlock {
  kind: 'explanation' | 'quote' | 'inference' | 'missing' | 'code' | 'formula' | 'table'
  text: string; evidence: Evidence[]; rows: string[][]
}
export interface QuickEntry {
  kind: 'definition' | 'formula' | 'rule' | 'conclusion' | 'steps' | 'list'
  name: string; text: string; evidence: Evidence[]
}
export interface Demo {
  kind: 'steps' | 'linear'; title: string; steps: string[]; a: number; b: number
  minimum: number; maximum: number; illustrative: boolean; evidence: Evidence[]
}
export interface Erratum {
  id: string; original: string; correction: string; reason: string; impact: string
  status: 'candidate' | 'confirmed' | 'dismissed'; evidence: Evidence[]
}
export interface ReviewSection {
  id: string; document_id: string; title: string; pages: number[]; blocks: ReviewBlock[]
  takeaways: QuickEntry[]; quick_reference: QuickEntry[]; demos: Demo[]; errata: Erratum[]
}
export interface ReviewPage {
  number: number; text: string; has_image: boolean; visual_description?: string; read_mode: 'text' | 'vision'
}
export interface ReviewDocument { id: string; name: string; pages: ReviewPage[] }
export interface CoursewareReview {
  id: string; document_ids: string[]; language: string; use_vision: boolean
  status: 'queued' | 'processing' | 'ready' | 'failed'; created_at: string; completed_pages: number
  documents: ReviewDocument[]; sections: ReviewSection[]; reviewed_sections: string[]; error: string | null
  total_pages?: number; phase?: string; current_pages?: number[]; current_document?: string; error_code?: string
  duplicates: { document_id: string; page: number; other_document_id: string; other_page: number }[]
}
export type ReviewListItem = Pick<CoursewareReview, 'id' | 'document_ids' | 'language' | 'status' | 'created_at' | 'completed_pages'>
export const listReviews = () => apiRequest<ReviewListItem[]>('/api/v1/reviews')
export const getReview = (id: string) => apiRequest<CoursewareReview>(`/api/v1/reviews/${id}`)
export const createReview = (ids: string[], language: string, vision: boolean) => apiRequest<CoursewareReview>('/api/v1/reviews', {
  method: 'POST', body: JSON.stringify({ document_ids: ids, response_language: language, use_vision: vision }),
})
export const updateReview = (id: string, patch: { reviewed_sections?: string[]; erratum_id?: string; decision?: Erratum['status'] }) =>
  apiRequest<CoursewareReview>(`/api/v1/reviews/${id}/state`, { method: 'PATCH', body: JSON.stringify(patch) })
export const deleteReview = (id: string) => apiRequest<void>(`/api/v1/reviews/${id}`, { method: 'DELETE' })
export async function getPageImage(reviewId: string, documentId: string, page: number): Promise<Blob> {
  const response = await authenticatedFetch(`/api/v1/reviews/${reviewId}/documents/${documentId}/pages/${page}/image`)
  if (!response.ok) throw new Error(`Original page unavailable (${response.status})`)
  return response.blob()
}
