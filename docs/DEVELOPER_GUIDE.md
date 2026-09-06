# CourseMind 开发者手册

本文档以当前仓库实现为准，说明本地开发、系统结构、主要数据流、接口、安全边界、测试与故障排查。

## 1. 当前能力

CourseMind 是 Vue 3 + FastAPI + PostgreSQL/pgvector 的知识库问答应用，现已具备：

- 用户注册、登录、刷新令牌和退出；
- 普通 Qwen 流式聊天与会话历史；
- TXT、Markdown、PDF 上传、校验、去重和后台处理；
- 文本解析、结构化切片、DashScope Embedding；
- pgvector 余弦相似度检索；
- 带来源引用和资料不足判断的 RAG 问答；
- 文档所有权隔离、删除和失败后重新处理；
- 文档管理与知识库问答前端页面。

## 2. 技术栈与目录

- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router。
- 后端：Python、FastAPI、SQLAlchemy 2、Pydantic、Alembic、httpx。
- 数据库：PostgreSQL 17、pgvector。
- AI：DashScope `text-embedding-v3`（1024 维）和 Qwen Chat。

```text
CourseMind/
├── backend/
│   ├── app/
│   │   ├── ai/             # Chat/Embedding 协议与 DashScope 适配器
│   │   ├── api/routes/     # auth、chat、documents、rag、health
│   │   ├── chunking/       # 递归字符切片
│   │   ├── core/           # 配置
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── parsers/        # TXT、Markdown、PDF 解析
│   │   ├── schemas/        # API DTO
│   │   └── services/       # 上传、摄取、检索、RAG
│   ├── alembic/            # 数据库迁移
│   ├── data/uploads/       # 运行时上传文件（Git 忽略）
│   ├── scripts/            # 独立验收脚本
│   └── tests/
├── frontend/src/
│   ├── api/
│   ├── router/
│   ├── stores/
│   └── views/
└── docker-compose.yml
```

## 3. 本地环境

### 3.1 前置条件

- Docker Desktop；
- Python 3.11 或更高版本；
- Node.js 18 或更高版本；
- npm。

### 3.2 配置

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

后端至少需要正确配置：

- `DATABASE_URL`：PostgreSQL 连接；
- `JWT_SECRET_KEY`：至少 32 字符；
- `DASHSCOPE_API_KEY`：真实 Embedding、Chat 和 RAG 所需；
- `CORS_ORIGINS`：前端来源；
- `EMBEDDING_TRUST_ENV`：是否读取系统代理；
- `RAG_MIN_SIMILARITY`：服务端不可降低的最低相似度，默认 `0.3`。

真实密钥只放在 `backend/.env` 或进程环境中，不提交到 Git。

### 3.3 启动 PostgreSQL

在仓库根目录执行：

```bash
docker compose up -d postgres
docker compose ps postgres
```

数据库数据存放在外部卷 `ban_coursemind_postgres_data`。不要随意删除该卷。

### 3.4 安装与迁移后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

启动后端：

```bash
set -a
source .env
set +a
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u NO_PROXY -u http_proxy -u https_proxy -u all_proxy -u no_proxy \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`http://127.0.0.1:8000/api/v1/health`；Swagger：`http://127.0.0.1:8000/docs`。

### 3.5 安装与启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

浏览器打开 `http://127.0.0.1:5173`。

## 4. 核心数据模型

### User

保存账号、密码哈希、启用状态和 `token_version`。退出登录会令既有 Access Token 失效。

### Document

保存文件元数据、SHA-256、处理状态和所有者。状态为：

```text
pending -> processing -> succeeded
                     \-> failed
```

同一用户内以 `(user_id, sha256)` 去重；不同用户可以上传相同内容。历史 `user_id IS NULL` 文档不会暴露给普通用户。

### ProcessingJob

记录每一次处理尝试。删除 Document 时由数据库外键级联删除。

### DocumentChunk

保存切片内容、页码、Markdown 标题路径、原文字符偏移、模型信息及 `vector(1024)`。字符区间采用 `[start_char, end_char)`。

## 5. 上传和摄取流程

```text
multipart 上传
  -> 扩展名/MIME/PDF 签名/大小检查
  -> backend/data/uploads/.staging 临时文件
  -> 流式计算 SHA-256
  -> 用户范围内去重
  -> 保存 Document
  -> 原子发布到 backend/data/uploads/{document_uuid}/{safe_name}
  -> 后台独立 Session
  -> 解析 -> 切片 -> Embedding -> 原子替换 chunks
```

文本和 Markdown 最大 10 MiB，PDF 最大 50 MiB。相对上传路径固定从 `backend` 目录解析，不受启动工作目录影响。

摄取远程调用发生在数据库短事务之外。成功写入 chunks 时使用事务原子替换；Embedding 或写入失败不会破坏既有 chunks。处理权使用条件更新领取，避免并发重复处理。

FastAPI `BackgroundTasks` 适用于当前单机开发环境，但不是持久任务队列；生产环境进程重启可能丢失尚未执行的后台任务。

### 5.1 Embedding 分批处理（2026-09-06）

`DashScopeEmbeddingProvider.embed()` 按最多 10 条非空文本分批请求，按输入顺序合并结果；仅重试失败批次，不重复发送成功批次。跨批次模型和维度必须一致，任一批失败时抛出异常，不返回部分向量。空输入位置沿用零向量占位行为，摄取层仍应拒绝无效向量。

真实 36 页 Python 资料生成 64 个切片，原来一次请求发送全部文本导致超过接口批量限制；修复后用户重新处理成功。不能由此推断任意 PDF 都能正确解析。

## 6. RAG 流程

```text
问题 + 当前用户 + document_ids
  -> 路由一次性验证所有文档所有权
  -> Embedding 查询向量
  -> pgvector cosine Top-K（再次按 user_id 过滤）
  -> 相似度阈值过滤
  -> 上下文字符预算
  -> Qwen 生成含 status 和 answer 的 JSON
  -> 回答状态及输出协议校验
  -> 引用合法性校验
  -> 只返回实际引用的 sources
```

服务端实际阈值为：

```python
max(RAG_MIN_SIMILARITY, request.min_similarity or 0.0)
```

客户端可以提高阈值，不能降低服务端底线。没有合格召回时直接返回 `insufficient_context=true`，不会调用 Chat Provider。

### 6.1 AI 控制层：回答状态与引用协议（2026-09-06）

相似度只表示检索相关性，不是答案正确率，也不能判断资料是否足以回答。RAG 系统提示要求模型只返回一个包含 `status`、`answer` 的 JSON 对象；普通 ChatProvider 接口和普通聊天接口不变。

| 模型内部 status | HTTP 响应行为 |
|---|---|
| `answered` | 保留答案，`insufficient_context=false`，只返回实际引用的来源 |
| `partial` | 保留有依据的答案和引用，明确缺失信息，`insufficient_context=true` |
| `insufficient` | 固定回答“现有文档不足以回答该问题。”，`sources=[]`，`insufficient_context=true` |

模型被调用时保留实际返回的 `model`；没有合格召回而直接拒答时 `model=null`。HTTP schema 暂未增加三态字段，前端对 partial 和 insufficient 均显示“资料不足”。

非 JSON、字段或状态错误、空答案、非正常结束原因被视为输出协议错误并返回 502。完整或部分回答必须有引用；不存在的引用返回 502。不再在无引用或引用无效时兜底返回全部检索来源。

该协议依赖模型遵循提示，不等于语义正确性证明。引用编号存在也不等于原文支持结论，仍需人工核对和多样化评测；JSON 格式不合规当前不自动修复或重试。

### 6.2 当前验证与后续交接

- 2026-09-06：`backend/tests` 完整回归 322 passed；RAG 专项连续两轮各 63 passed。
- 用户浏览器人工复测：Software Profiling 正常回答并引用 PDF 第 27 页；资料未提供的考试日期/考场拒答且无来源；混合提问保留可回答内容及引用，同时标记资料不足。
- 以上是特定样例验证，不是全部文档、知识点或生产质量验收。
- 上海“15分钟社区生活圈”行动工作导引：36 个 PDF 页面，约 29.6 MB。现有解析器生成 73 个切片，但中文大量乱码且未报错；另一提取工具也出现 CID 占位。严禁把“有字符”当作“解析正确”。
- PDF 第 5 页对应书内第 2、3 页，跨页排版需要区分物理页码和印刷页码。
- 仅在项目外做了 macOS 本地 OCR 单页试验：高清渲染改善明显，关键人口/面积数字可识别，但仍有漏字。OCR 未接入应用，不具备生产 OCR 能力，不应假定 macOS 试验可以直接部署到 Linux。
- 下次优先抽查表格及图文混排页，核对文字、数字、单位及阅读顺序，再决定异常文本检测和 OCR 方案；不要直接索引乱码，也不要由模型猜测纠正原文。
- 前端复选框存在 Element Plus label-as-value 弃用警告，待维护；未在本轮修改前端。
- 后续产品方向：可点击原文溯源、知识点卡片、选中知识点出题自测。均为待规划功能；PPTX/DOCX、识图、完整画布和学习者画像尚未因本轮试验而实现。

文档内容被视为不可信数据并与系统规则隔离。任何不存在、属于其他用户或 `NULL owner` 的文档都统一返回 404；混合合法和越权 ID 时整个请求失败，Provider 不会被调用。

## 7. API 一览

所有业务接口前缀为 `/api/v1`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| POST | `/auth/refresh` | 刷新 Access Token |
| GET | `/auth/me` | 当前用户 |
| POST | `/auth/logout` | 退出 |
| POST | `/chat/stream` | 普通流式聊天 |
| GET | `/chat/sessions` | 会话列表 |
| GET/PATCH/DELETE | `/chat/sessions/{id}` | 会话读取、重命名、删除 |
| POST | `/documents` | 上传文档，返回 202 |
| GET | `/documents` | 当前用户文档列表 |
| GET | `/documents/{id}` | 文档状态 |
| DELETE | `/documents/{id}` | 删除非 processing 文档 |
| POST | `/documents/{id}/reprocess` | 重新处理 failed 文档 |
| POST | `/rag/ask` | 指定文档范围的知识库问答 |

除健康检查、注册和登录外，受保护接口通过 `Authorization: Bearer <access_token>` 认证。Refresh Token 使用 HttpOnly Cookie。

## 8. 前端页面

- `/login`、`/register`：认证；
- `/`：功能入口；
- `/chat`：普通 AI 聊天；
- `/documents`：上传、查看状态、重新处理和删除文档；
- `/knowledge-ask`：选择成功文档、提问并查看引用来源；
- `/about`：项目说明。

前端文件校验用于即时反馈，后端校验始终是最终安全边界。

## 9. 测试与验收

后端完整测试：

```bash
cd backend
.venv/bin/pytest -q
```

前端静态验证：

```bash
cd frontend
npm run type-check
npm run lint
npm run build
```

真实服务验收脚本：

```bash
cd backend
.venv/bin/python scripts/check_embedding.py
.venv/bin/python scripts/check_rag_pipeline.py
.venv/bin/python scripts/check_rag_answer.py
.venv/bin/python scripts/check_document_http_pipeline.py \
  --base-url http://127.0.0.1:8000 --timeout 120
```

运行真实 DashScope 脚本时可按本机网络情况清除代理环境变量。脚本不得打印 API Key、完整 Prompt 或向量。

当前基线（2026-09-05）：完整后端测试 `298 passed`。该数字会随测试增加而变化，应以本地最新运行结果为准。

## 10. 数据库迁移

```bash
cd backend
alembic current
alembic heads
alembic upgrade head
```

当前迁移包含文档表、pgvector 扩展、`document_chunks` 和文档所有权隔离。不要修改已经应用过的历史迁移；结构修正应新增迁移。

迁移或测试前建议备份：

```bash
docker compose exec -T postgres pg_dump \
  -U coursemind -d coursemind -Fc > backups/coursemind.dump
```

恢复时先导入临时数据库并核查，不要直接覆盖当前数据库。

## 11. 安全与数据操作约束

- 禁止按文件名模式或全表条件清理测试数据；测试只按自己创建的 UUID 删除。
- 删除文件前必须验证目标目录位于上传根目录内。
- 不向客户端返回绝对路径、密钥、Provider 原始错误或堆栈。
- 权限检查必须以服务端认证用户为准，不能接受客户端传入的 `user_id`。
- RAG 路由必须在调用 Embedding/Chat Provider 前完成全部文档授权检查。
- `.env`、上传文件、数据库 dump 不得提交版本控制。
- 不要执行 `docker compose down -v`，除非明确要永久删除数据库卷。

## 12. 常见问题

### `/health` 返回 404

正确地址是 `/api/v1/health`。

### DashScope 返回 403、DNS 或代理错误

确认 API Key 有效，并检查代理环境。适配器默认可读取系统代理；若代理拒绝转发，可设置 `EMBEDDING_TRUST_ENV=false` 或在启动进程时清除代理变量。

### 文档一直 pending/processing

检查后端日志、`processing_jobs` 状态和磁盘文件是否存在。开发环境后台任务不持久，服务重启后可能需要将失败任务重新处理。

### 文档成功但 RAG 返回资料不足

确认选择了正确文档，检查 chunk 是否存在，并观察最高相似度与 `RAG_MIN_SIMILARITY`。阈值应依据评测集调整，不应为了让单个问题通过而随意降低。

### 前端构建出现大 chunk 警告

这是 Vite 的体积警告，不代表构建失败。后续可通过路由懒加载和 `manualChunks` 优化。

## 13. 当前已知限制与建议顺序

1. 用持久任务队列替换进程内 BackgroundTasks；
2. 建立带标注问题/答案/来源的 RAG 评测集；
3. 增加前端 Vitest 与端到端浏览器测试；
4. 增加结构化日志、指标与任务恢复机制；
5. 优化前端按路由拆包；
6. 部署前明确对象存储、备份、密钥管理和 HTTPS 策略。

## 14. 修改功能时的最小检查清单

- 是否保持用户所有权隔离？
- 是否避免在远程 API 调用期间持有长事务或锁？
- 失败是否保留原有有效 chunks？
- 是否只清理本次测试创建的数据和目录？
- 是否增加正向、失败、越权和边界测试？
- 后端完整测试是否通过？
- 前端 type-check、lint、build 是否通过？
- 是否更新本手册中受影响的接口或流程？
