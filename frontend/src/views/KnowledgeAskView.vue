<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import * as documentsApi from '@/api/documents'
import type { Document } from '@/api/documents'
import { askKnowledgeBase } from '@/api/rag'
import type { RagAnswer } from '@/api/rag'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()
const documents = ref<Document[]>([])
const selectedDocumentIds = ref<string[]>([])
const question = ref('')
const loadingDocuments = ref(false)
const asking = ref(false)
const result = ref<RagAnswer | null>(null)

const succeededDocuments = computed(() =>
  documents.value.filter((document) => document.status === 'succeeded'),
)

const selectedDocuments = computed(() =>
  succeededDocuments.value.filter((document) => selectedDocumentIds.value.includes(document.id)),
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
    
    // Auto-select document from query parameter
    const documentId = route.query.documentId as string | undefined
    if (documentId && availableIds.has(documentId) && !selectedDocumentIds.value.includes(documentId)) {
      selectedDocumentIds.value = [documentId]
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('knowledgeAsk.errors.loadDocumentsFailed'))
  } finally {
    loadingDocuments.value = false
  }
}

async function submitQuestion() {
  if (!canAsk.value) return
  asking.value = true
  result.value = null
  try {
    result.value = await askKnowledgeBase(question.value.trim(), selectedDocumentIds.value, locale.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('knowledgeAsk.errors.askFailed'))
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
    <header class="knowledge-ask__hero">
      <div class="cm-container knowledge-ask__hero-inner">
        <div>
          <el-button
            text
            class="knowledge-ask__back"
            @click="router.push('/')"
          >
            ← {{ t('common.back') }}
          </el-button>
          <h1>{{ t('knowledgeAsk.title') }}</h1>
          <p>{{ t('knowledgeAsk.headerSubtitle') }}</p>
        </div>
        
        <div class="knowledge-ask__hero-actions">
          <LocaleSwitcher />
          <el-tag
            size="large"
            type="success"
            effect="light"
          >
            {{ t('knowledgeAsk.citedKnowledgeBase') }}
          </el-tag>
        </div>
      </div>
    </header>

    <main class="knowledge-ask__main cm-container">
      <aside class="knowledge-panel">
        <el-card shadow="never" class="knowledge-card">
          <div class="card-header">
            <div>
              <strong>{{ t('knowledgeAsk.documentStep') }}</strong>
              <p>{{ t('knowledgeAsk.selectedCount', { count: selectedDocumentIds.length }) }}</p>
            </div>
            <el-button
              size="small"
              :loading="loadingDocuments"
              @click="loadDocuments"
            >
              {{ t('common.refresh') }}
            </el-button>
          </div>

          <el-empty
            v-if="!loadingDocuments && succeededDocuments.length === 0"
            :description="t('knowledgeAsk.noSucceededDocuments')"
          >
            <el-button
              type="primary"
              @click="router.push('/documents')"
            >
              {{ t('knowledgeAsk.goUpload') }}
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
              <span class="document-option">
                <strong>{{ document.original_name }}</strong>
                <small>{{ new Date(document.updated_at).toLocaleDateString() }}</small>
              </span>
            </el-checkbox>
          </el-checkbox-group>
        </el-card>

        <el-card shadow="never" class="knowledge-card scope-card">
          <strong>{{ t('knowledgeAsk.selectDocuments') }}</strong>
          <div class="scope-list">
            <el-tag
              v-for="document in selectedDocuments"
              :key="document.id"
              effect="plain"
            >
              {{ document.original_name }}
            </el-tag>
            <el-text v-if="selectedDocuments.length === 0" type="info">
              {{ t('knowledgeAsk.noSucceededDocuments') }}
            </el-text>
          </div>
        </el-card>
      </aside>

      <section class="ask-workspace">
        <el-card shadow="never" class="question-card">
          <div class="card-header">
            <div>
              <strong>{{ t('knowledgeAsk.questionStep') }}</strong>
              <p>{{ t('knowledgeAsk.question') }}</p>
            </div>
          </div>
          <el-input
            v-model="question"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            :placeholder="t('knowledgeAsk.questionPlaceholder')"
            @keydown.meta.enter.prevent="submitQuestion"
            @keydown.ctrl.enter.prevent="submitQuestion"
          />
          <div class="ask-actions">
            <span>{{ t('knowledgeAsk.sendShortcut') }}</span>
            <el-button
              type="primary"
              size="large"
              :disabled="!canAsk"
              :loading="asking"
              @click="submitQuestion"
            >
              {{ asking ? t('knowledgeAsk.asking') : t('knowledgeAsk.askButton') }}
            </el-button>
          </div>
        </el-card>

        <el-card
          v-if="asking"
          shadow="never"
          class="answer-card"
        >
          <el-skeleton :rows="4" animated />
        </el-card>

        <el-card
          v-else-if="result"
          shadow="never"
          class="answer-card"
        >
          <div class="card-header">
            <div>
              <strong>{{ t('knowledgeAsk.answer') }}</strong>
              <p>{{ t('knowledgeAsk.sources') }} · {{ result.sources.length }}</p>
            </div>
            <el-tag :type="result.insufficient_context ? 'warning' : 'success'">
              {{ result.insufficient_context ? t('knowledgeAsk.insufficientContextTag') : t('knowledgeAsk.citedKnowledgeBase') }}
            </el-tag>
          </div>

          <p class="answer-text">
            {{ result.answer }}
          </p>

          <section
            v-if="result.sources.length > 0"
            class="sources"
          >
            <h3>{{ t('knowledgeAsk.sources') }}</h3>
            <article
              v-for="source in result.sources"
              :key="source.chunk_id"
              class="source-item"
            >
              <div class="source-item__title">
                <el-tag size="small" effect="plain">
                  {{ source.source_id }}
                </el-tag>
                <strong>{{ source.file_name }}</strong>
                <span v-if="source.page_number">{{ t('knowledgeAsk.page', { page: source.page_number }) }}</span>
                <span>{{ t('knowledgeAsk.similarity', { score: formatSimilarity(source.similarity) }) }}</span>
              </div>
              <p>{{ source.excerpt }}</p>
            </article>
          </section>

          <el-empty
            v-else
            :description="t('knowledgeAsk.noSources')"
            :image-size="80"
          />
        </el-card>

        <el-card
          v-else
          shadow="never"
          class="answer-card answer-card--empty"
        >
          <el-empty
            :description="t('knowledgeAsk.noAnswer')"
            :image-size="96"
          />
        </el-card>
      </section>
    </main>
  </div>
</template>

<style scoped>
.knowledge-ask {
  min-height: 100vh;
  background: var(--cm-bg-secondary);
}

.knowledge-ask__hero {
  background: var(--cm-bg-elevated);
  border-bottom: 1px solid var(--cm-border-light);
}

.knowledge-ask__hero-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--cm-space-6);
  padding-top: var(--cm-space-8);
  padding-bottom: var(--cm-space-8);
}

.knowledge-ask__hero-actions {
  display: flex;
  align-items: center;
  gap: var(--cm-space-4);
}

.knowledge-ask__back {
  padding-left: 0;
  margin-bottom: var(--cm-space-3);
}

.knowledge-ask__hero h1 {
  margin: 0;
  font-size: var(--cm-text-4xl);
  font-weight: var(--cm-font-bold);
}

.knowledge-ask__hero p {
  margin-top: var(--cm-space-3);
  color: var(--cm-text-secondary);
}

.knowledge-ask__main {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  gap: var(--cm-space-6);
  padding-top: var(--cm-space-8);
  padding-bottom: var(--cm-space-16);
}

.knowledge-panel,
.ask-workspace {
  display: flex;
  flex-direction: column;
  gap: var(--cm-space-5);
}

.knowledge-card,
.question-card,
.answer-card {
  border: 1px solid var(--cm-border-light);
  border-radius: var(--cm-radius-lg);
}

.card-header,
.ask-actions,
.source-item__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--cm-space-3);
}

.card-header {
  margin-bottom: var(--cm-space-5);
}

.card-header strong {
  color: var(--cm-text-primary);
  font-size: var(--cm-text-base);
}

.card-header p {
  margin-top: var(--cm-space-1);
  color: var(--cm-text-secondary);
  font-size: var(--cm-text-sm);
}

.document-options {
  display: grid;
  gap: var(--cm-space-3);
}

.document-options :deep(.el-checkbox) {
  width: 100%;
  margin: 0;
  height: auto;
  padding: var(--cm-space-3);
  border-radius: var(--cm-radius-md);
}

.document-options :deep(.el-checkbox__label) {
  min-width: 0;
}

.document-option {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--cm-space-1);
}

.document-option strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-option small {
  color: var(--cm-text-tertiary);
}

.scope-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cm-space-2);
  margin-top: var(--cm-space-4);
}

.ask-actions {
  margin-top: var(--cm-space-4);
  color: var(--cm-text-secondary);
  font-size: var(--cm-text-sm);
}

.answer-text {
  margin: 0;
  line-height: 1.8;
  white-space: pre-wrap;
  color: var(--cm-text-primary);
}

.sources {
  margin-top: var(--cm-space-6);
  padding-top: var(--cm-space-5);
  border-top: 1px solid var(--cm-border-light);
}

.sources h3 {
  margin: 0 0 var(--cm-space-3);
  font-size: var(--cm-text-base);
}

.source-item {
  padding: var(--cm-space-4);
  margin-top: var(--cm-space-3);
  background: var(--cm-bg-secondary);
  border: 1px solid var(--cm-border-light);
  border-radius: var(--cm-radius-md);
}

.source-item__title {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.source-item__title span {
  color: var(--cm-text-secondary);
  font-size: var(--cm-text-sm);
}

.source-item p {
  margin: var(--cm-space-3) 0 0;
  color: var(--cm-text-secondary);
  line-height: 1.6;
}

@media (max-width: 960px) {
  .knowledge-ask__main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .knowledge-ask__hero-inner {
    align-items: flex-start;
    flex-direction: column;
  }

  .knowledge-ask__hero h1 {
    font-size: var(--cm-text-3xl);
  }

  .ask-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
