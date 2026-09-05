<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as documentsApi from '@/api/documents'
import type { Document } from '@/api/documents'
import { askKnowledgeBase } from '@/api/rag'
import type { RagAnswer } from '@/api/rag'

const router = useRouter()
const documents = ref<Document[]>([])
const selectedDocumentIds = ref<string[]>([])
const question = ref('')
const loadingDocuments = ref(false)
const asking = ref(false)
const result = ref<RagAnswer | null>(null)

const succeededDocuments = computed(() =>
  documents.value.filter((document) => document.status === 'succeeded'),
)

const canAsk = computed(
  () => selectedDocumentIds.value.length > 0 && question.value.trim().length > 0 && !asking.value,
)

async function loadDocuments() {
  loadingDocuments.value = true
  try {
    documents.value = await documentsApi.getDocuments()
    const availableIds = new Set(succeededDocuments.value.map((document) => document.id))
    selectedDocumentIds.value = selectedDocumentIds.value.filter((id) => availableIds.has(id))
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载文档失败')
  } finally {
    loadingDocuments.value = false
  }
}

async function submitQuestion() {
  if (!canAsk.value) return
  asking.value = true
  result.value = null
  try {
    result.value = await askKnowledgeBase(question.value.trim(), selectedDocumentIds.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '知识库问答失败')
  } finally {
    asking.value = false
  }
}

function formatSimilarity(similarity: number) {
  return `${(similarity * 100).toFixed(1)}%`
}

onMounted(loadDocuments)
</script>

<template>
  <div class="knowledge-ask">
    <header class="knowledge-ask__header">
      <el-button
        text
        @click="router.push('/')"
      >
        ← 返回
      </el-button>
      <div>
        <h1>知识库问答</h1>
        <p>选择资料后提问，回答将显示引用来源</p>
      </div>
    </header>

    <main class="knowledge-ask__main">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <strong>1. 选择知识库文档</strong>
            <el-button
              :loading="loadingDocuments"
              @click="loadDocuments"
            >
              刷新
            </el-button>
          </div>
        </template>

        <el-empty
          v-if="!loadingDocuments && succeededDocuments.length === 0"
          description="暂无处理成功的文档，请先上传资料"
        >
          <el-button
            type="primary"
            @click="router.push('/documents')"
          >
            前往上传
          </el-button>
        </el-empty>

        <el-checkbox-group
          v-else
          v-model="selectedDocumentIds"
          class="document-options"
        >
          <el-checkbox
            v-for="document in succeededDocuments"
            :key="document.id"
            :label="document.id"
            border
          >
            {{ document.original_name }}
          </el-checkbox>
        </el-checkbox-group>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <strong>2. 输入问题</strong>
        </template>
        <el-input
          v-model="question"
          type="textarea"
          :rows="4"
          maxlength="2000"
          show-word-limit
          placeholder="例如：CourseMind内部测试代号是什么？"
          @keydown.meta.enter.prevent="submitQuestion"
          @keydown.ctrl.enter.prevent="submitQuestion"
        />
        <div class="ask-actions">
          <span>Command/Ctrl + Enter 发送</span>
          <el-button
            type="primary"
            :disabled="!canAsk"
            :loading="asking"
            @click="submitQuestion"
          >
            提问
          </el-button>
        </div>
      </el-card>

      <el-card
        v-if="result"
        shadow="never"
      >
        <template #header>
          <div class="card-header">
            <strong>回答</strong>
            <el-tag :type="result.insufficient_context ? 'warning' : 'success'">
              {{ result.insufficient_context ? '资料不足' : '已引用知识库' }}
            </el-tag>
          </div>
        </template>

        <p class="answer-text">
          {{ result.answer }}
        </p>

        <section
          v-if="result.sources.length > 0"
          class="sources"
        >
          <h3>引用来源</h3>
          <article
            v-for="source in result.sources"
            :key="source.chunk_id"
            class="source-item"
          >
            <div class="source-item__title">
              <el-tag size="small">
                {{ source.source_id }}
              </el-tag>
              <strong>{{ source.file_name }}</strong>
              <span v-if="source.page_number">第 {{ source.page_number }} 页</span>
              <span>相似度 {{ formatSimilarity(source.similarity) }}</span>
            </div>
            <p>{{ source.excerpt }}</p>
          </article>
        </section>
      </el-card>
    </main>
  </div>
</template>

<style scoped>
.knowledge-ask {
  min-height: 100vh;
  background: #f5f7fa;
}

.knowledge-ask__header {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  padding: 24px 40px;
  background: white;
  border-bottom: 1px solid var(--el-border-color-light);
}

.knowledge-ask__header h1 {
  margin: 0 0 6px;
  font-size: 24px;
}

.knowledge-ask__header p {
  margin: 0;
  color: var(--el-text-color-secondary);
}

.knowledge-ask__main {
  display: grid;
  gap: 20px;
  width: min(960px, calc(100% - 40px));
  margin: 24px auto;
  padding-bottom: 40px;
}

.card-header,
.ask-actions,
.source-item__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.document-options {
  display: grid;
  gap: 12px;
}

.document-options :deep(.el-checkbox) {
  width: 100%;
  margin: 0;
}

.ask-actions {
  margin-top: 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.answer-text {
  margin: 0;
  line-height: 1.8;
  white-space: pre-wrap;
}

.sources {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-light);
}

.sources h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.source-item {
  padding: 14px;
  margin-top: 10px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.source-item__title {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.source-item__title span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.source-item p {
  margin: 10px 0 0;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

@media (max-width: 640px) {
  .knowledge-ask__header {
    padding: 18px 16px;
  }
}
</style>
