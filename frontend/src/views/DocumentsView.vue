<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRawFile, UploadUserFile } from 'element-plus'
import * as documentsApi from '@/api/documents'
import type { Document } from '@/api/documents'

// Define document status type based on backend schema
type DocumentStatus = 'pending' | 'processing' | 'succeeded' | 'failed'

const router = useRouter()
const documents = ref<Document[]>([])
const loading = ref(false)
const uploading = ref(false)
const fileList = ref<UploadUserFile[]>([])
const pollingTimers = new Map<string, number>()
const POLLING_INTERVAL = 2000
const MAX_POLLING_TIME = 5 * 60 * 1000 // 5 minutes

const statusMap: Record<DocumentStatus, { text: string; type: 'info' | 'warning' | 'success' | 'danger' }> = {
  pending: { text: '待处理', type: 'info' },
  processing: { text: '处理中', type: 'warning' },
  succeeded: { text: '成功', type: 'success' },
  failed: { text: '失败', type: 'danger' },
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
    ElMessage.error('加载文档列表失败')
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
  if (!isFileTypeAllowed(file)) {
    ElMessage.error('只支持 TXT、Markdown (.md/.markdown) 和 PDF 文件')
    return false
  }

  const maxSize = getMaxSizeForFile(file)
  if (maxSize === 0) {
    ElMessage.error('无法确定文件大小限制')
    return false
  }

  if (file.size > maxSize) {
    const sizeMB = Math.round(maxSize / 1024 / 1024)
    ElMessage.error(`文件大小超过 ${sizeMB}MB 限制`)
    return false
  }

  return true
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }

  const file = fileList.value[0].raw
  if (!file) return

  try {
    uploading.value = true
    const response = await documentsApi.uploadDocument(file)

    if (response.duplicate) {
      ElMessage.info(`该文件已存在：${response.original_name}`)
    } else {
      ElMessage.success('上传成功，正在处理中...')
    }

    fileList.value = []
    await loadDocuments()
  } catch (error) {
    const message = error instanceof Error ? error.message : '上传失败'
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
    return statusMap[status as DocumentStatus]
  }
  return { text: status, type: 'info' }
}

async function handleDelete(doc: Document) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档「${doc.original_name}」吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )

    await documentsApi.deleteDocument(doc.id)
    ElMessage.success('删除成功')

    // Stop polling for this document
    stopPolling(doc.id)

    // Remove from list
    await loadDocuments()
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    const message = error instanceof Error ? error.message : '删除失败'
    ElMessage.error(message)
    console.error('Delete failed:', error)
  }
}

async function handleReprocess(doc: Document) {
  try {
    await documentsApi.reprocessDocument(doc.id)
    ElMessage.success('已提交重新处理，请稍候...')

    // Update status to processing and start polling
    const index = documents.value.findIndex((d) => d.id === doc.id)
    if (index !== -1) {
      documents.value[index].status = 'processing'
      documents.value[index].error_message = null
      startPolling(doc.id)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '重新处理失败'
    ElMessage.error(message)
    console.error('Reprocess failed:', error)
  }
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
              返回
            </el-button>
            <div>
              <h2 class="documents__title">
                知识库管理
              </h2>
              <p class="documents__subtitle">
                上传和管理文档，支持 TXT、Markdown (.md / .markdown)、PDF 格式
              </p>
            </div>
          </div>
          <el-button
            :loading="loading"
            :disabled="uploading"
            @click="loadDocuments"
          >
            刷新列表
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
            上传文档
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
              拖拽文件到此处或 <em>点击选择</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                <p>支持格式：TXT、Markdown (.md / .markdown)、PDF</p>
                <p>大小限制：TXT/Markdown 最大 10MB，PDF 最大 50MB</p>
              </div>
            </template>
          </el-upload>

          <div class="documents__upload-actions">
            <el-button
              type="primary"
              size="large"
              :loading="uploading"
              :disabled="fileList.length === 0"
              @click="handleUpload"
            >
              {{ uploading ? '上传中...' : '开始上传' }}
            </el-button>
          </div>
        </el-card>

        <!-- Documents List -->
        <el-card
          class="documents__list-card"
          shadow="hover"
        >
          <h3 class="documents__section-title">
            文档列表
          </h3>

          <el-table
            v-loading="loading"
            :data="documents"
            style="width: 100%"
            stripe
          >
            <el-table-column
              prop="original_name"
              label="文件名"
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
              label="类型"
              width="120"
            >
              <template #default="{ row }">
                {{ getFileTypeDisplay(row.mime_type) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="size_bytes"
              label="大小"
              width="120"
            >
              <template #default="{ row }">
                {{ formatFileSize(row.size_bytes) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="status"
              label="状态"
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
              label="创建时间"
              width="180"
            >
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>

            <el-table-column
              prop="error_message"
              label="备注"
              min-width="200"
            >
              <template #default="{ row }">
                <el-text
                  v-if="row.error_message"
                  type="danger"
                  truncated
                >
                  {{ row.error_message }}
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
              label="操作"
              width="180"
              fixed="right"
            >
              <template #default="{ row }">
                <div class="documents__actions">
                  <el-button
                    v-if="row.status === 'failed'"
                    type="primary"
                    size="small"
                    :disabled="row.status === 'processing'"
                    @click="handleReprocess(row)"
                  >
                    重新处理
                  </el-button>
                  <el-button
                    v-if="row.status !== 'processing'"
                    type="danger"
                    size="small"
                    @click="handleDelete(row)"
                  >
                    删除
                  </el-button>
                  <el-text
                    v-if="row.status === 'processing'"
                    type="info"
                    size="small"
                  >
                    处理中...
                  </el-text>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <el-empty
            v-if="!loading && documents.length === 0"
            :image-size="120"
            description="还没有上传文档"
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
</style>
