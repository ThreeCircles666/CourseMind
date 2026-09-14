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
      throw new Error('FILE_TOO_LARGE')
    }
    if (response.status === 415) {
      // Return server detail if available, otherwise generic unsupported type
      throw new Error(detail || 'UNSUPPORTED_FILE_TYPE')
    }
    if (response.status === 422) {
      throw new Error(detail || 'VALIDATION_FAILED')
    }

    throw new Error(detail || `UPLOAD_FAILED:${response.status}`)
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
      throw new Error('DOCUMENT_NOT_FOUND')
    }
    if (response.status === 409) {
      throw new Error('CANNOT_DELETE_PROCESSING')
    }

    throw new Error(detail || `DELETE_FAILED:${response.status}`)
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
      throw new Error('DOCUMENT_NOT_FOUND')
    }
    if (response.status === 409) {
      throw new Error('CANNOT_REPROCESS')
    }
    if (response.status === 400) {
      throw new Error('FILE_NOT_FOUND')
    }

    throw new Error(detail || `REPROCESS_FAILED:${response.status}`)
  }
}
