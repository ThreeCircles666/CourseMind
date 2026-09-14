<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as documentsApi from '@/api/documents'
import type { Document } from '@/api/documents'
import { askKnowledgeBase } from '@/api/rag'
import type { RagSource } from '@/api/rag'
import { fetchHealth } from '@/api/health'

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()

// LocalStorage key for learning signals
const LEARNING_SIGNALS_KEY = 'coursemind_canvas_learning_signals'

// State
const documents = ref<Document[]>([])
const selectedDocumentId = ref<string>('')
const cards = ref<CanvasCard[]>([])
const selectedCardId = ref<string>('')
const loading = ref(false)
const generating = ref(false)
const asking = ref(false)
const followUpQuestion = ref('')
const selectedText = ref('')

// Demo check states
const demoCheckLoading = ref(false)
const isLoggedIn = ref(false)
const backendHealthy = ref(false)

// Types
interface CanvasCard {
  id: string
  title: string
  summary: string
  tag: 'definition' | 'formula' | 'example' | 'mistake' | 'exam' | 'followup' | 'quiz'
  documentId?: string
  fileName?: string
  pageNumber?: number | null
  excerpt?: string
  followUpCount: number
  isWeakPoint: boolean
  isChild: boolean
  parentId?: string
  isDemo?: boolean  // 标记是否为演示数据
  isFallback?: boolean  // 标记是否为 fallback 回答
  isGenerationFallback?: boolean
  quizQuestion?: string  // 自测题题目
  quizAnswer?: string  // 自测题答案
  quizExplanation?: string  // 自测题解析
  isExamFocus?: boolean  // 是否为高频考点
}

interface LearningSignal {
  cardId: string
  followUpCount: number
  isWeakPoint: boolean
}

interface StructuredConceptCard {
  title?: string
  summary?: string
  tag?: CanvasCard['tag']
  sourceIndex?: number
}

// Computed
const succeededDocuments = computed(() =>
  documents.value.filter((d) => d.status === 'succeeded')
)

const selectedCard = computed(() =>
  cards.value.find((c) => c.id === selectedCardId.value)
)

const rootCards = computed(() => cards.value.filter((c) => !c.isChild))

const canvasCards = computed(() => {
  const orderedCards: CanvasCard[] = []
  for (const rootCard of rootCards.value) {
    orderedCards.push(rootCard)
    orderedCards.push(...cards.value.filter((c) => c.isChild && c.parentId === rootCard.id))
  }
  return orderedCards
})

const childCards = computed(() => {
  if (!selectedCardId.value) return []
  return cards.value.filter((c) => c.isChild && c.parentId === selectedCardId.value)
})

const isChineseLocale = computed(() => locale.value === 'zh-CN')

// Stats
const statsData = computed(() => {
  const rootCardsCount = cards.value.filter(c => !c.isChild).length
  const followupsCount = cards.value.filter(c => c.isChild).length
  const weakPointsCount = cards.value.filter(c => c.isWeakPoint).length
  const examFocusCount = cards.value.filter(c => c.tag === 'exam' || c.isExamFocus).length
  
  return {
    concepts: rootCardsCount,
    followups: followupsCount,
    weakPoints: weakPointsCount,
    examFocus: examFocusCount,
  }
})

// Demo guide step
const demoGuideStep = computed(() => {
  if (cards.value.length === 0) {
    return 0
  }
  if (statsData.value.followups === 0) {
    return 1
  }
  return 2
})

// Demo check functions
async function checkDemoStatus() {
  demoCheckLoading.value = true

  try {
    await Promise.all([
      checkLoginStatus(),
      checkBackendHealth(),
    ])
  } finally {
    demoCheckLoading.value = false
  }
}

async function checkLoginStatus() {
  try {
    await documentsApi.getDocuments()
    isLoggedIn.value = true
  } catch {
    isLoggedIn.value = false
  }
}

async function checkBackendHealth() {
  try {
    const health = await fetchHealth()
    backendHealthy.value = health.status === 'healthy'
  } catch (error) {
    backendHealthy.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await loadDocuments()
  await checkDemoStatus()
})

// Methods
async function loadDocuments() {
  try {
    loading.value = true
    documents.value = await documentsApi.getDocuments()
    
    // Auto-select document from query parameter
    const documentId = route.query.documentId as string | undefined
    if (documentId) {
      const doc = documents.value.find(d => d.id === documentId && d.status === 'succeeded')
      if (doc) {
        selectedDocumentId.value = documentId
      }
    }
  } catch (error) {
    ElMessage.error(t('knowledgeAsk.errors.loadDocumentsFailed'))
    console.error('Failed to load documents:', error)
  } finally {
    loading.value = false
  }
}

async function generateCanvas() {
  if (!selectedDocumentId.value) {
    ElMessage.warning(t('learningCanvas.sidebar.selectFirst'))
    return
  }

  generating.value = true
  cards.value = []
  selectedCardId.value = ''

  try {
    const prompt = isChineseLocale.value
      ? `请基于这份课件，提炼 6-10 个最适合复习的知识点。请用编号列表输出，每条格式为“标题：适合学生复习的一句话摘要 [S来源编号]”。可以在标题或摘要中自然体现定义、公式、例子、易错点或考点类型。每条都必须引用最相关的来源编号。`
      : `Based on this course material, extract 6-10 key concepts for review. Use a numbered list. Each item must follow this format: "Title: one review-friendly sentence [source id]". Naturally indicate whether it is a definition, formula, example, mistake, or exam focus when relevant. Every item must cite the most relevant source id.`

    const response = await askKnowledgeBase(
      prompt,
      [selectedDocumentId.value],
    )

    // Try to parse AI response into cards
    const generatedCards = parseAIResponse(response.answer, selectedDocumentId.value, response.sources)
    
    if (generatedCards.length > 0) {
      cards.value = generatedCards
    } else {
      // Fallback to demo data
      cards.value = getGenerationFallbackCards(selectedDocumentId.value)
      ElMessage.info(t('learningCanvas.errors.generateFailed'))
    }
  } catch (error) {
    // Use fallback demo data
    cards.value = getGenerationFallbackCards(selectedDocumentId.value)
    ElMessage.warning(t('learningCanvas.errors.generateFailed'))
    console.error('Generate canvas failed:', error)
  } finally {
    generating.value = false
  }
}

// LocalStorage functions
function saveLearningSignals() {
  const signals: LearningSignal[] = cards.value
    .filter(card => card.isDemo && !card.isChild)
    .map(card => ({
      cardId: card.id,
      followUpCount: card.followUpCount,
      isWeakPoint: card.isWeakPoint,
    }))
  
  try {
    localStorage.setItem(LEARNING_SIGNALS_KEY, JSON.stringify(signals))
  } catch (error) {
    console.error('Failed to save learning signals:', error)
  }
}

function loadLearningSignals(): Map<string, LearningSignal> {
  try {
    const data = localStorage.getItem(LEARNING_SIGNALS_KEY)
    if (!data) return new Map()
    
    const signals: LearningSignal[] = JSON.parse(data)
    return new Map(signals.map(s => [s.cardId, s]))
  } catch (error) {
    console.error('Failed to load learning signals:', error)
    return new Map()
  }
}

function clearLearningSignals() {
  try {
    localStorage.removeItem(LEARNING_SIGNALS_KEY)
  } catch (error) {
    console.error('Failed to clear learning signals:', error)
  }
}

function clearCanvas() {
  cards.value = []
  selectedCardId.value = ''
  followUpQuestion.value = ''
}

async function resetLearningSignals() {
  try {
    await ElMessageBox.confirm(
      t('learningCanvas.sidebar.resetConfirm'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    
    clearLearningSignals()
    
    cards.value.forEach(card => {
      if (card.isDemo && !card.isChild) {
        card.followUpCount = 0
        card.isWeakPoint = false
      }
    })
    
    ElMessage.success(t('learningCanvas.sidebar.resetSuccess'))
  } catch {
    // User cancelled
  }
}

function hasVerifiedSource(card: CanvasCard): boolean {
  return !!(
    card.fileName &&
    card.pageNumber &&
    card.excerpt &&
    !card.isFallback &&
    !card.isGenerationFallback
  )
}

function getCardSourceLabel(card: CanvasCard): string {
  if (card.isGenerationFallback) {
    return t('learningCanvas.canvas.generationFallback')
  }
  if (card.isFallback) {
    return t('learningCanvas.canvas.demoExplanation')
  }
  if (card.isDemo) {
    return t('learningCanvas.canvas.demoData')
  }
  return t('learningCanvas.canvas.fromUploadedMaterial')
}

function loadDemoCanvas() {
  const demoDocumentId = 'demo-document'
  const demoCards = getFallbackCards(demoDocumentId)
  
  const signals = loadLearningSignals()
  
  demoCards.forEach(card => {
    card.isDemo = true
    const signal = signals.get(card.id)
    if (signal) {
      card.followUpCount = signal.followUpCount
      card.isWeakPoint = signal.isWeakPoint
    }
  })
  
  cards.value = demoCards
  selectedCardId.value = demoCards[0]?.id || ''
  selectedDocumentId.value = ''
  followUpQuestion.value = ''
}

function getGenerationFallbackCards(documentId: string): CanvasCard[] {
  return getFallbackCards(documentId).map(card => ({
    ...card,
    isGenerationFallback: true,
  }))
}

function resetDemoMode() {
  // Clear all states
  cards.value = []
  selectedCardId.value = ''
  selectedDocumentId.value = ''
  followUpQuestion.value = ''
  selectedText.value = ''
  
  // Clear browser text selection
  window.getSelection()?.removeAllRanges()
  
  // Clear localStorage
  localStorage.removeItem(LEARNING_SIGNALS_KEY)
  
  // Load fresh demo cards
  const demoDocumentId = 'demo-document'
  const demoCards = getFallbackCards(demoDocumentId)
  
  demoCards.forEach(card => {
    card.isDemo = true
  })
  
  cards.value = demoCards
  selectedCardId.value = demoCards[0]?.id || ''
  
  // Show success message
  ElMessage.success(t('learningCanvas.sidebar.demoModeSuccess'))
}

function isDemoCard(card: CanvasCard): boolean {
  return card.documentId === 'demo-document'
}

function parseAIResponse(answer: string, documentId: string, sources: RagSource[]): CanvasCard[] {
  const structuredCards = parseStructuredCards(answer, documentId, sources)
  if (structuredCards.length > 0) {
    return structuredCards
  }

  // Simple parsing logic - try to extract structured data
  const cards: CanvasCard[] = []
  
  // Try to find numbered lists or bullet points
  const lines = answer.split('\n').filter(line => line.trim())
  let currentCard: Partial<CanvasCard> | null = null
  
  for (const line of lines) {
    // Check if this is a title line (number or bullet)
    if (/^[\d]+[.、)]|^[•\-*]/.test(line.trim())) {
      if (currentCard && currentCard.title) {
        cards.push(completeCard(currentCard, documentId, sources[cards.length % Math.max(sources.length, 1)]))
      }
      currentCard = parseListConceptLine(line)
    } else if (currentCard && line.trim()) {
      // Add to summary
      currentCard.summary = (currentCard.summary || '') + line.trim() + ' '
    }
  }
  
  if (currentCard && currentCard.title) {
    cards.push(completeCard(currentCard, documentId, sources[cards.length % Math.max(sources.length, 1)]))
  }
  
  return cards.slice(0, 10) // Limit to 10 cards
}

function parseListConceptLine(line: string): Partial<CanvasCard> {
  const text = line
    .replace(/^(?:[\d]+[.、)]|[•\-*])\s*/, '')
    .replace(/\s*\[S\d+\]\s*/g, '')
    .trim()
  const separatorMatch = text.match(/[:：]/)

  if (!separatorMatch || separatorMatch.index === undefined) {
    return { title: text }
  }

  const title = text.slice(0, separatorMatch.index).trim()
  const summary = text.slice(separatorMatch.index + 1).trim()
  return {
    title: title || text,
    summary,
  }
}

function parseStructuredCards(answer: string, documentId: string, sources: RagSource[]): CanvasCard[] {
  const jsonText = extractJsonArray(answer)
  if (!jsonText) return []

  try {
    const parsed = JSON.parse(jsonText)
    if (!Array.isArray(parsed)) return []

    return parsed
      .map((item, index) => completeStructuredCard(item, documentId, sources, index))
      .filter((card): card is CanvasCard => card !== null)
      .slice(0, 10)
  } catch (error) {
    console.warn('Failed to parse structured canvas response:', error)
    return []
  }
}

function extractJsonArray(answer: string): string {
  const fencedJson = answer.match(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/i)
  if (fencedJson?.[1]) return fencedJson[1]

  const start = answer.indexOf('[')
  const end = answer.lastIndexOf(']')
  if (start === -1 || end === -1 || end <= start) return ''

  return answer.slice(start, end + 1)
}

function completeStructuredCard(
  item: unknown,
  documentId: string,
  sources: RagSource[],
  index: number,
): CanvasCard | null {
  if (!item || typeof item !== 'object') return null

  const raw = item as StructuredConceptCard
  const title = typeof raw.title === 'string' ? raw.title.trim() : ''
  const summary = typeof raw.summary === 'string' ? raw.summary.trim() : ''
  if (!title || !summary) return null

  const sourceIndex = typeof raw.sourceIndex === 'number' ? raw.sourceIndex - 1 : index
  const source = sources[sourceIndex] || sources[index % Math.max(sources.length, 1)]

  return {
    id: `card-${Date.now()}-${Math.random()}`,
    title,
    summary: summary.slice(0, 240),
    tag: normalizeCardTag(raw.tag),
    documentId,
    fileName: source?.file_name,
    pageNumber: source?.page_number,
    excerpt: source?.excerpt,
    followUpCount: 0,
    isWeakPoint: false,
    isChild: false,
  }
}

function normalizeCardTag(tag: unknown): CanvasCard['tag'] {
  const allowedTags: CanvasCard['tag'][] = ['definition', 'formula', 'example', 'mistake', 'exam']
  return allowedTags.includes(tag as CanvasCard['tag']) ? tag as CanvasCard['tag'] : 'definition'
}

function completeCard(partial: Partial<CanvasCard>, documentId: string, source?: RagSource): CanvasCard {
  const tagKeywords = {
    definition: ['定义', '概念', 'definition', 'concept'],
    formula: ['公式', '方程', 'formula', 'equation'],
    example: ['例子', '示例', 'example', 'instance'],
    mistake: ['易错', '注意', 'mistake', 'warning'],
    exam: ['考点', '重点', 'exam', 'key'],
  }
  
  let tag: CanvasCard['tag'] = 'definition'
  const text = (partial.title + ' ' + (partial.summary || '')).toLowerCase()
  
  for (const [key, keywords] of Object.entries(tagKeywords)) {
    if (keywords.some(kw => text.includes(kw))) {
      tag = key as CanvasCard['tag']
      break
    }
  }
  
  return {
    id: `card-${Date.now()}-${Math.random()}`,
    title: partial.title || 'Untitled',
    summary: (partial.summary || '').trim().slice(0, 200),
    tag,
    documentId,
    fileName: source?.file_name,
    pageNumber: source?.page_number,
    excerpt: source?.excerpt,
    followUpCount: 0,
    isWeakPoint: false,
    isChild: false,
  }
}

function getFallbackCards(documentId: string): CanvasCard[] {
  const selectedDoc = documents.value.find(d => d.id === documentId)
  const fileName = selectedDoc?.original_name || 'demo.pdf'
  
  return [
    {
      id: 'demo-1',
      title: isChineseLocale.value ? '向量空间的定义' : 'Vector Space Definition',
      summary: isChineseLocale.value
        ? '向量空间是定义了加法和数乘运算的集合，满足8条公理。它是线性代数的基础概念。'
        : 'A vector space is a set with addition and scalar multiplication operations satisfying 8 axioms. It is a fundamental concept in linear algebra.',
      tag: 'definition',
      documentId,
      fileName,
      pageNumber: 3,
      excerpt: isChineseLocale.value ? '向量空间 V 是一个集合...' : 'A vector space V is a set...',
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
    },
    {
      id: 'demo-2',
      title: isChineseLocale.value ? '线性变换公式' : 'Linear Transformation Formula',
      summary: isChineseLocale.value
        ? 'T(u+v) = T(u) + T(v) 且 T(cv) = cT(v)。这是判断线性变换的核心条件。'
        : 'T(u+v) = T(u) + T(v) and T(cv) = cT(v). These are the core conditions for linear transformations.',
      tag: 'formula',
      documentId,
      fileName,
      pageNumber: 7,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
    },
    {
      id: 'demo-3',
      title: isChineseLocale.value ? '基向量的例子' : 'Basis Vectors Example',
      summary: isChineseLocale.value
        ? 'R³ 的标准基是 {(1,0,0), (0,1,0), (0,0,1)}。任何向量都可以用基的线性组合表示。'
        : 'The standard basis of R³ is {(1,0,0), (0,1,0), (0,0,1)}. Any vector can be expressed as a linear combination of the basis.',
      tag: 'example',
      documentId,
      fileName,
      pageNumber: 5,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
    },
    {
      id: 'demo-4',
      title: isChineseLocale.value ? '易错：零向量的唯一性' : 'Common Mistake: Zero Vector Uniqueness',
      summary: isChineseLocale.value
        ? '学生常忘记零向量在向量空间中是唯一的。这由公理的组合可以证明。'
        : 'Students often forget that the zero vector is unique in a vector space. This can be proven from the combination of axioms.',
      tag: 'mistake',
      documentId,
      fileName,
      pageNumber: 4,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
    },
    {
      id: 'demo-5',
      title: isChineseLocale.value ? '特征值与特征向量' : 'Eigenvalues & Eigenvectors',
      summary: isChineseLocale.value
        ? 'Av = λv，其中 v≠0。求解特征方程 det(A-λI)=0。这是期末考试必考内容。'
        : 'Av = λv, where v≠0. Solve characteristic equation det(A-λI)=0. This is essential for final exams.',
      tag: 'exam',
      documentId,
      fileName,
      pageNumber: 12,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
      isExamFocus: true,  // 标记为高频考点
    },
    {
      id: 'demo-6',
      title: isChineseLocale.value ? '正交矩阵的性质' : 'Orthogonal Matrix Properties',
      summary: isChineseLocale.value
        ? '正交矩阵 Q 满足 Q^T Q = I。它保持向量长度和角度不变。'
        : 'An orthogonal matrix Q satisfies Q^T Q = I. It preserves vector length and angles.',
      tag: 'definition',
      documentId,
      fileName,
      pageNumber: 15,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: false,
    },
  ]
}

async function handleFollowUp(quickAction?: string) {
  if (!selectedCard.value) return
  
  let question = followUpQuestion.value.trim()
  
  if (quickAction === 'selection') {
    // Handle selected text follow-up
    if (!selectedText.value) {
      ElMessage.warning(t('learningCanvas.detail.selectTextFirst'))
      return
    }
    
    question = isChineseLocale.value
      ? `我选中了这段内容：「${selectedText.value}」。它来自知识点「${selectedCard.value.title}」。请只围绕这段选中内容解释，回答要适合学生复习，并尽量引用课件依据。`
      : `I selected this passage: "${selectedText.value}". It comes from the concept "${selectedCard.value.title}". Please explain only this selected passage for student review, and cite the course material where possible.`
  } else if (quickAction) {
    if (quickAction === 'simple') {
      question = isChineseLocale.value
        ? '请用更简单的语言解释这个知识点'
        : 'Please explain this concept in simpler terms'
    } else if (quickAction === 'example') {
      question = isChineseLocale.value
        ? '请举一个具体的例子'
        : 'Please give a concrete example'
    } else if (quickAction === 'quiz') {
      question = isChineseLocale.value
        ? '请基于这个知识点生成一道选择题和一道简答题'
        : 'Please generate one multiple-choice question and one short-answer question based on this concept'
    }
  }
  
  if (!question) {
    ElMessage.warning(t('knowledgeAsk.errors.enterQuestion'))
    return
  }
  
  asking.value = true

  if (isDemoCard(selectedCard.value)) {
    createDemoFollowUpCard(selectedCard.value, quickAction)
    followUpQuestion.value = ''
    selectedText.value = ''
    asking.value = false
    ElMessage.success(t('common.success'))
    return
  }
  
  try {
    const contextPrompt = quickAction === 'selection'
      ? question  // For selection, question already contains full context
      : isChineseLocale.value
        ? `我正在复习知识点「${selectedCard.value.title}」。摘要是：「${selectedCard.value.summary}」。请回答我的追问：${question}。回答要适合学生复习，并尽量引用课件依据。`
        : `I'm reviewing the concept "${selectedCard.value.title}". Summary: "${selectedCard.value.summary}". Please answer my follow-up: ${question}. The answer should be suitable for student review and cite the course material where possible.`
    
    const response = await askKnowledgeBase(
      contextPrompt,
      [selectedCard.value.documentId || selectedDocumentId.value || 'demo'],
    )
    
    // Create child card
    let childTitle = ''
    if (quickAction === 'selection') {
      childTitle = t('learningCanvas.detail.selectionExplanationTitle', {
        title: selectedCard.value.title,
      })
    } else if (quickAction === 'quiz') {
      childTitle = t('learningCanvas.quizTitle', { title: selectedCard.value.title })
    } else {
      childTitle = `${t('learningCanvas.tags.followup')}: ${selectedCard.value.title}`
    }
    
    const childCard: CanvasCard = {
      id: `child-${Date.now()}-${Math.random()}`,
      title: childTitle,
      summary: response.answer.slice(0, 300),
      tag: quickAction === 'quiz' ? 'quiz' : 'followup',
      documentId: response.sources[0]?.document_id || selectedCard.value.documentId,
      fileName: response.sources[0]?.file_name || selectedCard.value.fileName,
      pageNumber: response.sources[0]?.page_number || null,
      excerpt: response.sources[0]?.excerpt || undefined,
      followUpCount: 0,
      isWeakPoint: false,
      isChild: true,
      parentId: selectedCard.value.id,
      quizQuestion: quickAction === 'quiz' ? response.answer : undefined,
    }
    
    cards.value.push(childCard)
    markFollowedUp(selectedCard.value.id)
    
    followUpQuestion.value = ''
    selectedText.value = ''
    ElMessage.success(t('common.success'))
  } catch (error) {
    createDemoFollowUpCard(selectedCard.value, quickAction)
    followUpQuestion.value = ''
    selectedText.value = ''
    ElMessage.warning(t('learningCanvas.errors.askFailed'))
    console.error('Follow-up failed, using demo fallback:', error)
  } finally {
    asking.value = false
  }
}

function createDemoFollowUpCard(card: CanvasCard, quickAction?: string) {
  let demoAnswer = ''
  let childTitle = ''
  let quizQuestion = undefined
  let quizAnswer = undefined
  let quizExplanation = undefined
  
  if (quickAction === 'selection' && selectedText.value) {
    demoAnswer = isChineseLocale.value
      ? `这是关于选中文本「${selectedText.value.substring(0, 50)}...」的演示解释。在实际应用中，AI 会基于课件内容针对这段选中文本生成详细解释。`
      : `This is a demo explanation for the selected text "${selectedText.value.substring(0, 50)}...". In production, AI will generate detailed explanations based on course materials for this selected passage.`
    
    childTitle = t('learningCanvas.detail.selectionExplanationTitle', { title: card.title })
  } else if (quickAction === 'quiz') {
    // Generate structured quiz for demo mode
    childTitle = t('learningCanvas.quizTitle', { title: card.title })
    
    if (isChineseLocale.value) {
      quizQuestion = `关于「${card.title}」，以下哪个说法是正确的？\nA. 选项A（演示选项）\nB. 选项B（演示选项）\nC. 选项C（演示选项）\nD. 选项D（演示选项）`
      quizAnswer = 'C'
      quizExplanation = `这是演示模式的解析。在实际应用中，AI 会基于课件内容生成真实的自测题和详细解析。`
    } else {
      quizQuestion = `Regarding "${card.title}", which statement is correct?\nA. Option A (demo)\nB. Option B (demo)\nC. Option C (demo)\nD. Option D (demo)`
      quizAnswer = 'C'
      quizExplanation = `This is a demo explanation. In production, AI will generate real quiz questions and detailed explanations based on course materials.`
    }
    
    demoAnswer = quizQuestion
  } else {
    demoAnswer = isChineseLocale.value
      ? `这是关于「${card.title}」的演示解释。在实际应用中，AI 会基于课件内容生成详细回答。`
      : `This is a demo explanation for "${card.title}". In production, AI will generate detailed answers based on course materials.`
    
    childTitle = `${t('learningCanvas.tags.followup')}: ${card.title}`
  }

  const childCard: CanvasCard = {
    id: `child-demo-${Date.now()}-${Math.random()}`,
    title: childTitle,
    summary: demoAnswer,
    tag: quickAction === 'quiz' ? 'quiz' : 'followup',
    documentId: card.documentId,
    fileName: card.fileName,
    pageNumber: card.pageNumber,
    excerpt: isChineseLocale.value ? '演示模式' : 'Demo Mode',
    followUpCount: 0,
    isWeakPoint: false,
    isChild: true,
    parentId: card.id,
    isFallback: true,  // 标记为 fallback
    quizQuestion,
    quizAnswer,
    quizExplanation,
  }

  cards.value.push(childCard)
  markFollowedUp(card.id)
}

function markFollowedUp(cardId: string) {
  const parentIndex = cards.value.findIndex(c => c.id === cardId)
  if (parentIndex !== -1) {
    cards.value[parentIndex].followUpCount++
    if (cards.value[parentIndex].followUpCount >= 2) {
      cards.value[parentIndex].isWeakPoint = true
    }
    
    // 如果是 demo 卡片，保存学习信号
    if (cards.value[parentIndex].isDemo) {
      saveLearningSignals()
    }
  }
}

function selectCard(cardId: string) {
  selectedCardId.value = cardId === selectedCardId.value ? '' : cardId
  followUpQuestion.value = ''
  selectedText.value = ''
}

function handleTextSelection() {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    return
  }
  
  const text = selection.toString().trim()
  if (text.length === 0) {
    return
  }
  
  // Limit to 300 characters
  selectedText.value = text.length > 300 ? text.substring(0, 300) + '...' : text
}

function clearSelection() {
  selectedText.value = ''
  window.getSelection()?.removeAllRanges()
}

function getParentTitle(card: CanvasCard): string {
  if (!card.parentId) return ''
  return cards.value.find((candidate) => candidate.id === card.parentId)?.title || ''
}

function getTagColor(tag: CanvasCard['tag']): string {
  const colors = {
    definition: '#409EFF',
    formula: '#67C23A',
    example: '#E6A23C',
    mistake: '#F56C6C',
    exam: '#F59E0B',
    followup: '#8B5CF6',
    quiz: '#EC4899',
  }
  return colors[tag] || '#909399'
}

function handleBack() {
  router.push('/')
}
</script>

<template>
  <div class="learning-canvas">
    <el-container class="canvas-container">
      <!-- Header -->
      <el-header class="canvas-header">
        <div class="header-content">
          <el-button
            text
            @click="handleBack"
          >
            <el-icon>
              <svg
                viewBox="0 0 1024 1024"
                xmlns="http://www.w3.org/2000/svg"
              ><path
                fill="currentColor"
                d="M224 480h640a32 32 0 1 1 0 64H224a32 32 0 0 1 0-64z"
              /><path
                fill="currentColor"
                d="m237.248 512 265.408 265.344a32 32 0 0 1-45.312 45.312l-288-288a32 32 0 0 1 0-45.312l288-288a32 32 0 1 1 45.312 45.312L237.248 512z"
              /></svg>
            </el-icon>
            {{ t('common.back') }}
          </el-button>
          <div>
            <h1 class="canvas-title">
              {{ t('learningCanvas.title') }}
            </h1>
            <p class="canvas-subtitle">
              {{ t('learningCanvas.subtitle') }}
            </p>
          </div>
        </div>
        
        <!-- Stats Bar -->
        <div
          v-if="cards.length > 0"
          class="canvas-stats"
        >
          <div class="stat-item">
            <span class="stat-value">{{ statsData.concepts }}</span>
            <span class="stat-label">{{ t('learningCanvas.stats.concepts') }}</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-value">{{ statsData.followups }}</span>
            <span class="stat-label">{{ t('learningCanvas.stats.followups') }}</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-value">{{ statsData.weakPoints }}</span>
            <span class="stat-label">{{ t('learningCanvas.stats.weakPoints') }}</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-value">{{ statsData.examFocus }}</span>
            <span class="stat-label">{{ t('learningCanvas.stats.examFocus') }}</span>
          </div>
        </div>
      </el-header>

      <el-container class="canvas-main">
        <!-- Left Sidebar -->
        <el-aside
          width="280px"
          class="canvas-sidebar"
        >
          <el-card shadow="never">
            <template #header>
              <strong>{{ t('learningCanvas.sidebar.selectDocument') }}</strong>
            </template>

            <div
              v-if="succeededDocuments.length === 0"
              class="empty-docs"
            >
              <el-empty
                :description="t('learningCanvas.sidebar.noDocuments')"
                :image-size="60"
              >
                <el-button
                  size="small"
                  @click="router.push('/documents')"
                >
                  {{ t('learningCanvas.sidebar.goUpload') }}
                </el-button>
                <el-button
                  size="default"
                  @click="loadDemoCanvas"
                >
                  {{ t('learningCanvas.sidebar.loadDemo') }}
                </el-button>
                <el-button
                  type="primary"
                  size="default"
                  class="sidebar-full-button"
                  @click="resetDemoMode"
                >
                  {{ t('learningCanvas.sidebar.demoMode') }}
                </el-button>
              </el-empty>
            </div>

            <div v-else>
              <el-select
                v-model="selectedDocumentId"
                :placeholder="t('learningCanvas.sidebar.selectDocument')"
                style="width: 100%"
                :disabled="generating"
              >
                <el-option
                  v-for="doc in succeededDocuments"
                  :key="doc.id"
                  :label="doc.original_name"
                  :value="doc.id"
                />
              </el-select>

              <el-button
                type="primary"
                :loading="generating"
                :disabled="!selectedDocumentId"
                style="width: 100%; margin-top: 16px"
                @click="generateCanvas"
              >
                {{ generating ? t('learningCanvas.sidebar.generating') : t('learningCanvas.sidebar.generateCanvas') }}
              </el-button>

              <el-button
                style="width: 100%; margin-top: 10px"
                :disabled="generating"
                @click="loadDemoCanvas"
              >
                {{ t('learningCanvas.sidebar.loadDemo') }}
              </el-button>

              <el-button
                type="primary"
                style="width: 100%; margin-top: 10px"
                @click="resetDemoMode"
              >
                {{ t('learningCanvas.sidebar.demoMode') }}
              </el-button>

              <el-button
                style="width: 100%; margin-top: 10px"
                :disabled="cards.length === 0"
                @click="clearCanvas"
              >
                {{ t('learningCanvas.sidebar.clearCanvas') }}
              </el-button>

              <el-button
                style="width: 100%; margin-top: 10px"
                @click="resetLearningSignals"
              >
                {{ t('learningCanvas.sidebar.resetLearning') }}
              </el-button>

              <el-divider />

              <div
                v-if="cards.length > 0"
                class="card-stats"
              >
                <el-tag type="info">
                  {{ t('learningCanvas.canvas.cardCount', { count: rootCards.length }) }}
                </el-tag>
                <el-tag>
                  {{ t('learningCanvas.canvas.totalCardCount', { count: cards.length }) }}
                </el-tag>
              </div>
            </div>

            <template v-if="cards.length > 0 && cards[0]?.isDemo">
              <el-divider />

              <!-- Demo Guide Steps -->
              <div class="demo-guide">
                <div class="demo-guide-title">
                  {{ t('learningCanvas.demoGuide.title') }}
                </div>
                <el-steps
                  :active="demoGuideStep"
                  direction="vertical"
                  :space="60"
                >
                  <el-step :title="t('learningCanvas.demoGuide.stepLoad')" />
                  <el-step :title="t('learningCanvas.demoGuide.stepAsk')" />
                  <el-step :title="t('learningCanvas.demoGuide.stepQuiz')" />
                </el-steps>
              </div>
              
              <el-divider />
              
              <!-- Demo Check Panel -->
              <div class="demo-check">
                <div class="demo-check-header">
                  <div class="demo-check-title">
                    {{ t('learningCanvas.demoCheck.title') }}
                  </div>
                  <el-button
                    size="small"
                    :loading="demoCheckLoading"
                    @click="checkDemoStatus"
                  >
                    {{ demoCheckLoading ? t('learningCanvas.demoCheck.checking') : t('learningCanvas.demoCheck.refresh') }}
                  </el-button>
                </div>
                
                <div class="demo-check-items">
                  <!-- Login Status -->
                  <div class="demo-check-item">
                    <span class="demo-check-label">{{ t('learningCanvas.demoCheck.login') }}</span>
                    <el-tag
                      :type="isLoggedIn ? 'success' : 'info'"
                      size="small"
                    >
                      {{ isLoggedIn ? t('learningCanvas.demoCheck.loginYes') : t('learningCanvas.demoCheck.loginNo') }}
                    </el-tag>
                  </div>
                  
                  <!-- Backend Status -->
                  <div class="demo-check-item">
                    <span class="demo-check-label">{{ t('learningCanvas.demoCheck.backend') }}</span>
                    <el-tag
                      :type="backendHealthy ? 'success' : 'danger'"
                      size="small"
                    >
                      {{ backendHealthy ? t('learningCanvas.demoCheck.backendHealthy') : t('learningCanvas.demoCheck.backendUnavailable') }}
                    </el-tag>
                  </div>
                  
                  <!-- Demo Canvas -->
                  <div class="demo-check-item">
                    <span class="demo-check-label">{{ t('learningCanvas.demoCheck.demoCanvas') }}</span>
                    <el-tag
                      type="success"
                      size="small"
                    >
                      {{ t('learningCanvas.demoCheck.demoCanvasAvailable') }}
                    </el-tag>
                  </div>
                  
                  <!-- AI Service -->
                  <div class="demo-check-item">
                    <span class="demo-check-label">{{ t('learningCanvas.demoCheck.aiService') }}</span>
                    <span class="demo-check-note">{{ t('learningCanvas.demoCheck.aiServiceNote') }}</span>
                  </div>
                </div>
              </div>
            </template>
          </el-card>
        </el-aside>

        <!-- Center Canvas -->
        <el-main class="canvas-area">
          <div
            v-if="cards.length === 0"
            class="canvas-empty"
          >
            <el-empty
              :description="t('learningCanvas.emptyState.description')"
              :image-size="120"
            >
              <div class="canvas-empty-actions">
                <el-button
                  type="primary"
                  size="large"
                  @click="resetDemoMode"
                >
                  {{ t('learningCanvas.sidebar.demoMode') }}
                </el-button>
                <el-button
                  size="large"
                  @click="router.push('/documents')"
                >
                  {{ t('learningCanvas.emptyState.goUpload') }}
                </el-button>
              </div>
            </el-empty>
          </div>

          <div
            v-else
            class="canvas-grid"
          >
            <div
              v-for="card in canvasCards"
              :key="card.id"
              class="canvas-card"
              :class="{ selected: selectedCardId === card.id, 'weak-point': card.isWeakPoint, 'child-node': card.isChild }"
              @click="selectCard(card.id)"
            >
              <div
                class="card-tag"
                :style="{ backgroundColor: getTagColor(card.tag) }"
              >
                {{ t(`learningCanvas.tags.${card.tag}`) }}
              </div>

              <div class="card-source-badge">
                <el-tag 
                  :type="card.isDemo || card.isFallback ? 'info' : 'success'" 
                  size="small"
                >
                  {{ getCardSourceLabel(card) }}
                </el-tag>
              </div>

              <h3 class="card-title">
                {{ card.title }}
              </h3>
              <p
                v-if="card.isChild"
                class="card-parent"
              >
                {{ t('learningCanvas.canvas.childOf', { title: getParentTitle(card) }) }}
              </p>
              
              <!-- Quiz card structure -->
              <div v-if="card.tag === 'quiz' && card.quizQuestion">
                <div class="quiz-card-label">
                  <strong>
                    {{ t('learningCanvas.quizQuestion') }}
                  </strong>
                </div>
                <p class="card-summary quiz-card-question">
                  {{ card.quizQuestion.substring(0, 100) }}{{ card.quizQuestion.length > 100 ? '...' : '' }}
                </p>
              </div>
              
              <!-- Regular card summary -->
              <p
                v-else
                class="card-summary"
              >
                {{ card.summary }}
              </p>

              <div class="card-footer">
                <div class="card-source">
                  <el-icon>
                    <svg
                      viewBox="0 0 1024 1024"
                      xmlns="http://www.w3.org/2000/svg"
                    ><path
                      fill="currentColor"
                      d="M832 384H576V128H192v768h640V384zm-26.496-64L640 154.496V320h165.504zM160 64h480l256 256v608a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32z"
                    /></svg>
                  </el-icon>
                  <span v-if="card.pageNumber">{{ t('learningCanvas.detail.page', { page: card.pageNumber }) }}</span>
                  <span v-else-if="card.fileName">{{ card.fileName }}</span>
                </div>
                <div
                  v-if="card.followUpCount > 0"
                  class="follow-up-badge"
                >
                  <el-badge
                    :value="card.followUpCount"
                    type="warning"
                  />
                </div>
              </div>

              <div
                v-if="card.isWeakPoint"
                class="weak-point-badge"
              >
                <el-tag
                  type="danger"
                  size="small"
                >
                  {{ t('learningCanvas.detail.weakPoint') }}
                </el-tag>
              </div>
              
              <div
                v-if="card.tag === 'exam' || card.isExamFocus"
                class="exam-focus-badge"
              >
                <el-tag
                  type="warning"
                  size="small"
                >
                  {{ t('learningCanvas.examFocus') }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-main>

        <!-- Right Detail Panel -->
        <el-aside
          width="360px"
          class="canvas-detail"
        >
          <el-card
            shadow="never"
            class="detail-card"
          >
            <template #header>
              <strong>{{ t('learningCanvas.detail.title') }}</strong>
            </template>

            <div
              v-if="!selectedCard"
              class="no-selection"
            >
              <el-empty
                :description="t('learningCanvas.detail.noSelection')"
                :image-size="80"
              />
              <p class="hint">
                {{ t('learningCanvas.canvas.selectCard') }}
              </p>
            </div>

            <div
              v-else
              class="detail-content"
            >
              <div
                class="detail-tag"
                :style="{ backgroundColor: getTagColor(selectedCard.tag) }"
              >
                {{ t(`learningCanvas.tags.${selectedCard.tag}`) }}
              </div>

              <h3 class="detail-title">
                {{ selectedCard.title }}
              </h3>
              <p 
                class="detail-summary"
                @mouseup="handleTextSelection"
              >
                {{ selectedCard.summary }}
              </p>

              <el-divider />

              <div
                class="answer-scope-notice"
                style="margin-bottom: 16px;"
              >
                <el-alert
                  :title="t('learningCanvas.detail.answerScope')"
                  type="info"
                  :closable="false"
                  show-icon
                />
              </div>

              <div
                v-if="selectedCard.excerpt || selectedCard.pageNumber || selectedCard.fileName"
                class="detail-source"
              >
                <h4>{{ t('learningCanvas.detail.source') }}</h4>
                
                <div
                  v-if="hasVerifiedSource(selectedCard)"
                  style="margin-bottom: 8px;"
                >
                  <el-tag
                    type="success"
                    size="small"
                  >
                    {{ t('learningCanvas.canvas.verifiedSource') }}
                  </el-tag>
                </div>
                
                <p
                  v-if="selectedCard.fileName"
                  class="source-page"
                >
                  {{ t('learningCanvas.detail.sourceFile', { fileName: selectedCard.fileName }) }}
                </p>
                <p
                  v-if="selectedCard.pageNumber"
                  class="source-page"
                >
                  {{ t('learningCanvas.detail.page', { page: selectedCard.pageNumber }) }}
                </p>
                <p
                  v-if="selectedCard.excerpt"
                  class="source-excerpt"
                  @mouseup="handleTextSelection"
                >
                  "{{ selectedCard.excerpt }}"
                </p>
              </div>
              
              <div
                v-else
                class="detail-source"
              >
                <h4>{{ t('learningCanvas.detail.source') }}</h4>
                <p class="source-page">
                  {{ t('learningCanvas.detail.noSource') }}
                </p>
              </div>

              <el-divider />

              <div class="detail-followup">
                <h4>{{ t('learningCanvas.detail.followUp') }}</h4>
                
                <!-- Selected text display -->
                <div
                  v-if="selectedText"
                  class="selected-text-box"
                >
                  <div class="selected-text-header">
                    <strong>{{ t('learningCanvas.detail.selectedText') }}</strong>
                    <el-button
                      size="small"
                      text
                      @click="clearSelection"
                    >
                      {{ t('learningCanvas.detail.clearSelection') }}
                    </el-button>
                  </div>
                  <div class="selected-text-content">
                    {{ selectedText }}
                  </div>
                </div>
                
                <div class="quick-actions">
                  <el-button
                    size="small"
                    :disabled="asking"
                    @click="handleFollowUp('simple')"
                  >
                    {{ t('learningCanvas.detail.explainSimply') }}
                  </el-button>
                  <el-button
                    size="small"
                    :disabled="asking"
                    @click="handleFollowUp('example')"
                  >
                    {{ t('learningCanvas.detail.giveExample') }}
                  </el-button>
                  <el-button
                    size="small"
                    :disabled="asking"
                    @click="handleFollowUp('quiz')"
                  >
                    {{ t('learningCanvas.detail.generateQuiz') }}
                  </el-button>
                  <el-button
                    size="small"
                    type="success"
                    :disabled="!selectedText || asking"
                    @click="handleFollowUp('selection')"
                  >
                    {{ t('learningCanvas.detail.askSelection') }}
                  </el-button>
                </div>

                <el-input
                  v-model="followUpQuestion"
                  type="textarea"
                  :rows="3"
                  :placeholder="t('learningCanvas.detail.followUpPlaceholder')"
                  :disabled="asking"
                  style="margin-top: 12px"
                />

                <el-button
                  type="primary"
                  :loading="asking"
                  :disabled="!followUpQuestion.trim() || asking"
                  style="width: 100%; margin-top: 12px"
                  @click="handleFollowUp()"
                >
                  {{ asking ? t('learningCanvas.detail.asking') : t('learningCanvas.detail.askButton') }}
                </el-button>
              </div>

              <div
                v-if="childCards.length > 0"
                class="child-cards"
              >
                <el-divider />
                <h4>{{ t('learningCanvas.detail.followUpCount', { count: childCards.length }) }}</h4>
                <div
                  v-for="child in childCards"
                  :key="child.id"
                  class="child-card"
                >
                  <div
                    class="child-tag"
                    :style="{ backgroundColor: getTagColor(child.tag) }"
                  >
                    {{ t(`learningCanvas.tags.${child.tag}`) }}
                  </div>
                  
                  <!-- Quiz card structure -->
                  <div v-if="child.tag === 'quiz' && (child.quizQuestion || child.quizAnswer)">
                    <div
                      v-if="child.quizQuestion"
                      class="quiz-section"
                    >
                      <strong class="quiz-section-title">
                        {{ t('learningCanvas.quizQuestion') }}
                      </strong>
                      <p class="child-summary quiz-card-question">
                        {{ child.quizQuestion }}
                      </p>
                    </div>
                    
                    <div
                      v-if="child.quizAnswer"
                      class="quiz-section quiz-section-spaced"
                    >
                      <strong class="quiz-section-title">
                        {{ t('learningCanvas.quizAnswer') }}
                      </strong>
                      <p class="child-summary">
                        {{ child.quizAnswer }}
                      </p>
                    </div>
                    
                    <div
                      v-if="child.quizExplanation"
                      class="quiz-section quiz-section-spaced"
                    >
                      <strong class="quiz-section-title">
                        {{ t('learningCanvas.quizExplanation') }}
                      </strong>
                      <p class="child-summary">
                        {{ child.quizExplanation }}
                      </p>
                    </div>
                  </div>
                  
                  <!-- Regular card summary -->
                  <p
                    v-else
                    class="child-summary"
                  >
                    {{ child.summary }}
                  </p>
                </div>
              </div>
            </div>
          </el-card>
        </el-aside>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
.learning-canvas {
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.canvas-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.canvas-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  padding: 0;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  padding: 16px 24px;
}

.canvas-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.canvas-subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.canvas-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding: 12px 24px;
  background: rgba(102, 126, 234, 0.08);
  border-top: 1px solid rgba(102, 126, 234, 0.15);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(0, 0, 0, 0.1);
}

.canvas-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.canvas-empty-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.canvas-sidebar {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  overflow-y: auto;
  padding: 16px;
}

.empty-docs {
  padding: 20px 0;
}

.sidebar-full-button {
  width: 100%;
}

.demo-guide {
  margin-bottom: 16px;
}

.demo-guide-title {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.demo-check {
  margin-bottom: 16px;
}

.demo-check-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.demo-check-title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.demo-check-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.demo-check-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.demo-check-label {
  color: var(--el-text-color-regular);
  flex-shrink: 0;
  margin-right: 8px;
}

.demo-check-note {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-align: right;
  line-height: 1.4;
}

.card-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.canvas-area {
  background: #f5f7fa;
  background-image: 
    linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
  overflow-y: auto;
  padding: 24px;
}

.canvas-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.canvas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.canvas-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  border: 2px solid transparent;
}

.canvas-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.canvas-card.selected {
  border-color: #409EFF;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
}

.canvas-card.weak-point {
  border-color: #F56C6C;
}

.canvas-card.child-node {
  margin-left: 20px;
  border-style: dashed;
  background: #fbfdff;
}

.canvas-card.child-node::before {
  content: "";
  position: absolute;
  top: 28px;
  left: -22px;
  width: 22px;
  border-top: 2px solid var(--el-border-color);
}

.card-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.card-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.card-parent {
  margin: -6px 0 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-summary {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.card-source {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.weak-point-badge {
  position: absolute;
  top: 12px;
  right: 12px;
}

.exam-focus-badge {
  position: absolute;
  top: 48px;
  right: 12px;
}

.quiz-section {
  margin-bottom: 8px;
}

.quiz-section-spaced {
  margin-top: 12px;
}

.quiz-section-title {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

.quiz-card-label {
  margin-bottom: 8px;
}

.quiz-card-label strong {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.quiz-card-question {
  white-space: pre-line;
}

.selected-text-box {
  margin-bottom: 12px;
  padding: 12px;
  background-color: var(--el-fill-color-light);
  border-left: 3px solid var(--el-color-primary);
  border-radius: 4px;
}

.selected-text-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.selected-text-header strong {
  font-size: 14px;
}

.selected-text-content {
  max-height: 60px;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.6;
  text-overflow: ellipsis;
}

.canvas-detail {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-left: 1px solid rgba(0, 0, 0, 0.06);
  overflow-y: auto;
  padding: 16px;
}

.detail-card {
  height: 100%;
}

.no-selection {
  text-align: center;
  padding: 40px 20px;
}

.hint {
  margin-top: 16px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.detail-content {
  font-size: 14px;
}

.detail-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.detail-title {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.detail-summary {
  margin: 0;
  line-height: 1.8;
  color: var(--el-text-color-regular);
}

.detail-source h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.source-page {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.source-excerpt {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  font-style: italic;
}

.detail-followup h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-actions .el-button {
  flex: 1;
  min-width: 0;
}

.child-cards h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.child-card {
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  margin-bottom: 12px;
}

.child-card:last-child {
  margin-bottom: 0;
}

.child-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  color: white;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
}

.child-summary {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.card-source-badge {
  position: absolute;
  top: 48px;
  right: 12px;
  z-index: 1;
}

.answer-scope-notice {
  margin-bottom: 16px;
}
</style>
