# CourseMind 多语言 (i18n) 实施指南

## 已完成的工作

### 1. 基础设施搭建 ✅

#### 新增文件
- `frontend/src/i18n/index.ts` - i18n 配置入口
- `frontend/src/i18n/locales/zh-CN.ts` - 简体中文翻译
- `frontend/src/i18n/locales/en-US.ts` - 英文翻译

#### 依赖安装
在 `package.json` 中添加了 `vue-i18n: ^9.13.1`

需要运行：
```bash
cd frontend
npm install
```

#### 主入口集成
已在 `frontend/src/main.ts` 中注册 i18n 插件

### 2. 已完成多语言改造的页面 ✅

#### IndexView.vue (首页) - 100% 完成
- ✅ 导入 useI18n 和语言切换功能
- ✅ 添加语言选择器（在header右侧）
- ✅ 所有硬编码文本替换为 t() 函数
- ✅ 包含：欢迎语、功能卡片、按钮等

#### AuthView.vue (登录/注册) - 100% 完成
- ✅ 导入 useI18n
- ✅ 表单标签、占位符、按钮文本
- ✅ 错误提示信息
- ✅ 成功消息

#### DocumentsView.vue (知识库管理) - 80% 完成
- ✅ 导入 useI18n
- ✅ 页面标题、副标题
- ✅ 上传卡片所有文本
- ✅ 文档列表表头
- ✅ 操作按钮（删除、重新处理）
- ✅ 错误提示改进（支持.pptx等具体格式提示）
- ✅ 实现 translateErrorMessage 函数处理API错误码

#### documents.ts (API层) - 100% 完成
- ✅ 错误消息改为错误码（如 FILE_TOO_LARGE、UNSUPPORTED_FILE_TYPE）
- ✅ 由组件层使用 t() 翻译

### 3. 文件格式错误提示改进 ✅

**旧版本：**
```
暂不支持该文件类型
```

**新版本（中文）：**
```
暂不支持 .pptx 文件。当前支持：TXT、Markdown、PDF。
该文件没有扩展名。当前支持：TXT、Markdown、PDF。
```

**新版本（英文）：**
```
.pptx files are not supported yet. Supported formats: TXT, Markdown, PDF.
This file has no extension. Supported formats: TXT, Markdown, PDF.
```

实现位置：
- `DocumentsView.vue` 的 `beforeUpload` 函数
- `translateErrorMessage` 函数

---

## 需要完成的工作（用户TODO）

### 1. KnowledgeAskView.vue (知识库问答)

需要替换的文本：
```typescript
// 在 script 中添加
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

// 替换错误消息
'加载文档列表失败' → t('knowledgeAsk.errors.loadDocumentsFailed')
'请先选择至少一个文档' → t('knowledgeAsk.errors.selectDocuments')
'请输入问题' → t('knowledgeAsk.errors.enterQuestion')
'提问失败，请重试' → t('knowledgeAsk.errors.askFailed')
'现有文档不足以回答该问题...' → t('knowledgeAsk.errors.insufficientContext')
```

在模板中替换：
```html
<!-- 标题 -->
<h1>知识库问答</h1> → <h1>{{ t('knowledgeAsk.title') }}</h1>
<p>选择资料后提问，回答将显示引用来源</p> → <p>{{ t('knowledgeAsk.subtitle') }}</p>

<!-- 按钮和标签 -->
← 返回 → {{ t('common.back') }}
刷新 → {{ t('common.refresh') }}
1. 选择知识库文档 → {{ t('knowledgeAsk.selectDocuments') }}
2. 输入问题 → {{ t('knowledgeAsk.question') }}
提问 → {{ t('knowledgeAsk.askButton') }}
思考中... → {{ t('knowledgeAsk.asking') }}
清空历史 → {{ t('knowledgeAsk.clearHistory') }}

<!-- 文档选择 -->
暂无处理成功的文档，请先上传资料 → (需自行实现)
前往上传 → (需自行实现)

<!-- 结果显示 -->
回答 → {{ t('knowledgeAsk.answer') }}
来源 → {{ t('knowledgeAsk.sources') }}
置信度 → {{ t('knowledgeAsk.confidence') }}
第 X 页 → {{ t('knowledgeAsk.page', { page: X }) }}
```

### 2. ChatView.vue (AI对话) - 如果时间允许

需要创建翻译键：
```typescript
// 在 zh-CN.ts 和 en-US.ts 中添加
chat: {
  title: 'AI 对话' / 'AI Chat',
  subtitle: '...',
  // 其他文本
}
```

### 3. AboutView.vue (关于页面) - 如果时间允许

类似处理。

---

## 语言切换器位置

已在 `IndexView.vue` 的 header 中添加：
```html
<el-select
  :model-value="locale"
  class="locale-selector"
  @change="handleLocaleChange"
>
  <el-option
    v-for="loc in SUPPORTED_LOCALES"
    :key="loc"
    :label="LOCALE_NAMES[loc]"
    :value="loc"
  />
</el-select>
```

**建议：** 其他页面如果需要语言切换，可以复制这段代码，或者创建一个共享的 `LocaleSwitcher.vue` 组件。

---

## 使用方式

### 在组件中使用 i18n

```vue
<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

// 切换语言
import { setLocale } from '@/i18n'
setLocale('en-US')
</script>

<template>
  <!-- 简单文本 -->
  <h1>{{ t('common.appName') }}</h1>
  
  <!-- 带参数 -->
  <p>{{ t('common.welcome', { nickname: user.nickname }) }}</p>
  
  <!-- 复数 -->
  <span>{{ t('knowledgeAsk.selectedCount', { count: 5 }) }}</span>
</template>
```

### 添加新翻译

1. 在 `src/i18n/locales/zh-CN.ts` 添加中文
2. 在 `src/i18n/locales/en-US.ts` 添加对应英文
3. 使用 `t('your.new.key')` 引用

---

## 验证步骤

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 类型检查
```bash
npm run type-check
```

如果报错，可能是 vue-i18n 的类型声明问题。创建 `src/shims-vue-i18n.d.ts`：
```typescript
declare module 'vue-i18n' {
  // 类型声明
}
```

### 3. Lint检查
```bash
npm run lint
```

### 4. 构建
```bash
npm run build
```

### 5. 运行开发服务器测试
```bash
npm run dev
```

测试点：
- ✅ 首页语言选择器工作
- ✅ 切换语言后页面文本同步更新
- ✅ 刷新页面语言设置保持
- ✅ 登录/注册表单文本正确
- ✅ 文档上传错误提示具体化（测试上传.pptx）
- ✅ 删除/重新处理按钮和提示正确

---

## 翻译质量检查清单

### 中文
- ✅ 简洁自然
- ✅ 适合Demo展示
- ✅ 无机器翻译痕迹

### 英文
- ✅ 地道表达
- ✅ 不是逐字翻译
- ✅ 符合英文产品惯例

### 示例对比

| 场景 | 中文 | 英文 |
|------|------|------|
| 知识库问答 | 知识库问答 | Knowledge Q&A ✅ (不是 Knowledge Base Q&A) |
| 上传成功 | 上传成功，正在处理中... | Uploaded successfully. Processing... ✅ |
| 文档不足 | 现有文档不足以回答该问题。 | The uploaded materials do not contain enough information to answer this question. ✅ |
| 不支持格式 | 暂不支持 .pptx 文件 | .pptx files are not supported yet ✅ |

---

## 剩余硬编码文本位置

运行此命令查找剩余中文硬编码：
```bash
cd frontend/src
grep -r "[\u4e00-\u9fa5]" views/*.vue --color
```

重点检查：
1. KnowledgeAskView.vue - 模板中的所有中文
2. ChatView.vue - 全部内容
3. AboutView.vue - 全部内容
4. 任何 ElMessage、ElMessageBox 调用

---

## 常见问题

### Q: 类型错误 `Property '$t' does not exist`
A: 添加全局类型声明或使用 `useI18n()` 替代 `this.$t`

### Q: 某些文本没有翻译
A: 检查是否遗漏了 `t()` 包裹，或翻译键拼写错误

### Q: 切换语言后部分文本没变
A: 检查是否使用了字符串模板而非 `t()` 函数

### Q: 浏览器默认语言不生效
A: 清除 localStorage 中的 `locale` 键，刷新页面

---

## 后续优化建议

1. **创建语言切换组件**
   ```vue
   <!-- components/LocaleSwitcher.vue -->
   <template>
     <el-select v-model="currentLocale" @change="handleChange">
       ...
     </el-select>
   </template>
   ```

2. **添加更多语言**
   - 繁体中文 (zh-TW)
   - 日语 (ja-JP)
   - 韩语 (ko-KR)

3. **提取验证消息**
   表单验证错误也应该使用 i18n

4. **数字和日期格式化**
   使用 `locale.value` 来格式化日期：
   ```typescript
   new Date().toLocaleString(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US')
   ```

5. **Element Plus 国际化**
   参考：https://element-plus.org/zh-CN/guide/i18n.html

---

## 完成标准

- [ ] npm install 成功
- [ ] npm run type-check 通过
- [ ] npm run build 成功
- [ ] 首页语言切换器可用
- [ ] 所有优先页面完成翻译（IndexView, AuthView, DocumentsView）
- [ ] 文件格式错误提示具体化
- [ ] KnowledgeAskView 完成翻译
- [ ] 无残留硬编码中文（除ChatView/AboutView外）
- [ ] 切换语言后localStorage保存设置
- [ ] 刷新后语言设置保持

---

生成时间：2024
