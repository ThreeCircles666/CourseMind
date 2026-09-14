# CourseMind 选中文字局部追问功能 - 完成报告

## ✅ 修改的文件（3个）

### 1. `frontend/src/i18n/locales/zh-CN.ts`

**新增翻译**：
- `learningCanvas.detail.askSelection`: '追问选中内容'
- `learningCanvas.detail.selectedText`: '已选中'
- `learningCanvas.detail.clearSelection`: '清除'

### 2. `frontend/src/i18n/locales/en-US.ts`

**对应英文翻译**：
- `learningCanvas.detail.askSelection`: 'Ask Selection'
- `learningCanvas.detail.selectedText`: 'Selected'
- `learningCanvas.detail.clearSelection`: 'Clear'

### 3. `frontend/src/views/LearningCanvasView.vue`

**新增状态**：
- `selectedText = ref('')` - 保存选中的文本

**新增函数**：
- `handleTextSelection()` - 监听文本选择事件
- `clearSelection()` - 清除选中文本

**更新函数**：
- `selectCard()` - 切换卡片时清空选中文本
- `handleFollowUp()` - 支持 `quickAction === 'selection'`
- `createDemoFollowUpCard()` - 支持选中文本的 fallback

**模板更新**：
- 详情摘要 `<p class="detail-summary">` 添加 `@mouseup` 事件
- 来源片段 `<p class="source-excerpt">` 添加 `@mouseup` 事件
- 追问区域添加"已选中"文本显示框
- 快捷按钮区域添加"追问选中内容"按钮（success 类型）

---

## 🎯 如何操作"选中文字局部追问"

### 完整操作流程

```
1. 打开学习画布 → 加载演示画布（或生成真实画布）
   ↓
2. 点击任意知识卡片 → 右侧显示详情
   ↓
3. 在右侧详情区用鼠标选中文字
   - 可选中"摘要"中的文字
   - 或选中"原文片段"中的文字
   ↓
4. 松开鼠标（mouseup）
   ↓
5. 右侧追问区顶部出现"已选中"框
   - 显示选中的文本（最多 2-3 行）
   - 右上角有"清除"按钮
   ↓
6. 快捷按钮区出现"追问选中内容"按钮（绿色，可点击）
   ↓
7. 点击"追问选中内容"
   ↓
8. AI 针对选中文本生成解释
   ↓
9. 子卡片回写到画布
   - 标题：选中内容解释：{原卡片标题}
   - 内容：针对选中文本的解释
```

### 具体示例

**场景**：学习"向量空间的定义"卡片

1. **选中文本**：用鼠标选中摘要中的"满足8条公理"
2. **已选中框显示**：
   ```
   已选中                    [清除]
   满足8条公理
   ```
3. **点击"追问选中内容"**
4. **AI 提问内容**（自动生成）：
   ```
   我选中了这段内容：「满足8条公理」。
   它来自知识点「向量空间的定义」。
   请只围绕这段选中内容解释，回答要适合学生复习，并尽量引用课件依据。
   ```
5. **生成子卡片**：
   - 标题：`选中内容解释：向量空间的定义`
   - 内容：详细解释8条公理是什么
   - 标签：追问解释（蓝色）

---

## 💡 技术实现细节

### 1. 文本选择监听

```typescript
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
```

**特点**：
- 使用 `window.getSelection()` API
- 自动截断超过 300 字符的文本
- 在 mouseup 事件时触发

### 2. 选中内容追问 Prompt

**中文 Prompt**：
```typescript
`我选中了这段内容：「${selectedText.value}」。它来自知识点「${selectedCard.value.title}」。请只围绕这段选中内容解释，回答要适合学生复习，并尽量引用课件依据。`
```

**英文 Prompt**：
```typescript
`I selected this passage: "${selectedText.value}". It comes from the concept "${selectedCard.value.title}". Please explain only this selected passage for student review, and cite the course material where possible.`
```

**设计要点**：
- 明确告知 AI 这是选中的内容
- 提供上下文（来自哪个知识点）
- 要求只解释选中内容（不发散）
- 要求引用课件依据

### 3. 子卡片标题

**中文**：
```typescript
`选中内容解释：${selectedCard.value.title}`
```

**英文**：
```typescript
`Selection Explanation: ${selectedCard.value.title}`
```

**与普通追问的区别**：
- 普通追问：`追问解释：向量空间的定义`
- 选中追问：`选中内容解释：向量空间的定义`

### 4. 清除选中文本

```typescript
function clearSelection() {
  selectedText.value = ''
  window.getSelection()?.removeAllRanges()
}
```

**触发时机**：
- 用户点击"清除"按钮
- 用户切换到其他卡片
- 用户提交追问后

---

## 🎨 UI 设计

### "已选中"文本框

```
┌─────────────────────────────────────┐
│ 已选中                    [清除]    │
├─────────────────────────────────────┤
│ 向量空间是定义了加法和数乘运算的    │
│ 集合，满足8条公理...                │
└─────────────────────────────────────┘
```

**样式**：
- 背景色：浅灰色 `var(--el-fill-color-light)`
- 左边框：3px 蓝色 `var(--el-color-primary)`
- 内边距：12px
- 文本：最多显示 2-3 行（60px 高度）

### 快捷按钮布局

**改进前**：
```
[解释得更简单] [举一个例子] [生成自测题]
```

**改进后**：
```
[解释得更简单] [举一个例子] [生成自测题] [追问选中内容]
                                          ↑ 绿色，有选中文本时可点击
```

**按钮样式**：
- 类型：`success`（绿色）
- 尺寸：`small`
- Disabled：`!selectedText || asking`

---

## 🔄 Fallback 场景表现

### 场景 1：Demo 卡片 + 选中文本

**操作**：
1. 加载演示画布
2. 选中"向量空间的定义"卡片中的"满足8条公理"
3. 点击"追问选中内容"

**Fallback 行为**：
```typescript
demoAnswer = isChineseLocale.value
  ? `这是关于选中文本「${selectedText.value.substring(0, 50)}...」的演示解释。在实际应用中，AI 会基于课件内容针对这段选中文本生成详细解释。`
  : `This is a demo explanation for the selected text "${selectedText.value.substring(0, 50)}...". In production, AI will generate detailed explanations based on course materials for this selected passage.`

childTitle = isChineseLocale.value
  ? `选中内容解释：${card.title}`
  : `Selection Explanation: ${card.title}`
```

**生成子卡片**：
- 标题：`选中内容解释：向量空间的定义`
- 内容：明确说明这是演示解释
- 标签：`followup`（蓝色）
- 来源：`演示模式` / `Demo Mode`
- `isFallback: true`

### 场景 2：真实卡片 + RAG API 失败

**操作**：
1. 上传真实文档并生成画布
2. 选中卡片中的文字
3. 点击"追问选中内容"
4. RAG API 调用失败（无 API Key 或网络错误）

**Fallback 行为**：
- 进入 `catch` 块
- 调用 `createDemoFollowUpCard(selectedCard.value, 'selection')`
- 生成 fallback 子卡片（同场景 1）
- 显示警告消息：`追问失败，请重试`

**用户体验**：
- ✅ 不会卡住
- ✅ 仍然生成子卡片
- ✅ 明确标注为演示模式
- ✅ 不伪装成真实 AI

### 场景 3：真实卡片 + RAG API 成功

**操作**：
1. 上传真实文档并生成画布
2. 选中卡片中的文字
3. 点击"追问选中内容"
4. RAG API 调用成功

**正常行为**：
```typescript
const contextPrompt = `我选中了这段内容：「${selectedText.value}」。它来自知识点「${selectedCard.value.title}」。请只围绕这段选中内容解释，回答要适合学生复习，并尽量引用课件依据。`

const response = await askKnowledgeBase(contextPrompt, [documentId])
```

**生成子卡片**：
- 标题：`选中内容解释：{原标题}`
- 内容：AI 生成的真实解释（前 300 字符）
- 标签：`followup`
- 来源：从 RAG 返回的真实来源
- `isFallback: false`

---

## 📊 功能对比

| 追问方式 | 触发方式 | Prompt 内容 | 子卡片标题 |
|---------|---------|------------|-----------|
| **普通追问** | 输入框输入 | `我正在复习知识点「xxx」。摘要是：「xxx」。请回答我的追问：{question}` | `追问解释：xxx` |
| **快捷追问** | 点击快捷按钮 | `请用更简单的语言解释这个知识点` | `追问解释：xxx` |
| **选中追问** | 选中文本后点击 | `我选中了这段内容：「{text}」。它来自知识点「xxx」。请只围绕这段选中内容解释...` | `选中内容解释：xxx` |

### 核心差异

**选中追问的独特之处**：
1. ✅ 局部性：只针对选中文本，不是整个知识点
2. ✅ 精确性：明确告知 AI 要解释的具体内容
3. ✅ 上下文：保留来源知识点信息
4. ✅ 用户主动：用户明确选择感兴趣的部分

---

## 🎯 使用场景示例

### 场景 1：不理解某个专业术语

**知识点**：向量空间的定义  
**摘要**：向量空间是定义了加法和数乘运算的集合，满足8条公理。它是线性代数的基础概念。

**用户操作**：
1. 选中"满足8条公理"
2. 点击"追问选中内容"

**AI 回答**：
详细解释这 8 条公理分别是什么，为什么需要满足这些公理。

### 场景 2：想深入理解某个例子

**知识点**：基向量的例子  
**摘要**：R³ 的标准基是 {(1,0,0), (0,1,0), (0,0,1)}。任何向量都可以用基的线性组合表示。

**用户操作**：
1. 选中"任何向量都可以用基的线性组合表示"
2. 点击"追问选中内容"

**AI 回答**：
具体解释什么是线性组合，如何用这三个基向量表示任意向量。

### 场景 3：来源片段中的关键信息

**来源片段**：`"向量空间 V 是一个集合..."`

**用户操作**：
1. 选中来源片段中的某段话
2. 点击"追问选中内容"

**AI 回答**：
针对原文中的这段话进行详细解释。

---

## 🧪 功能测试清单

### 基本功能测试

- [ ] 选中详情摘要中的文字 → "已选中"框出现
- [ ] 选中来源片段中的文字 → "已选中"框出现
- [ ] 选中超过 300 字符 → 自动截断并添加 `...`
- [ ] "已选中"框显示选中的文本（最多 2-3 行）
- [ ] 点击"清除"按钮 → 选中文本消失
- [ ] 切换到其他卡片 → 选中文本自动清空
- [ ] "追问选中内容"按钮：无选中时 disabled
- [ ] "追问选中内容"按钮：有选中时可点击（绿色）

### 追问功能测试

- [ ] 点击"追问选中内容" → 生成子卡片
- [ ] 子卡片标题：`选中内容解释：{原标题}`
- [ ] 子卡片内容包含针对选中文本的解释
- [ ] 追问后选中文本自动清空
- [ ] 子卡片回写到画布（虚线边框）
- [ ] 父卡片追问次数 +1
- [ ] 追问 2 次后父卡片标记为易忘点

### Fallback 测试

**Demo 卡片**：
- [ ] 加载演示画布 → 选中文字 → 追问
- [ ] 生成 fallback 子卡片
- [ ] 子卡片内容提到"演示解释"
- [ ] 子卡片标题正确：`选中内容解释：xxx`
- [ ] 不伪装成真实 AI

**RAG 失败**：
- [ ] 真实文档但无 API Key → 选中文字 → 追问
- [ ] 生成 fallback 子卡片
- [ ] 显示警告消息

### 多语言测试

- [ ] 中文环境：按钮显示"追问选中内容"
- [ ] 英文环境：按钮显示"Ask Selection"
- [ ] 中文环境："已选中"和"清除"正确显示
- [ ] 英文环境："Selected"和"Clear"正确显示
- [ ] 子卡片标题根据语言正确生成

### 边界情况测试

- [ ] 选中空白 → 不保存
- [ ] 选中后再次点击其他地方 → 保留之前的选中
- [ ] 选中后手动清除浏览器选区 → "已选中"框仍显示
- [ ] 快速多次选中 → 最后一次生效
- [ ] 选中时 asking=true → 按钮 disabled

---

## 🔧 验证命令（需要手动运行）

```bash
cd frontend

# TypeScript 类型检查
npm run type-check
# 预期：✅ 通过

# ESLint 检查
npm run lint
# 预期：✅ 通过

# 构建测试
npm run build
# 预期：✅ 成功生成 dist/
```

**注意**：当前环境无 npm，需要在本地终端执行。

---

## 💡 设计亮点

### 1. 最小化实现

- ✅ 只支持文字选择（不做图片局部追问）
- ✅ 不引入新的 UI 库
- ✅ 复用现有追问逻辑
- ✅ 不新增后端接口

### 2. 用户体验优先

- ✅ 选中即显示，所见即所得
- ✅ 明确的"已选中"视觉反馈
- ✅ 一键清除
- ✅ 按钮 disabled 状态清晰

### 3. 智能 Prompt 设计

- ✅ 包含选中文本
- ✅ 包含来源知识点
- ✅ 明确要求"只围绕选中内容"
- ✅ 要求引用课件依据

### 4. 完整的 Fallback

- ✅ Demo 卡片有 fallback
- ✅ RAG 失败有 fallback
- ✅ 明确标注演示模式
- ✅ 不伪装成真实 AI

---

## 🎯 核心价值

### 对用户的价值

1. **精准追问**：不再需要手动输入"请解释XXX"，直接选中即可
2. **降低门槛**：不需要思考如何提问，系统自动构造问题
3. **局部深入**：针对不理解的具体内容追问，而不是整个知识点
4. **自然交互**：选中文字是用户的自然行为，符合直觉

### 对产品的价值

1. **核心闭环补齐**：完成"局部追问"这一核心能力
2. **差异化**：不是简单的整体追问，而是精确到段落级别
3. **可扩展**：未来可以支持图片局部追问、公式追问等
4. **数据价值**：可以分析用户最关注哪些内容

---

## 📝 后续优化建议

### 短期（如果时间允许）

1. **选中高亮**
   - 选中后保持高亮显示
   - 用黄色背景标记选中文本

2. **选中历史**
   - 记录最近 3 次选中的文本
   - 可以快速切换

### 中期（1-2 周）

1. **多段选择**
   - 支持选中多个不连续的段落
   - 综合追问

2. **选中注释**
   - 选中后添加个人注释
   - 注释保存到 localStorage

### 长期（1-3 个月）

1. **图片局部追问**
   - 支持框选图片区域
   - AI 识别并解释

2. **公式追问**
   - 自动识别数学公式
   - 提供专门的公式解释

---

## 🎉 总结

### 核心改进

**从"整体追问"到"精确到段落级别的局部追问"**

### 关键实现

1. ✅ 文本选择监听（mouseup 事件）
2. ✅ 选中文本显示（已选中框）
3. ✅ 智能 Prompt 构造（包含选中文本和上下文）
4. ✅ 子卡片标题区分（选中内容解释 vs 追问解释）
5. ✅ 完整的 Fallback 机制

### 用户体验提升

- 操作步骤减少：输入问题 → 直接选中
- 问题质量提升：系统自动构造精确的问题
- 交互更自然：选中文字是用户的直觉行为
- 反馈更清晰："已选中"框明确显示选中内容

**结果**：学习画布核心闭环补齐，支持精确到段落级别的局部追问！

---

生成时间: 2024
文件: TEXT_SELECTION_FOLLOWUP_REPORT.md
状态: ✅ 已完成
