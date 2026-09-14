<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRawFile, UploadUserFile } from 'element-plus'
import * as documentsApi from '@/api/documents'
import type { Document } from '@/api/documents'

// Define document status type based on backend schema
type DocumentStatus = 'pending' | 'processing' | 'succeeded' | 'failed'

const router = useRouter()
const { t } = useI18n()
const documents = ref<Document[]>([])
const loading = ref(false)
const uploading = ref(false)
const fileList = ref<UploadUserFile[]>([])
const pollingTimers = new Map<string, number>()
const POLLING_INTERVAL = 2000
const MAX_POLLING_TIME = 5 * 60 * 1000 // 5 minutes

const statusMap: Record<DocumentStatus, { type: 'info' | 'warning' | 'success' | 'danger' }> = {
  pending: { type: 'info' },
  processing: { type: 'warning' },
  succeeded: { type: 'success' },
  failed: { type: 'danger' },
}

const mimeTypeMap: Record<string, string> = {
  'text/plain': 'TXT',
  'text/markdown': 'Markdown',
  'application/pdf': 'PDF',
}

// Allowed file extensions
const allowedExtensions = ['.txt', '.md', '.markdown', '.pdf']

// MIME type compatibility rules
const mimeCompatibility: Record<string, string[]> = {
  '.txt': ['text/plain'],
  '.md': ['text/markdown', 'text/plain'],
  '.markdown': ['text/markdown', 'text/plain'],
  '.pdf': ['application/pdf'],
}

// File size limits by extension
const maxSizeByExtension: Record<string, number> = {
  '.txt': 10 * 1024 * 1024,
  '.md': 10 * 1024 * 1024,
  '.markdown': 10 * 1024 * 1024,
  '.pdf': 50 * 1024 * 1024,
}

onMounted(async () => {
  await loadDocuments()
})

onUnmounted(() => {
  stopAllPolling()
})

function handleBack() {
  router.push('/')
}

async function loadDocuments() {
  try {
    loading.value = true
    documents.value = await documentsApi.getDocuments()

    // Start polling for pending/processing documents
    documents.value.forEach((doc) => {
      if (doc.status === 'pending' || doc.status === 'processing') {
        startPolling(doc.id)
      }
    })
  } catch (error) {
    ElMessage.error(t('documents.errors.loadFailed'))
    console.error('Failed to load documents:', error)
  } finally {
    loading.value = false
  }
}

function getFileExtension(fileName: string): string {
  const lowerName = fileName.toLowerCase()
  const dotIndex = lowerName.lastIndexOf('.')
  if (dotIndex === -1) return ''
  return lowerName.substring(dotIndex)
}

function getMaxSizeForFile(file: UploadRawFile): number {
  const extension = getFileExtension(file.name)
  return maxSizeByExtension[extension] || 0
}

function isFileTypeAllowed(file: UploadRawFile): boolean {
  const fileName = file.name
  const mimeType = file.type

  // Step 1: Extract and validate extension
  const extension = getFileExtension(fileName)
  if (!extension || !allowedExtensions.includes(extension)) {
    return false
  }

  // Step 2: If no MIME type (empty or undefined), allow based on extension
  // Backend will perform final validation
  if (!mimeType) {
    return true
  }

  // Step 3: If MIME is application/octet-stream, allow based on extension
  // Browser may report this for unknown types
  if (mimeType === 'application/octet-stream') {
    return true
  }

  // Step 4: If MIME exists and is specific, it must be compatible with extension
  const compatibleMimes = mimeCompatibility[extension]
  if (!compatibleMimes) {
    return false
  }

  return compatibleMimes.includes(mimeType)
}

function beforeUpload(file: UploadRawFile): boolean {
  const extension = getFileExtension(file.name)
  
  if (!extension) {
    ElMessage.error(t('documents.errors.noExtension'))
    return false
  }
  
  if (!allowedExtensions.includes(extension)) {
    ElMessage.error(t('documents.errors.unsupportedFormat', { ext: extension }))
    return false
  }

  if (!isFileTypeAllowed(file)) {
    ElMessage.error(t('documents.errors.unsupportedFormat', { ext: extension }))
    return false
  }

  const maxSize = getMaxSizeForFile(file)
  if (maxSize === 0) {
    ElMessage.error(t('documents.errors.sizeCheckFailed'))
    return false
  }

  if (file.size > maxSize) {
    const sizeMB = Math.round(maxSize / 1024 / 1024)
    ElMessage.error(t('documents.errors.fileTooLarge', { size: sizeMB }))
    return false
  }

  return true
}

function translateErrorMessage(error: Error): string {
  const message = error.message
  
  // Handle error codes from API
  if (message === 'FILE_TOO_LARGE') {
    return t('documents.errors.fileTooLarge', { size: 50 })
  }
  if (message === 'UNSUPPORTED_FILE_TYPE') {
    return t('documents.errors.unsupportedType')
  }
  if (message === 'DOCUMENT_NOT_FOUND') {
    return t('documents.errors.documentNotFound')
  }
  if (message === 'CANNOT_DELETE_PROCESSING') {
    return t('documents.errors.cannotDelete')
  }
  if (message === 'CANNOT_REPROCESS') {
    return t('documents.errors.cannotReprocess')
  }
  if (message === 'FILE_NOT_FOUND') {
    return t('documents.errors.fileNotFound')
  }
  
  // If message starts with error code prefix, use generic error
  if (message.startsWith('UPLOAD_FAILED:')) {
    return t('documents.errors.uploadFailed')
  }
  if (message.startsWith('DELETE_FAILED:')) {
    return t('documents.errors.deleteFailed')
  }
  if (message.startsWith('REPROCESS_FAILED:')) {
    return t('documents.errors.reprocessFailed')
  }
  
  // Return original message if not a known error code
  return message
}

function getUserFriendlyErrorMessage(errorMessage: string | null): string {
  if (!errorMessage) {
    return '-'
  }
  
  const lowerMessage = errorMessage.toLowerCase()
  
  // CID font encoding issues
  if (
    lowerMessage.includes('cid') ||
    lowerMessage.includes('pdftextnotfound') ||
    lowerMessage.includes('font encoding') ||
    lowerMessage.includes('unreadable') ||
    lowerMessage.includes('custom font') ||
    (lowerMessage.includes('text extraction') && lowerMessage.includes('failed'))
  ) {
    return t('documents.errors.pdfTextExtractionFailed')
  }
  
  // AI service not configured
  if (
    lowerMessage.includes('api key') ||
    lowerMessage.includes('dashscope') ||
    lowerMessage.includes('embedding') ||
    lowerMessage.includes('api_key') ||
    lowerMessage.includes('credential')
  ) {
    return t('documents.errors.aiServiceNotConfigured')
  }
  
  // PDF parsing failed
  if (
    lowerMessage.includes('pdf') &&
    (lowerMessage.includes('parse') ||
     lowerMessage.includes('parsing') ||
     lowerMessage.includes('extract') ||
     lowerMessage.includes('encrypted') ||
     lowerMessage.includes('scanned'))
  ) {
    return t('documents.errors.pdfParsingFailed')
  }
  
  // Truncate long error messages
  if (errorMessage.length > 120) {
    return errorMessage.substring(0, 117) + '...'
  }
  
  return errorMessage
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning(t('documents.upload.selectFile'))
    return
  }

  const file = fileList.value[0].raw
  if (!file) return

  try {
    uploading.value = true
    const response = await documentsApi.uploadDocument(file)

    if (response.duplicate) {
      ElMessage.info(t('documents.upload.duplicateFile', { filename: response.original_name }))
    } else {
      ElMessage.success(t('documents.upload.uploadSuccess'))
    }

    fileList.value = []
    await loadDocuments()
  } catch (error) {
    const message = error instanceof Error ? translateErrorMessage(error) : t('documents.errors.uploadFailed')
    ElMessage.error(message)
    console.error('Upload failed:', error)
  } finally {
    uploading.value = false
  }
}

function startPolling(documentId: string) {
  // Prevent duplicate timers
  if (pollingTimers.has(documentId)) {
    return
  }

  const startTime = Date.now()

  const timerId = window.setInterval(async () => {
    try {
      const doc = await documentsApi.getDocument(documentId)

      // Update document in list
      const index = documents.value.findIndex((d) => d.id === documentId)
      if (index !== -1) {
        documents.value[index] = doc
      }

      // Stop polling if final state or timeout
      if (doc.status === 'succeeded' || doc.status === 'failed') {
        stopPolling(documentId)
      } else if (Date.now() - startTime > MAX_POLLING_TIME) {
        stopPolling(documentId)
        console.warn(`Polling timeout for document ${documentId}`)
      }
    } catch (error) {
      console.error('Polling error:', error)
      stopPolling(documentId)
    }
  }, POLLING_INTERVAL)

  pollingTimers.set(documentId, timerId)
}

function stopPolling(documentId: string) {
  const timerId = pollingTimers.get(documentId)
  if (timerId) {
    clearInterval(timerId)
    pollingTimers.delete(documentId)
  }
}

function stopAllPolling() {
  pollingTimers.forEach((timerId) => clearInterval(timerId))
  pollingTimers.clear()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getFileTypeDisplay(mimeType: string): string {
  return mimeTypeMap[mimeType] || mimeType
}

function getStatusDisplay(status: string): { text: string; type: 'info' | 'warning' | 'success' | 'danger' } {
  // Safe fallback for unknown status
  if (status in statusMap) {
    return {
      text: t(`documents.status.${status}`),
      type: statusMap[status as DocumentStatus].type
    }
  }
  return { text: status, type: 'info' }
}

async function handleDelete(doc: Document) {
  try {
    await ElMessageBox.confirm(
      t('documents.list.deleteConfirm', { filename: doc.original_name }),
      t('documents.list.deleteTitle'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )

    await documentsApi.deleteDocument(doc.id)
    ElMessage.success(t('documents.list.deleteSuccess'))

    // Stop polling for this document
    stopPolling(doc.id)

    // Remove from list
    await loadDocuments()
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    const message = error instanceof Error ? translateErrorMessage(error) : t('documents.errors.deleteFailed')
    ElMessage.error(message)
    console.error('Delete failed:', error)
  }
}

async function handleReprocess(doc: Document) {
  try {
    await documentsApi.reprocessDocument(doc.id)
    ElMessage.success(t('documents.list.reprocessSuccess'))

    // Update status to processing and start polling
    const index = documents.value.findIndex((d) => d.id === doc.id)
    if (index !== -1) {
      documents.value[index].status = 'processing'
      documents.value[index].error_message = null
      startPolling(doc.id)
    }
  } catch (error) {
    const message = error instanceof Error ? translateErrorMessage(error) : t('documents.errors.reprocessFailed')
    ElMessage.error(message)
    console.error('Reprocess failed:', error)
  }
}

function goToAsk(doc: Document) {
  router.push({
    path: '/knowledge-ask',
    query: { documentId: doc.id }
  })
}

function goToCanvas(doc: Document) {
  router.push({
    path: '/canvas',
    query: { documentId: doc.id }
  })
}
</script>

<template>
  <div class="documents-layout">
    <el-card
      class="documents__card"
      shadow="never"
    >
      <template #header>
        <div class="documents__header">
          <div class="documents__header-left">
            <el-button
              text
              class="documents__back-button"
              @click="handleBack"
            >
              <el-icon>
                <svg
                  viewBox="0 0 1024 1024"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fill="currentColor"
                    d="M224 480h640a32 32 0 1 1 0 64H224a32 32 0 0 1 0-64z"
                  />
                  <path
                    fill="currentColor"
                    d="m237.248 512 265.408 265.344a32 32 0 0 1-45.312 45.312l-288-288a32 32 0 0 1 0-45.312l288-288a32 32 0 1 1 45.312 45.312L237.248 512z"
                  />
                </svg>
              </el-icon>
              {{ t('common.back') }}
            </el-button>
            <div>
              <h2 class="documents__title">
                {{ t('documents.title') }}
              </h2>
              <p class="documents__subtitle">
                {{ t('documents.subtitle') }}
              </p>
            </div>
          </div>
          <el-button
            :loading="loading"
            :disabled="uploading"
            @click="loadDocuments"
          >
            {{ t('common.refresh') }}
          </el-button>
        </div>
      </template>

      <div class="documents__content">
        <!-- Upload Section -->
        <el-card
          class="documents__upload-card"
          shadow="hover"
        >
          <h3 class="documents__section-title">
            {{ t('documents.upload.title') }}
          </h3>

          <el-upload
            v-model:file-list="fileList"
            :auto-upload="false"
            :limit="1"
            :before-upload="beforeUpload"
            :disabled="uploading"
            drag
            class="documents__upload"
          >
            <el-icon class="documents__upload-icon">
              <svg
                viewBox="0 0 1024 1024"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  fill="currentColor"
                  d="M544 864V672h128L512 480 352 672h128v192H320v-1.6c-5.376.32-10.496 1.6-16 1.6A240 240 0 0 1 64 624c0-123.136 93.12-223.488 212.608-237.248A239.808 239.808 0 0 1 512 192a239.872 239.872 0 0 1 235.456 194.752c119.488 13.76 212.48 114.112 212.48 237.248a240 240 0 0 1-240 240c-5.376 0-10.56-1.28-16-1.6v1.6H544z"
                />
              </svg>
            </el-icon>
            <div class="el-upload__text">
              {{ t('documents.upload.dragText') }} <em>{{ t('documents.upload.clickText') }}</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                <p>{{ t('documents.upload.supportedFormats') }}</p>
                <p>{{ t('documents.upload.sizeLimit') }}</p>
              </div>
            </template>
          </el-upload>

          <el-alert
            :title="t('documents.upload.formatNotice')"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          />

          <div class="documents__upload-actions">
            <el-button
              type="primary"
              size="large"
              :loading="uploading"
              :disabled="fileList.length === 0"
              @click="handleUpload"
            >
              {{ uploading ? t('documents.upload.uploading') : t('documents.upload.startUpload') }}
            </el-button>
          </div>
        </el-card>

        <!-- Documents List -->
        <el-card
          class="documents__list-card"
          shadow="hover"
        >
          <h3 class="documents__section-title">
            {{ t('documents.list.title') }}
          </h3>

          <el-table
            v-loading="loading"
            :data="documents"
            style="width: 100%"
            stripe
          >
            <el-table-column
              prop="original_name"
              :label="t('documents.list.filename')"
              min-width="200"
            >
              <template #default="{ row }">
                <el-text truncated>
                  {{ row.original_name }}
                </el-text>
              </template>
            </el-table-column>

            <el-table-column
              prop="mime_type"
              :label="t('documents.list.type')"
              width="120"
            >
              <template #default="{ row }">
                {{ getFileTypeDisplay(row.mime_type) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="size_bytes"
              :label="t('documents.list.size')"
              width="120"
            >
              <template #default="{ row }">
                {{ formatFileSize(row.size_bytes) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="status"
              :label="t('documents.list.status')"
              width="120"
            >
              <template #default="{ row }">
                <el-tag :type="getStatusDisplay(row.status).type">
                  {{ getStatusDisplay(row.status).text }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column
              prop="created_at"
              :label="t('documents.list.createdAt')"
              width="180"
            >
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="error_message"
              :label="t('documents.list.notes')"
              min-width="200"
            >
              <template #default="{ row }">
                <el-tooltip
                  v-if="row.error_message"
                  :content="getUserFriendlyErrorMessage(row.error_message)"
                  placement="top"
                  popper-class="documents-error-tooltip"
                >
                  <el-text
                    type="danger"
                    truncated
                  >
                    {{ getUserFriendlyErrorMessage(row.error_message) }}
                  </el-text>
                </el-tooltip>
                <el-text
                  v-else-if="row.status === 'succeeded'"
                  type="success"
                >
                  {{ t('documents.list.availableForUse') }}
                </el-text>
                <el-text
                  v-else
                  type="info"
                >
                  -
                </el-text>
              </template>
            </el-table-column>

            <el-table-column
              :label="t('documents.list.actions')"
              width="240"
              fixed="right"
            >
              <template #default="{ row }">
                <div class="documents__actions">
                  <!-- Succeeded: show Ask and Canvas buttons -->
                  <template v-if="row.status === 'succeeded'">
                    <el-button
                      type="primary"
                      size="small"
                      @click="goToAsk(row)"
                    >
                      {{ t('documents.list.goAsk') }}
                    </el-button>
                    <el-button
                      type="success"
                      size="small"
                      @click="goToCanvas(row)"
                    >
                      {{ t('documents.list.goCanvas') }}
                    </el-button>
                  </template>
                  
                  <!-- Failed: show Reprocess button -->
                  <el-button
                    v-if="row.status === 'failed'"
                    type="primary"
                    size="small"
                    @click="handleReprocess(row)"
                  >
                    {{ t('documents.list.reprocess') }}
                  </el-button>
                  
                  <!-- Processing: show status text -->
                  <el-text
                    v-if="row.status === 'processing'"
                    type="info"
                    size="small"
                  >
                    {{ t('common.processing') }}
                  </el-text>
                  
                  <!-- Delete button (not for processing) -->
                  <el-button
                    v-if="row.status !== 'processing'"
                    type="danger"
                    size="small"
                    @click="handleDelete(row)"
                  >
                    {{ t('common.delete') }}
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <el-empty
            v-if="!loading && documents.length === 0"
            :image-size="120"
            :description="t('documents.list.empty')"
          />
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.documents-layout {
  height: 100vh;
  overflow: auto;
  background-color: var(--el-fill-color-light);
}

.documents__card {
  margin: 0;
  border-radius: 0;
  border: none;
  min-height: 100vh;
}

.documents__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.documents__header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.documents__back-button {
  font-size: 14px;
  padding: 8px 12px;
}

.documents__title {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.documents__subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.documents__content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.documents__upload-card,
.documents__list-card {
  border: 1px solid var(--el-border-color-light);
}

.documents__section-title {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
}

.documents__upload {
  margin-bottom: 20px;
}

.documents__upload-icon {
  font-size: 67px;
  color: var(--el-text-color-placeholder);
  margin-bottom: 16px;
}

.documents__upload :deep(.el-upload-dragger) {
  padding: 40px;
}

.documents__upload :deep(.el-upload__tip) {
  margin-top: 12px;
  line-height: 1.6;
}

.documents__upload :deep(.el-upload__tip p) {
  margin: 4px 0;
}

.documents__upload-actions {
  display: flex;
  justify-content: center;
  padding-top: 12px;
}

.documents__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

:global(.documents-error-tooltip) {
  max-width: 360px;
  line-height: 1.5;
  white-space: normal;
}
</style>
