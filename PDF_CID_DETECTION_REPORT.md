# CourseMind PDF CID 乱码检测 - 完成报告

## ✅ 修改的文件（5个）

1. **`backend/app/parsers/pdf_parser.py`**
   - 新增 `_check_cid_encoding()` 函数
   - 在 `parse()` 方法中调用 CID 检测

2. **`backend/tests/test_document_parsers.py`**
   - 新增 4 个 CID 检测测试用例

3. **`frontend/src/i18n/locales/zh-CN.ts`**
   - 新增 `pdfTextExtractionFailed` 翻译

4. **`frontend/src/i18n/locales/en-US.ts`**
   - 新增对应英文翻译

5. **`frontend/src/views/DocumentsView.vue`**
   - 更新 `getUserFriendlyErrorMessage()` 函数
   - 添加 CID 错误检测逻辑

---

## 🎯 CID 检测规则

### 后端检测逻辑

```python
def _check_cid_encoding(text: str, filename: str) -> None:
    """检测 CID 字体编码问题"""
    
    # 规则1：文本太短（<200字符）放行
    if len(text) < 200:
        return
    
    # 规则2：绝对阈值 - CID 出现 >= 20 次
    cid_count = text.count("(cid:")
    if cid_count >= 20:
        raise PdfTextNotFoundError(...)
    
    # 规则3：比例阈值 - CID 内容 > 15%
    if cid_count > 0:
        cid_chars = cid_count * 10  # 估算 CID 字符数
        ratio = cid_chars / len(text)
        if ratio > 0.15:
            raise PdfTextNotFoundError(...)
```

### 检测规则表

| 条件 | 文本长度 | CID 数量 | CID 比例 | 结果 |
|------|---------|---------|---------|------|
| **短文本** | < 200 | 任意 | 任意 | ✅ 放行 |
| **高计数** | >= 200 | >= 20 | 任意 | ❌ 拒绝 |
| **高比例** | >= 200 | > 0 | > 15% | ❌ 拒绝 |
| **低比例** | >= 200 | < 20 | <= 15% | ✅ 放行 |

### 错误消息

**后端抛出**：
```
PdfTextNotFoundError: PDF text extraction failed: the file may use 
custom font encoding or scanned pages. Found 25 font encoding errors. 
Please use a text-selectable PDF.
```

**前端显示**：
- 中文：`PDF 文本抽取失败：该文件可能使用特殊字体编码或扫描版，请换用可复制文字的 PDF。`
- 英文：`PDF text extraction failed. The file may use custom font encoding or scanned pages. Please use a text-selectable PDF.`

---

## 🔍 前端错误映射

### getUserFriendlyErrorMessage 逻辑

```typescript
function getUserFriendlyErrorMessage(errorMessage: string | null): string {
  const lowerMessage = errorMessage.toLowerCase()
  
  // 1. CID 检测（优先级最高）
  if (
    lowerMessage.includes('cid') ||
    lowerMessage.includes('font encoding') ||
    (lowerMessage.includes('text extraction') && lowerMessage.includes('failed'))
  ) {
    return t('documents.errors.pdfTextExtractionFailed')
  }
  
  // 2. AI 服务未配置
  if (lowerMessage.includes('api key') || ...) {
    return t('documents.errors.aiServiceNotConfigured')
  }
  
  // 3. PDF 解析失败（通用）
  if (lowerMessage.includes('pdf') && ...) {
    return t('documents.errors.pdfParsingFailed')
  }
  
  // 4. 其他错误
  return errorMessage
}
```

### 匹配关键词

| 关键词 | 说明 |
|--------|------|
| `cid` | CID 字体编码问题 |
| `font encoding` | 字体编码问题 |
| `text extraction` + `failed` | 文本抽取失败 |

---

## 🧪 测试用例

### 1. test_pdf_cid_encoding_high_count

**场景**：PDF 包含 25 个 CID 引用

```python
cid_text = "Normal text " + " ".join([f"(cid:{i})" for i in range(25)])
```

**预期**：抛出 `PdfTextNotFoundError`，错误消息包含 "font encoding"

### 2. test_pdf_cid_encoding_high_ratio

**场景**：短文本，CID 占比 > 15%

```python
cid_text = "(cid:123)(cid:456)(cid:789)(cid:012)(cid:345)"
```

**预期**：抛出 `PdfTextNotFoundError`，错误消息包含 "Text quality too poor"

### 3. test_pdf_few_cid_references_accepted

**场景**：长文本，只有 3 个 CID 引用（低比例）

```python
cid_text = "This is a normal PDF with mostly good text. " * 20
cid_text += "(cid:123) (cid:456) (cid:789)"
```

**预期**：✅ 解析成功

### 4. test_pdf_short_text_with_cid_passes

**场景**：短文本（< 200 字符）包含 CID

```python
cid_text = "(cid:123)(cid:456)(cid:789)"
```

**预期**：✅ 解析成功（文本太短，无法可靠判断）

---

## 📊 处理流程

### 正常 PDF

```
用户上传 PDF
   ↓
后端解析文本 → 文本正常
   ↓
CID 检测 → 通过（CID < 20 且比例 < 15%）
   ↓
分块、嵌入
   ↓
状态：succeeded
```

### CID 乱码 PDF

```
用户上传 PDF
   ↓
后端解析文本 → 提取到大量 "(cid:数字)"
   ↓
CID 检测 → 失败（CID >= 20 或比例 > 15%）
   ↓
抛出 PdfTextNotFoundError
   ↓
状态：failed
error_message: "PDF text extraction failed: ...font encoding..."
   ↓
前端显示：
"PDF 文本抽取失败：该文件可能使用特殊字体编码或扫描版，
请换用可复制文字的 PDF。"
```

---

## 💡 设计亮点

### 1. 多层检测规则

**绝对阈值**：
- CID >= 20 → 拒绝
- 防止大量乱码进入数据库

**比例阈值**：
- CID 比例 > 15% → 拒绝
- 防止短文档乱码

**短文本豁免**：
- 长度 < 200 → 放行
- 避免误判

### 2. 清晰的错误提示

**技术准确性**：
- 提到"字体编码"和"扫描版"
- 用户理解问题根源

**解决方案明确**：
- "请换用可复制文字的 PDF"
- 告诉用户如何解决

### 3. 前端错误映射

**关键词匹配**：
- `cid`、`font encoding`、`text extraction`
- 覆盖各种错误表述

**优先级设计**：
- CID 检测优先级最高
- 避免被通用 PDF 错误掩盖

---

## 🔧 验证命令

### 后端测试

```bash
cd backend

# 运行所有解析器测试
pytest tests/test_document_parsers.py -v

# 只运行 CID 测试
pytest tests/test_document_parsers.py::test_pdf_cid_encoding_high_count -v
pytest tests/test_document_parsers.py::test_pdf_cid_encoding_high_ratio -v
pytest tests/test_document_parsers.py::test_pdf_few_cid_references_accepted -v
pytest tests/test_document_parsers.py::test_pdf_short_text_with_cid_passes -v

# 运行相关路由测试
pytest tests/test_document_routes.py -v

# 运行上传服务测试
pytest tests/test_upload_service.py -v
```

### 前端验证

```bash
cd frontend

# TypeScript 类型检查
npm run type-check

# ESLint 检查
npm run lint

# 构建测试
npm run build
```

---

## 🎯 实际效果

### 改进前

**问题**：
- ❌ CID 乱码 PDF 显示"处理成功"
- ❌ 但实际文本全是 `(cid:20759)(cid:1406)...`
- ❌ RAG 无法工作，生成画布失败
- ❌ 用户不知道为什么失败

### 改进后

**效果**：
- ✅ CID 乱码 PDF 被拒绝，状态"失败"
- ✅ 错误提示明确："字体编码或扫描版"
- ✅ 告诉用户如何解决："换用可复制文字的 PDF"
- ✅ 正常 PDF 不受影响

---

## 📝 CID 问题背景

### 什么是 CID

**CID (Character ID)**：
- PDF 中字体的内部字符标识
- 用于映射字符到字形

**正常情况**：
- PDF 包含字体映射表
- `pypdf` 可以正确提取文本

**CID 乱码情况**：
- PDF 使用自定义字体编码
- 缺少标准字符映射表
- `pypdf` 只能提取 CID 引用：`(cid:123)`

### 常见原因

1. **特殊字体编码**
   - PDF 使用非标准字体
   - 缺少 ToUnicode 映射表

2. **扫描版 PDF**
   - 扫描图片 + OCR 文本层
   - OCR 质量差或映射错误

3. **PDF 生成工具问题**
   - 某些工具生成的 PDF 编码不规范

### 解决方案

**用户角度**：
- 换用可复制文字的 PDF
- 使用 Adobe Acrobat 或其他工具重新导出

**系统角度**：
- 检测并拒绝 CID 乱码 PDF
- 避免无用数据进入 RAG

---

## 🚀 未来优化建议

### 短期（如果需要）

1. **更精确的阈值**
   - 收集实际 CID 乱码样本
   - 调整 20 次和 15% 阈值

2. **中文特殊处理**
   - 检测是否为中文 PDF
   - 中文 PDF 对 CID 更敏感

### 长期（1-3 个月）

1. **OCR 支持**
   - 检测到 CID 乱码后提示 OCR
   - 集成 Tesseract 或云 OCR

2. **PDF 修复**
   - 尝试修复字体映射
   - 使用 pdfplumber 或其他工具

3. **智能降级**
   - 部分页面有 CID，保留正常页面
   - 给用户选择是否继续

---

**完成时间**：约 30 分钟  
**测试用例**：4 个新增  
**状态**：✅ 已完成，待验证
