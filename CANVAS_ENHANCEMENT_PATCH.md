# CourseMind 学习画布产品增强补丁

本文档记录了需要对 `LearningCanvasView.vue` 进行的关键修改。

## 1. 添加类型定义

在 `interface CanvasCard` 中添加两个新字段：

```typescript
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
  isDemo?: boolean  // 新增：标记是否为演示数据
  isFallback?: boolean  // 新增：标记是否为 fallback 回答
}

// 新增类型
interface LearningSignal {
  cardId: string
  followUpCount: number
  isWeakPoint: boolean
}
```

## 2. 添加 localStorage 常量和函数

在 State 部分之前添加：

```typescript
// LocalStorage key for learning signals
const LEARNING_SIGNALS_KEY = 'coursemind_canvas_learning_signals'
```

在 Methods 部分添加：

```typescript
// LocalStorage functions
function saveLearningSignals() {
  const signals: LearningSignal[] = cards.value
    .filter(card => card.isDemo && !card.isChild)  // 只保存 demo 根卡片
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

// Clear canvas
function clearCanvas() {
  cards.value = []
  selectedCardId.value = ''
  followUpQuestion.value = ''
}

// Reset learning signals
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
    
    // Clear localStorage
    clearLearningSignals()
    
    // Reset current cards
    cards.value.forEach(card => {
      if (card.isDemo && !card.isChild) {
        card.followUpCount = 0
        card.isWeakPoint = false
      }
    })
    
    ElMessage.success(t('learningCanvas.sidebar.resetSuccess'))
  } catch (error) {
    // User cancelled
  }
}
```

## 3. 修改 loadDemoCanvas 函数

```typescript
function loadDemoCanvas() {
  const demoDocumentId = 'demo-document'
  const demoCards = getFallbackCards(demoDocumentId)
  
  // Load saved learning signals
  const signals = loadLearningSignals()
  
  // Apply saved signals to demo cards
  demoCards.forEach(card => {
    card.isDemo = true  // 标记为演示数据
    const signal = signals.get(card.id)
    if (signal) {
      card.followUpCount = signal.followUpCount
      card.isWeakPoint = signal.isWeakPoint
    }
  })
  
  cards.value = demoCards
  selectedCardId.value = demoCards[0]?.id || ''
  followUpQuestion.value = ''
}
```

## 4. 修改 getFallbackCards 函数

在每张卡片中添加 `isDemo: true`：

```typescript
function getFallbackCards(documentId: string): CanvasCard[] {
  const fileName = documentId === 'demo-document' ? 'demo.pdf' : 'demo.pdf'
  
  return [
    {
      id: 'demo-1',
      // ... 其他字段
      isDemo: true,  // 添加这行
    },
    // ... 其他卡片同样添加
  ]
}
```

## 5. 修改 handleFollowUp 函数中创建子卡片部分

在创建子卡片时添加 `isFallback` 标记：

```typescript
// 在 catch 块中创建 fallback 子卡片
const childCard: CanvasCard = {
  // ... 其他字段
  isFallback: true,  // 标记为 fallback
  excerpt: isChineseLocale.value ? '演示模式' : 'Demo Mode',
}

// 在成功创建子卡片时
const childCard: CanvasCard = {
  // ... 其他字段
  isFallback: false,  // 非 fallback
}

// 在更新父卡片后，保存学习信号
if (cards.value[parentIndex].isDemo) {
  saveLearningSignals()
}
```

## 6. 添加辅助函数

```typescript
// 判断卡片是否有可验证来源
function hasVerifiedSource(card: CanvasCard): boolean {
  return !!(card.fileName && card.pageNumber && card.excerpt && !card.isFallback)
}

// 获取卡片数据来源标签
function getCardSourceLabel(card: CanvasCard): string {
  if (card.isFallback) {
    return t('learningCanvas.canvas.demoExplanation')
  }
  if (card.isDemo) {
    return t('learningCanvas.canvas.demoData')
  }
  return t('learningCanvas.canvas.fromUploadedMaterial')
}
```

## 7. 模板修改要点

### 左侧操作区添加按钮：

```vue
<el-button
  @click="clearCanvas"
  :disabled="cards.length === 0"
>
  {{ t('learningCanvas.sidebar.clearCanvas') }}
</el-button>

<el-button
  @click="resetLearningSignals"
>
  {{ t('learningCanvas.sidebar.resetLearning') }}
</el-button>
```

### 卡片上显示数据来源标签：

```vue
<div class="card-source-badge">
  <el-tag :type="card.isDemo ? 'info' : 'success'" size="small">
    {{ getCardSourceLabel(card) }}
  </el-tag>
</div>
```

### 右侧详情区添加回答范围说明：

```vue
<div class="answer-scope-notice">
  <el-alert
    :title="t('learningCanvas.detail.answerScope')"
    type="info"
    :closable="false"
    show-icon
  />
</div>

<div v-if="hasVerifiedSource(selectedCard)" class="verified-source">
  <el-tag type="success" size="small">
    {{ t('learningCanvas.canvas.verifiedSource') }}
  </el-tag>
</div>
```

---

由于文件较大（1096行），我建议手动应用这些补丁，或者我可以为您生成完整的新文件。

请确认是否需要我生成完整的新版本文件？
