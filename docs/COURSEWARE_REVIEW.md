# 课件复习开发指南 / Courseware Review

实现日期：2026-11-13。入口为 `/review`，首页、文档管理和学习画布均有入口。本文描述已经实现的功能及其边界。

## 中文说明

### 产品流程

1. 上传 PDF、PPTX、TXT 或 Markdown；选择最多 8 份同一用户的资料。
2. 选择是否逐页视觉读取，生成章节讲解。默认只读取文字；勾选后将每个 PDF/PPTX 原页的 JPEG 提交给配置的视觉模型，包括已有文字的页面。
3. 章节包含原文、讲解、推导、缺失说明、公式、表格、原始代码、本节要点及按需演示。仅保留有课件依据的内容，不把模型扩展或考试预测当作课件内容。
4. 页码标签可悬停/聚焦预览摘录和原图，点击放大；原图可前后翻页并返回对应讲解。目录、要点、速查和搜索可定位正文。
5. 速查按文件和章节组织定义、公式、规则、结论、步骤，支持类型计数、关键词筛选和双向跳转。
6. 每节手动标记已复习；这与学习画布按追问频次标记易忘点的逻辑独立。
7. AI 勘误先作为候选，展示原表述、建议修正、依据和影响；用户可确认、忽略或重置。
8. 下载一个包含图片、公式字体、样式和脚本的 HTML 文件，可离线双击使用。离线进度与决定仅存于该浏览器，不回写服务器。

课件复习直接读取存储的原文件，**不要求向量索引成功**。因此扫描 PDF 上传后即使显示索引失败，仍可从该文档的“课件复习”入口启用视觉读取；这不会替扫描件建立可用于 RAG 的 OCR 索引。纯图片文件及旧 `.ppt` 暂不支持，需转成 PDF/PPTX。

### 实现与数据流

- `backend/app/api/routes/review.py`：认证、所有权、任务创建、读取、进度/勘误决定、原页图片与删除。
- `backend/app/schemas/review.py`：Pydantic 结构化输出契约。
- `backend/app/services/review.py`：全文分批、视觉调用、总结调用、覆盖/引用校验、有限重试、重复页提示及持久化。
- `backend/app/services/review_media.py`：PDFium 渲染；PPTX 使用独立 LibreOffice profile 转为 PDF，再按物理页渲染。
- `backend/app/services/review_checks.py`：显式四则运算复算、线性演示系数校验。
- `backend/app/parsers/pptx_parser.py`：供既有摄取/RAG 使用的幻灯片文字及表格提取；图片和复杂图形不进入这个文字索引。
- `frontend/src/views/CoursewareReviewView.vue`：复习阅读、目录、速查、搜索、原页弹窗、状态和进度。
- `frontend/src/components/Review*.vue`：安全公式渲染、来源卡片及演示组件。
- `frontend/src/utils/reviewExport.ts`：独立离线 HTML，不使用 CDN，不包含令牌或 API Key。

全文生成与 `/rag/ask` 分离。按照原页顺序，每批最多 4 页且文字与视觉描述合计最多 24,000 字符；单页超限明确失败，**不会静默截断**。模型将相邻页按主题归入章节；当前章节边界也会受批次边界影响，不进行跨批主题重排。合并课件时保留用户选择的文件顺序。重复页面按去空白后的文字完全一致检测并显示关联，不自动删掉原页，也不声称能识别语义近似或修订差异。

每条事实性 block、要点、速查、演示及勘误都带 `page + quote`。后端验证页码属于该章节、摘录确实出现在对应文字层或视觉描述中，并标明 `origin=text|vision`；每页必须按顺序且仅归属一个章节。代码与原文摘录也要匹配来源。结构/引用不合格时重试一次，仍失败则任务失败，不发布成品，也不替换为虚构的演示内容。

**引用字符串存在不是语义蕴含的证明。** 视觉模型也可能误读，`origin=vision` 明确表示视觉模型的读取结果。推导、勘误和重要数字仍需人核对。

### 演示与核对范围

- `steps`：上一步、下一步、重置，逐步展示课件已有过程或算例。
- `linear`：仅支持来源中明确写出的数值形式 `y = ax + b`；后端核对数值系数，前端滑块同步更新数值与图形。其他公式使用步骤演示，不执行模型生成的任意代码。
- 探索性输入标明示意用途，不能当作课件的原始观测数据。每个演示都有来源标签。
- 确定性复算目前只检查原文中显式写出的数字加减乘除等式，容忍所示精度的舍入；不会校验所有公式、图片内运算、单位或数学证明。复算发现的问题仍需要用户确认。
- 课件代码原样展示，**不会在服务端自动执行上传代码**。

### 配置与依赖

```dotenv
DASHSCOPE_API_KEY=your-existing-key
RAG_CHAT_MODEL=qwen3.8-flash
REVIEW_VISION_MODEL=qwen3-vl-plus
REVIEW_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REVIEW_MAX_PAGES=120
REVIEW_JOB_TIMEOUT_SECONDS=1800
```

`REVIEW_MAX_PAGES` 是一次请求所有资料的合计上限。模型名称、服务区域和账号权限必须匹配；视觉模型可替换为支持 OpenAI-compatible `image_url` 输入的模型。`REVIEW_AI_BASE_URL` 是服务端配置，客户端不能覆盖。文字与视觉调用共用现有 DashScope Key，开启视觉读取会增加调用次数、时间和费用。

后端安装 `pypdfium2`、`Pillow`、`python-pptx`；前端安装 `katex`。PPTX 原页查看需要 LibreOffice 的 `soffice` 命令，本地没有时可先导出 PDF。Dockerfile 已安装 `libreoffice-impress` 和中文字体。转换使用临时目录、独立 profile、120 秒超时；PDFium 调用由锁串行化。PPTX 展开体积限制为 200 MB。

```bash
cd backend
.venv/bin/python -m pip install -e '.[dev]'
# 本地需安装 LibreOffice 并确保 soffice 位于 PATH；或使用 Docker 镜像。
cd ../frontend
npm install
```

### API

所有接口沿用 Bearer access token 和现有刷新流程；不接受客户端传入的用户身份。

| 方法与路径 | 行为 |
| --- | --- |
| `POST /api/v1/reviews` | `{document_ids, response_language, use_vision}`；202 返回任务 |
| `GET /api/v1/reviews?limit=50` | 当前用户可访问的历史任务，limit 1–100 |
| `GET /api/v1/reviews/{id}` | 任务状态、文档页、章节、速查、演示、进度、勘误 |
| `PATCH /api/v1/reviews/{id}/state` | `reviewed_sections` 或 `erratum_id + decision` |
| `GET /api/v1/reviews/{id}/documents/{doc}/pages/{page}/image` | 认证后的原页 JPEG；页码为从 1 开始的物理页码 |
| `DELETE /api/v1/reviews/{id}` | 删除复习记录和派生图片，不删除原始课件 |

状态：`queued → processing → ready|failed`。`completed_pages` 在每批总结验证后更新。`decision` 为 `candidate|confirmed|dismissed`，确认仅代表用户决定。只有 ready 状态可更改学习进度和勘误决定。

所有读取、图片、更新和删除都重新核对所有来源文件的归属。任意来源不存在、归属他人或没有 owner 时，整个请求统一 404。删除原始文档后，对应旧复习也不可再访问；派生目录仍需按备份/保留策略清理。

无 Key 返回 503；每个用户最多 2 个活动任务，超限 429；活动记录删除返回 409。中断遗留记录在创建超过 61 分钟后可以移除并重新生成。任务有 30 分钟默认总超时，可配置 60–3600 秒。生成失败不会泄露上游原始响应、密钥或文件路径。

真实服务连通性检查仅使用自制样例，但会调用付费服务：`PYTHONPATH=. .venv/bin/python scripts/smoke_review.py --pptx --vision`。

### 存储、部署与恢复

无需数据库迁移：原始文档继续存于现有上传目录，复习结果以 JSON 和派生图片存于：

```text
UPLOAD_ROOT/.reviews/{user_id}/{review_uuid}/review.json
UPLOAD_ROOT/.reviews/{user_id}/{review_uuid}/{document_uuid}/page-{n}.jpg
UPLOAD_ROOT/.reviews/{user_id}/{review_uuid}/{document_uuid}/source.pdf  # PPTX 转换结果
```

JSON 用临时文件原子替换。在线进度与勘误决定随记录保存在服务器，重新打开可恢复。生成由 FastAPI BackgroundTasks 驱动，使用进程内并发控制（全局 2 个生成任务）；**当前支持单个 API worker、持久本地上传卷**。多 worker、多副本、分布式存储、跨进程并发限制、自动续跑尚未实现。重启可能留下 processing 状态；不会冒充成功，需删除过期记录再生成。生产扩容前应接持久任务队列和共享事务存储。

离线导出逐页获取原图，原图合计超过 100 MB 则中止并提示缩小范围。HTML 使用限制外部连接的 CSP，正文转义后渲染，KaTeX 设置 `trust:false`。文件包含所选课件的原图与文本，应按原始资料的访问范围自行保管。该 HTML 的浏览器存储只是离线便利功能，不是用户身份认证。

### 验证

```bash
cd backend
.venv/bin/python -m pytest tests/test_review.py -q
cd ../frontend
npm run type-check
npm run build
npx playwright install chromium
npm run test:e2e
```

浏览器测试使用合成课件和模拟 API，验证桌面/窄屏布局、公式、原页预览与翻页、要点与速查跳转、搜索、进度、勘误、演示以及离线断网行为。模型协议和越权在后端独立测试；真实服务还需通过小样本人工/集成验证，不能把 UI 的模拟接口验收当成模型质量评测。

旧后端测试有预置 `user_id=1` 和受保护 `test2.pdf` 元数据的依赖。全量回归请使用独立、名称包含 `_test` 的数据库，迁移后执行下列脚本生成**合成记录**，不要复制真实课程资料：

```bash
cd backend
export DATABASE_URL=postgresql+psycopg://coursemind:coursemind_dev@127.0.0.1:5432/coursemind_review_test
.venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python scripts/prepare_review_test_database.py
.venv/bin/python -m pytest tests -q
```

2026-11-13 的验证结果记录在 [发布验证](REVIEW_VALIDATION.md)。

## English implementation notes

Courseware Review is an authenticated `/review` workspace, linked from Home, Documents and the existing Learning Canvas. It reads complete stored sources independently of top-k RAG. PDF/PPTX originals can be rendered and optionally read by a vision model; TXT/Markdown remain text-only. An indexing failure does not prevent review generation. Visual reading does **not** create an OCR-backed RAG index.

The pipeline preserves source order, batches at most four pages and 24,000 characters, and rejects oversized pages rather than truncating them. Every page must belong to exactly one ordered section. Evidence quotes must occur in the referenced page text or vision description; provenance distinguishes `text` from `vision`. Typed validation retries once, then fails explicitly. This does not prove semantic correctness or eliminate vision hallucinations. Duplicate notes detect exact normalized text only; original pages and sections remain available.

The reader provides chapter explanations, source quotations, derived statements, missing-content notices, formulas, tables, verbatim code, takeaways, quick references, search, original-page previews, manual progress, source-based step demonstrations, numeric affine exploration and user decisions on proposed corrections. Source code is displayed, never automatically executed. Deterministic arithmetic checks cover only explicit basic numeric equations, tolerate displayed rounding, and still produce unconfirmed candidates. Affine demonstrations require coefficients matching a literal numeric source equation `y=ax+b`.

The API routes and configuration above apply equally to English (`response_language=en-US`). Progress and correction decisions persist in server JSON; offline exports embed originals, fonts and scripts and retain browser-local state only. Every request rechecks ownership of **all** referenced documents. Foreign, unowned or deleted sources make the artifact inaccessible with 404. Requests cannot specify a user identity or provider endpoint.

No migration is needed. Back up the persistent upload volume including `.reviews`. This release supports **one API worker** with local persistent storage and process-local concurrency limits. Background generation does not resume after a restart. Default total job timeout is 1,800 seconds; interrupted records may be removed after 61 minutes. A durable queue and shared transactional storage are prerequisites for multiworker/multireplica deployment. Offline original-image payloads are limited to 100 MB.

PPTX indexing extracts text and table content with python-pptx. Original slide rendering additionally requires LibreOffice; Docker includes Impress and CJK fonts. PPTX conversion uses a private temporary profile and a 120-second timeout. PDFium rendering is serialized. Expanded PPTX archives are limited to 200 MB.

Browser tests use synthetic materials and mocked APIs. They verify application interactions, real KaTeX rendering, responsive layout and network-free offline export. Backend tests separately verify model contracts, coverage, quotation matching, failure handling and authorization. See [validation results](REVIEW_VALIDATION.md) for actual external-provider smoke tests and the full regression run. Legacy tests require synthetic prerequisite rows prepared with the test-only script above.

## 官方实现参考 / Primary references

- [Qwen vision inputs](https://www.alibabacloud.com/help/en/model-studio/vision)
- [PDFium Python API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
- [KaTeX rendering options](https://katex.org/docs/options.html)
