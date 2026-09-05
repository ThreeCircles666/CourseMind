import { apiRequest, authenticatedFetch } from './client'

export type DocumentStatus = 'pending' | 'processing' | 'succeeded' | 'failed'

export interface Document {
  id: string
  original_name: string
  mime_type: string
  size_bytes: number
  status: DocumentStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  id: string
  original_name: string
  mime_type: string
  size_bytes: number
  status: DocumentStatus
  duplicate: boolean
  created_at: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
}

/**
 * Upload a document file
 * @param file - The file to upload
 * @returns Upload response with document info
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  // Use authenticatedFetch to handle FormData properly (no manual Content-Type)
  const response = await authenticatedFetch('/api/v1/documents', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = (body as { detail?: string }).detail

    if (response.status === 413) {
      throw new Error('文件超过允许大小')
    }
    if (response.status === 415) {
      throw new Error('暂不支持该文件类型')
    }
    if (response.status === 422) {
      throw new Error(detail || '文件验证失败')
    }

    throw new Error(detail || `上传失败：HTTP ${response.status}`)
  }

  return await response.json()
}

/**
 * Get list of documents
 * @returns Document list
 */
export async function getDocuments(): Promise<Document[]> {
  const response = await apiRequest<DocumentListResponse>('/api/v1/documents', {
    method: 'GET',
  })
  return response.documents
}

/**
 * Get single document by ID
 * @param documentId - Document UUID
 * @returns Document details
 */
export async function getDocument(documentId: string): Promise<Document> {
  return apiRequest<Document>(`/api/v1/documents/${documentId}`, {
    method: 'GET',
  })
}

/**
 * Delete a document
 * @param documentId - Document UUID
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const response = await authenticatedFetch(`/api/v1/documents/${documentId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = (body as { detail?: string }).detail

    if (response.status === 404) {
      throw new Error('文档不存在或无权访问')
    }
    if (response.status === 409) {
      throw new Error('文档正在处理中，无法删除')
    }

    throw new Error(detail || `删除失败：HTTP ${response.status}`)
  }
}

/**
 * Reprocess a failed document
 * @param documentId - Document UUID
 */
export async function reprocessDocument(documentId: string): Promise<void> {
  const response = await authenticatedFetch(`/api/v1/documents/${documentId}/reprocess`, {
    method: 'POST',
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = (body as { detail?: string }).detail

    if (response.status === 404) {
      throw new Error('文档不存在或无权访问')
    }
    if (response.status === 409) {
      throw new Error('文档正在处理或已成功，无需重新处理')
    }
    if (response.status === 400) {
      throw new Error('文档文件缺失，无法重新处理')
    }

    throw new Error(detail || `重新处理失败：HTTP ${response.status}`)
  }
}
