# CourseMind - AI 学习画布

语言：[English](README.md) | [简体中文](README.zh-CN.md)

> **CourseMind：从课件到笔记、追问、自测与复习重点，一站式生成你的 AI 学习画布。**

CourseMind 是一个面向学生和教学场景的 AI 学习工作流平台。它可以把上传的课程资料转化为可追溯的知识库回答、学习卡片、AI 对话、自测题和复习重点。产品围绕完整学习路径设计：上传/管理课程文档，基于知识库提问，在学习画布中组织内容，并通过 AI 对话继续辅助学习。

## 当前版本亮点

- 已完成 8 个核心页面的页面级 UI/UX 优化。
- 所有页面都提供语言选择器。
- AI 回答会跟随 CourseMind 当前界面语言。
- 中英文文案通过 `vue-i18n` 维护，避免大量硬编码。
- 新增统一设计令牌，统一颜色、间距、卡片、按钮和页面节奏。
- Devpost 提交材料已整理到 `submission/devpost/`。

## 核心功能

### AI 学习画布

- 从上传课件中提炼复习知识点。
- 用卡片组织定义、公式、例子、易错点和考试重点。
- 支持围绕单个知识点继续追问。
- 追问回答会作为子卡片回写到画布，形成个人学习脉络。
- 多次追问的知识点会自动标记为易忘点。
- 在可用时展示来源文件、页码和原文片段。
- 内置演示模式 fallback，方便稳定展示完整工作流。

### 知识库问答

- 支持上传 TXT、Markdown 和可复制文本的 PDF。
- 自动解析、分块、向量化并存入 PostgreSQL + pgvector。
- 基于用户选择的文档进行检索增强问答。
- 展示引用来源和相似度信息。
- 区分完整回答、部分回答和资料不足。
- 根据当前界面语言返回中文或英文答案。

### AI 对话

- 提供专注的学习辅助对话界面。
- 支持会话历史、会话切换、重命名和删除。
- 支持流式输出。
- 使用当前界面语言作为 AI 回答语言。

### 文档管理

- 上传和管理课程资料。
- 展示解析和索引状态。
- 支持刷新、删除等基础操作。
- 按登录用户隔离文档所有权。

### 国际化体验

- 内置 `zh-CN` 和 `en-US` 两套语言包。
- 首页、登录、注册、文档管理、知识库问答、学习画布、AI 对话和关于页均可切换语言。
- 语言选择会保存到浏览器本地。
- 主要 AI 工作流会接收当前语言，并按该语言作答。

## 页面

| 路由 | 页面 |
| --- | --- |
| `/` | 学习工作台 / 首页 |
| `/login` | 登录 |
| `/register` | 注册 |
| `/documents` | 文档管理 |
| `/knowledge-ask` | 知识库问答 |
| `/canvas` | 学习画布 |
| `/chat` | AI 对话 |
| `/about` | 产品说明与系统状态 |

## 快速启动

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 可选：阿里云 DashScope API Key，用于真实 AI 流程

### 使用 Docker 启动

```bash
git clone https://github.com/ThreeCircles666/CourseMind.git
cd CourseMind

export DASHSCOPE_API_KEY=sk-your-key-here
docker compose up --build
```

启动后访问：

- 前端：http://127.0.0.1:5174
- 后端 API：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

也可以使用项目脚本：

```bash
chmod +x start-docker.sh
./start-docker.sh
```

## DashScope 配置

CourseMind 的真实 AI 流程依赖 DashScope：

- `text-embedding-v3` 用于文档向量化。
- Qwen 对话模型用于 RAG 问答、AI 对话和学习画布生成。

如果没有配置 `DASHSCOPE_API_KEY`：

- 注册、登录、优化后的界面、演示画布和 fallback 流程仍可使用。
- 真实文档向量化、基于资料的知识问答和文档画布生成需要 API Key。

## 演示流程

1. 打开 http://127.0.0.1:5174。
2. 注册并登录。
3. 在语言选择器中选择中文或 English。
4. 进入「文档管理」，上传 TXT、Markdown 或可复制文本的 PDF。
5. 等待文档状态变为成功。
6. 进入「知识库问答」，提问并查看引用来源。
7. 打开「学习画布」，基于文档生成学习卡片。
8. 选择卡片继续追问，并生成自测题。
9. 打开「AI 对话」，验证回答会跟随当前界面语言。

没有 API Key 时，可以使用学习画布的演示路径展示完整交互。

## 技术架构

### 技术栈

- 前端：Vue 3、TypeScript、Vite、Vue Router、Pinia、Element Plus、vue-i18n
- 后端：Python 3.11、FastAPI、SQLAlchemy、Alembic
- 数据库：PostgreSQL 17、pgvector
- AI：DashScope Qwen、DashScope `text-embedding-v3`
- 部署：Docker、Docker Compose

### 系统结构

```text
Browser
  |
  | HTTP / REST
  v
Frontend (Vue 3 + Element Plus + vue-i18n)
  |
  | /api proxy
  v
Backend (FastAPI)
  |              \
  | SQL           \ DashScope Qwen / Embedding
  v               v
PostgreSQL + pgvector
```

## 项目结构

```text
CourseMind/
├── frontend/
│   ├── src/
│   │   ├── api/              # 前端 API 客户端
│   │   ├── assets/           # 设计令牌和全局样式
│   │   ├── components/       # 复用组件
│   │   ├── composables/      # 流式对话等复用逻辑
│   │   ├── i18n/             # zh-CN / en-US 语言包
│   │   ├── stores/           # 登录和应用状态
│   │   └── views/            # 页面组件
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── ai/               # AI 契约和适配器
│   │   ├── api/              # FastAPI 路由
│   │   ├── models/           # 数据库模型
│   │   ├── parsers/          # TXT / Markdown / PDF 解析
│   │   └── services/         # RAG、检索、上传、摄取逻辑
│   ├── alembic/              # 数据库迁移
│   └── Dockerfile
├── submission/devpost/       # Hackathon 提交包
├── docker-compose.yml
├── start-docker.sh
├── README.md                 # English
└── README.zh-CN.md           # 简体中文
```

## 本地开发

```bash
# 终端 1：数据库
docker compose up postgres

# 终端 2：后端
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[dev]"
export DASHSCOPE_API_KEY=sk-your-key-here
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 终端 3：前端
cd frontend
npm install
npm run dev
```

本地 Vite 默认端口通常是 http://localhost:5173；Docker 版前端端口是 http://127.0.0.1:5174。

## 测试与检查

```bash
# 前端类型检查和生产构建
cd frontend
npm run type-check
npm run build

# 后端测试，需要本地安装测试依赖
cd backend
.venv/bin/python -m pytest
```

## Hackathon 提交材料

Devpost 提交包位于 `submission/devpost/`：

- `DEVPOST_SUBMISSION.md`
- `JUDGE_TESTING_INSTRUCTIONS.md`
- `DEMO_VIDEO_SCRIPT.md`
- `PITCH_DECK_OUTLINE.md`
- `AI_USAGE_AND_DISCLOSURE.md`
- `SUBMISSION_CHECKLIST.md`
- `CourseMind_AI_Builders_Hackathon_Deck_v2.pptx`

## 当前边界

- 支持 TXT、Markdown、可复制文本的 PDF；暂不支持 PPTX、DOCX 和图片 OCR。
- 扫描版 PDF 或特殊字体编码的 PDF 可能无法解析。
- 学习画布当前是结构化卡片工作区，不是真正无限自由画布。
- 易忘点基于交互频率标记，尚未实现长期学习画像。
- RAG 回答只基于上传资料，不进行联网搜索。

## 文档

- [Docker 快速启动](DOCKER_QUICKSTART.md)
- [演示脚本](DEMO_SCRIPT.md)
- [演示检查清单](DEMO_CHECKLIST.md)
- [项目总结](SUBMISSION_SUMMARY.md)
- [开发者指南](docs/DEVELOPER_GUIDE.md)

## 许可

MIT License
