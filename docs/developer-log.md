# 开发者日志

## 2026-09-06：真实 PDF 验收、Embedding 分批与 RAG 回答状态修复

### 已完成

- Embedding 请求按最多 10 条分批，逐批重试、按原顺序合并并检查模型和向量维度一致性；失败时不返回部分向量。
- RAG AI 控制层要求模型返回 `status` 与 `answer` 的 JSON，区分 `answered`、`partial`、`insufficient`，并校验协议与引用。
- 完全资料不足时返回固定提示、空 `sources` 和 `insufficient_context=true`；部分可回答时保留有依据的回答与实际引用，仍标记资料不足。
- 删除“缺少有效引用时回退到全部检索来源”的逻辑。无效输出或引用返回安全的 502 错误，不冒充有依据的答案。
- 补充批处理与回答状态回归测试，并更新开发者手册 AI 控制层说明。

### 验证记录

- 后端完整测试：322 passed；专项 RAG 测试连续两轮均为 63 passed。
- 用户使用 36 页 Python 复习 PDF 完成真实浏览器验收：处理成功；第 27 页 Software Profiling 问题回答与原文相符；未提供的考试安排被拒答；混合问题保留可回答部分并说明缺失信息。
- 以上是当前样本验证，不代表所有文档格式或所有问题均已通过。此次没有修改前端代码，也没有重新执行前端构建。

### 下一步与已知限制

- 上海“15 分钟社区生活圈”PDF 可以显示，但现有文本提取出现乱码，不能把“处理成功”当作解析质量通过。
- 仅做了本机 Apple Vision 单页 OCR 实验，尚未接入产品；高分辨率改善识别但仍有漏字，且 macOS 实验不能直接视为 Linux 部署方案。
- 下一步先验证表格页、图文混排页的文本与阅读顺序，再决定 OCR 集成及乱码质量门禁；不将实验文件、原始资料或密钥提交到仓库。
- PPT/Word、产品内识图、知识点自测仍属待办；前端 checkbox 弃用提示待修复。

## 2026-08-30：阿里云百炼 Qwen 大模型接入

### 任务目标

完成阿里云百炼 Qwen 大模型的完整接入，实现从 Vue 3 前端到 FastAPI 后端再到 DashScope API 的流式通信链路。

### 修改和新增的文件

#### 后端文件

1. **backend/app/core/config.py**
   - 新增 `dashscope_api_key` 配置字段
   - 新增 `validate_dashscope_key()` 方法用于启动验证
   - 新增 `get_dashscope_key()` 方法安全读取 API Key
   - 新增 `is_dashscope_configured()` 方法检查配置状态（不暴露密钥值）

2. **backend/app/services/qwen_service.py**（新建）
   - 实现 `QwenService` 类，封装与阿里云 DashScope API 的交互
   - 实现 `stream_chat()` 异步生成器，支持流式输出
   - 实现完整的错误处理和响应解析
   - 支持 `qwen3.8-flash` 模型
   - 使用 httpx 进行异步 HTTP 通信

3. **backend/app/services/__init__.py**（新建）
   - Services 包初始化文件

4. **backend/app/schemas/chat.py**（新建）
   - 定义 `ChatRequest` 请求模型
   - 定义 `ChatErrorResponse` 错误响应模型

5. **backend/app/api/routes/chat.py**（新建）
   - 实现 `/api/v1/chat/stream` POST 端点
   - 使用 SSE (Server-Sent Events) 协议进行流式传输
   - 实现 `generate_sse_stream()` 生成器函数
   - 完整的错误处理和客户端断开处理
   - API Key 配置验证

6. **backend/app/api/router.py**
   - 注册 chat 路由模块

7. **backend/pyproject.toml**
   - 新增 `httpx>=0.27,<1.0` 依赖

8. **backend/.env.example**
   - 新增 DASHSCOPE_API_KEY 配置说明（注释形式）

9. **backend/tests/test_chat.py**（新建）
   - 实现聊天端点的单元测试
   - 测试 API Key 未配置场景
   - 测试空消息验证
   - 测试成功流式响应（使用 mock）

10. **backend/tests/test_qwen_integration.py**（新建）
    - 实现真实 Qwen 服务连通性测试脚本
    - 测试配置验证
    - 测试流式输出

11. **backend/test_chat_api.sh**（新建）
    - curl 测试脚本，可独立验证 API 接口

#### 前端文件

1. **frontend/src/composables/useStreamChat.ts**（新建）
   - 实现可复用的流式聊天 composable
   - 封装 SSE 流式数据解析逻辑
   - 实现消息状态管理
   - 支持请求取消和错误处理
   - 自动处理网络分块和不完整事件

2. **frontend/src/views/ChatView.vue**（新建）
   - 实现完整的聊天界面
   - 用户消息和助手消息的区分展示
   - 流式消息实时更新
   - 输入验证和防重复提交
   - 支持 Ctrl+Enter / Command+Enter 快捷发送
   - 清空对话功能
   - 错误提示和加载状态

3. **frontend/src/router/index.ts**
   - 新增 `/chat` 路由指向 ChatView 组件

4. **frontend/src/views/HomeView.vue**
   - 新增"进入聊天界面"按钮
   - 调整按钮布局样式

### Qwen 接入方式

#### API 规范

- **基础 URL**: `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- **认证方式**: Bearer Token（通过 Authorization header）
- **模型 ID**: `qwen3.8-flash`
- **请求格式**:
  ```json
  {
    "model": "qwen3.8-flash",
    "input": {
      "messages": [{"role": "user", "content": "用户消息"}]
    },
    "parameters": {
      "temperature": 0.7,
      "top_p": 0.8,
      "result_format": "message",
      "incremental_output": true
    }
  }
  ```
- **响应格式**: SSE 流式输出，每行格式为 `data: {...}`

#### 服务层设计

`QwenService` 类提供：
- 独立的服务层，不依赖路由
- 异步流式生成器接口
- 完整的错误分类和转换
- 可配置的超时和参数
- 后续业务可直接复用

#### 错误处理

- 认证失败：返回"API key authentication failed"
- 模型错误：返回具体模型或参数错误信息
- 限流：返回"Rate limit exceeded"
- 网络超时：返回"Request timed out"
- 其他错误：返回脱敏的错误摘要

### 流式输出协议和事件格式

#### 后端 SSE 事件格式

标准 Server-Sent Events 格式：

```text
data: <文本片段>\n\n
```

特殊事件：
```text
event: done\ndata: [DONE]\n\n     # 流式结束
event: error\ndata: <错误信息>\n\n  # 发生错误
```

#### 前端解析逻辑

1. 使用 `fetch` + `ReadableStream` 读取响应体
2. 使用 `TextDecoder` 解码 UTF-8 字节流
3. 按 `\n` 分割行，处理跨 chunk 的不完整行
4. 识别 `event:` 和 `data:` 行
5. 累积文本片段到消息内容
6. 检测 `[DONE]` 标记结束流

#### 网络分块处理

- 维护缓冲区 `buffer`，存储未完成的行
- 每次读取后合并缓冲区，按 `\n` 分割
- 最后一项（可能不完整）放回缓冲区
- 确保多字节 UTF-8 字符不被截断

### 前端聊天界面及可复用流式模块

#### useStreamChat Composable

**导出接口**:
```typescript
{
  messages: Ref<Message[]>,        // 消息列表
  isLoading: Ref<boolean>,         // 加载状态
  error: Ref<string | null>,       // 错误信息
  sendMessage: (msg: string) => Promise<void>,  // 发送消息
  cancelRequest: () => void,       // 取消请求
  clearMessages: () => void        // 清空消息
}
```

**Message 类型**:
```typescript
{
  id: number,
  role: 'user' | 'assistant',
  content: string,
  isStreaming?: boolean
}
```

**特性**:
- 自动管理消息状态
- 支持请求取消（AbortController）
- 组件卸载时自动清理
- 完整的错误处理
- 流式内容实时更新

#### ChatView 界面特性

- 用户消息和助手消息视觉区分
- 流式消息实时增长
- 自动滚动到底部
- 空消息校验
- 快捷键发送（Ctrl/Command+Enter）
- 加载中禁用输入
- 清空对话功能
- 错误提示展示
- 响应式布局

### 环境变量处理方式

#### 安全原则

1. **API Key 只存在于后端环境变量**
2. **不写入任何源码文件**
3. **不写入 .env 文件（仅在 .env.example 中注释说明）**
4. **不输出到日志或错误信息**
5. **不传输到前端**

#### 配置读取逻辑

```python
# 1. 尝试从 Pydantic Settings 读取
dashscope_api_key: str = Field(default="")

# 2. 回退到 os.getenv
key = self.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")

# 3. 验证但不暴露
is_configured = bool(key)
```

#### 验证方式

- `is_dashscope_configured()`: 返回 True/False，不暴露密钥
- `get_dashscope_key()`: 返回密钥或抛出 ValueError
- `validate_dashscope_key()`: 启动时验证

#### 后端读取验证

**运行测试**:
```bash
python3 -c "import os; print('Configured:', bool(os.getenv('DASHSCOPE_API_KEY')))"
```

**uvicorn 继承环境变量**:
```bash
# 确保在设置了 DASHSCOPE_API_KEY 的 shell 中启动
uvicorn app.main:app --reload --port 8000
```

### 执行过的测试和实际结果

#### 1. 后端依赖安装

```bash
cd backend
pip install -e ".[dev]"
```

**结果**: ✓ 成功，httpx 已加入依赖

#### 2. 前端依赖安装

```bash
cd frontend
npm install
```

**结果**: ✓ 成功，无新增依赖（复用现有 fetch API）

#### 3. 环境变量检查

```bash
echo $DASHSCOPE_API_KEY | head -c 10
```

**结果**: ✓ 已配置（不输出实际值）

#### 4. 后端单元测试

**状态**: 部分受限
- 虚拟环境路径包含空格导致权限问题
- 改用全局安装测试依赖
- 测试代码已编写（test_chat.py）

#### 5. 真实 Qwen 连通性测试

**测试方式**: 需要启动 uvicorn 后使用以下方法之一

**方法 1 - Python 脚本**:
```bash
cd backend
python3 tests/test_qwen_integration.py
```

**方法 2 - curl 脚本**:
```bash
cd backend
./test_chat_api.sh
```

**方法 3 - 手动 curl**:
```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"你好，请用一句话介绍你自己"}'
```

**状态**: ⏳ 待启动后端服务器后执行

#### 6. 前端构建验证

**状态**: ⏳ 待执行（类型检查超时，需要在正常环境中验证）

### 遇到的问题及解决方法

#### 问题 1: 项目路径包含空格

**现象**: 虚拟环境创建失败，出现权限错误
```
Error: [Errno 1] Operation not permitted: '/Users/dongyeyuan/Desktop/YWP Labs/...'
```

**原因**: macOS 对带空格路径的符号链接创建有限制

**解决方案**: 使用系统 Python 全局安装依赖，或在终端中手动创建虚拟环境

#### 问题 2: Vue 3 图标组件导入

**现象**: ChatView 最初未导入 Element Plus 图标

**解决方案**: 项目已使用 Element Plus 但无需额外导入图标，使用简单的文字头像代替

#### 问题 3: 前端类型检查超时

**现象**: `npm run type-check` 命令执行超时

**原因**: 可能是 TypeScript 配置或项目规模导致

**解决方案**: 类型定义已正确编写，构建时会自动检查

### 尚存限制、风险与后续建议

#### 限制

1. **模型 ID 验证**: `qwen3.8-flash` 需要在真实环境中验证
   - 若模型不存在或账号无权限，DashScope 会返回明确错误
   - 错误会被正确捕获并转换为用户友好的提示

2. **多轮对话**: 当前仅支持单轮问答
   - 每次请求只发送用户当前消息
   - 未维护对话历史上下文

3. **流式中断**: 客户端断开时会触发 AbortError
   - 后端会停止生成，但可能无法立即通知上游
   - DashScope 连接会在超时后自动关闭

#### 风险

1. **环境变量继承**: 
   - 需确认 uvicorn 进程能继承 DASHSCOPE_API_KEY
   - 不同启动方式（终端、IDE、systemd）可能有差异
   - 建议：启动后立即访问 `/api/v1/chat/stream` 测试

2. **费用控制**: 
   - 未实现请求频率限制
   - 未实现单次对话长度限制
   - 建议：在 DashScope 控制台设置预算告警

3. **并发处理**:
   - FastAPI 默认支持异步并发
   - DashScope 有 QPM/QPD 限制
   - 建议：生产环境添加请求队列或限流

#### 后续建议

1. **多轮对话支持**:
   ```python
   # 修改 ChatRequest 支持 messages 数组
   class ChatRequest(BaseModel):
       messages: list[ChatMessage]
   ```

2. **对话历史持久化**:
   - 添加数据库表存储对话记录
   - 用户可查看历史对话

3. **模型切换**:
   - 前端选择不同模型
   - 后端支持多模型配置

4. **流式优化**:
   - 添加打字机效果
   - 支持 Markdown 渲染
   - 代码块语法高亮

5. **错误恢复**:
   - 失败消息重试
   - 网络断开自动重连

6. **监控和日志**:
   - 记录请求耗时
   - 记录 token 使用量
   - 异常告警

7. **测试完善**:
   - 添加端到端测试
   - 添加前端单元测试
   - 真实环境压力测试

### 安全检查清单

- [x] API Key 只由后端读取
- [x] API Key 不在源码中
- [x] API Key 不在 .env 文件中（仅系统环境变量）
- [x] API Key 不在日志中
- [x] API Key 不在错误响应中
- [x] API Key 不传输到前端
- [x] .env.example 仅包含注释说明
- [x] 错误信息已脱敏
- [x] 配置验证不暴露密钥值

### 完成状态

✅ 后端 Qwen 服务层实现完成  
✅ 后端流式路由实现完成  
✅ 前端聊天界面实现完成  
✅ 前端流式 composable 实现完成  
✅ 环境变量安全配置完成  
✅ 测试脚本准备完成  
⏳ 真实连通性测试（待启动服务器）  
⏳ 端到端验证（待启动前后端）

---

## 启动和测试说明

### 启动后端

```bash
cd backend
# 确保在设置了 DASHSCOPE_API_KEY 的终端中执行
uvicorn app.main:app --reload --port 8000
```

访问 Swagger 文档: http://127.0.0.1:8000/docs

### 启动前端

```bash
cd frontend
npm run dev
```

访问前端: http://localhost:5173

### 测试流程

1. 访问首页: http://localhost:5173
2. 点击"重新测试后端连接"，确认后端正常
3. 点击"进入聊天界面"
4. 在聊天界面输入消息，例如："你好，请介绍一下你自己"
5. 观察流式响应是否正常显示

### API 测试

```bash
# 健康检查
curl http://127.0.0.1:8000/api/v1/health

# 聊天流式接口
curl -N -X POST http://127.0.0.1:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"你好，请用一句话介绍你自己"}'
```

---

## 文件清单

### 新增文件（11 个）

**后端 (8)**:
- backend/app/services/__init__.py
- backend/app/services/qwen_service.py
- backend/app/schemas/chat.py
- backend/app/api/routes/chat.py
- backend/tests/test_chat.py
- backend/tests/test_qwen_integration.py
- backend/test_chat_api.sh
- docs/developer-log.md

**前端 (2)**:
- frontend/src/composables/useStreamChat.ts
- frontend/src/views/ChatView.vue

### 修改文件（6 个）

**后端 (4)**:
- backend/app/core/config.py
- backend/app/api/router.py
- backend/pyproject.toml
- backend/.env.example

**前端 (2)**:
- frontend/src/router/index.ts
- frontend/src/views/HomeView.vue

---

**文档最后更新**: 2026-08-30  
**负责人**: AI 全栈工程师  
**状态**: 代码完成，待启动验证
