# CourseMind - AI 驱动的学习画布

语言：[English](README.md) | [简体中文](README.zh-CN.md)

> 把课件变成可追问、可溯源、可复习的知识画布。

CourseMind 是一个面向学生复习场景的 AI 教学辅助平台。用户上传 TXT、Markdown 或 PDF 课件后，系统会解析文档、生成向量索引，并通过 RAG 问答和学习画布把资料转化为可追问的知识卡片。界面支持简体中文和 English，用户可在页面右上角随时选择语言。

## 核心功能

### 学习画布

- AI 从上传课件中提炼 6-10 个复习知识点。
- 用卡片标签区分定义、公式、例子、易错点和高频考点。
- 支持点击单个知识点继续追问。
- 追问回答会作为子卡片回写到画布，形成个人学习脉络。
- 多次追问的知识点会自动标记为易忘点。
- 真实生成结果显示来源文件、页码和原文片段。
- AI 生成失败时自动回退到演示结构，保证演示不中断。

### 知识库问答

- 支持上传 TXT、Markdown、PDF。
- 自动解析、分块、向量化并写入 PostgreSQL + pgvector。
- 基于用户选择的文档进行 RAG 问答。
- 回答必须基于检索来源，并显示引用和相似度。
- 后端会区分资料不足、部分回答和完整回答。

### 用户与语言选择

- 支持注册、登录、访问令牌刷新和文档所有权隔离。
- 前端使用 `vue-i18n`，内置 `zh-CN` 和 `en-US`。
- 语言选择器为全局控件，登录页、首页、知识库、问答和学习画布均可切换。
- 语言选择会保存到浏览器本地存储，下次打开自动沿用。

## 快速启动

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 可选：阿里云 DashScope API Key

### 使用 Docker 启动

```bash
git clone https://github.com/ThreeCircles666/CourseMind.git
cd CourseMind

# 如需真实文档处理和 RAG，请先配置环境变量
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
- `qwen-turbo` 用于 RAG 问答和画布知识点生成。

如果没有配置 `DASHSCOPE_API_KEY`：

- 仍可使用注册、登录、演示画布和部分 fallback 流程。
- 无法使用真实文档向量化、知识库问答和基于上传文档的画布生成。

推荐用环境变量启动：

```bash
export DASHSCOPE_API_KEY=sk-your-key-here
docker compose up --build
```

## 演示流程

1. 打开 http://127.0.0.1:5174。
2. 注册并登录。
3. 在右上角选择简体中文或 English。
4. 进入「知识库」，上传 TXT、Markdown 或可复制文字的 PDF。
5. 等待文档状态变为「成功」。
6. 点击「生成画布」，进入学习画布。
7. 点击「生成学习画布」，查看基于课件的知识卡片。
8. 点击卡片，在右侧详情区继续追问或生成自测题。

没有 API Key 时，可直接在学习画布点击「加载演示画布」体验完整交互。

## 技术架构

### 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、vue-i18n
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
│   │   ├── i18n/             # zh-CN / en-US 语言包
│   │   ├── stores/           # 登录状态
│   │   └── views/            # 页面组件
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── ai/               # DashScope 适配器
│   │   ├── api/              # FastAPI 路由
│   │   ├── models/           # 数据库模型
│   │   ├── parsers/          # TXT / Markdown / PDF 解析
│   │   └── services/         # RAG、检索、上传、摄取逻辑
│   ├── alembic/              # 数据库迁移
│   └── Dockerfile
├── docker-compose.yml
├── start-docker.sh
├── DEMO_SCRIPT.md
├── README.md             # English
└── README.zh-CN.md       # 简体中文
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

## 当前边界

- 支持 TXT、Markdown、PDF；暂不支持 PPTX、DOCX 和图片 OCR。
- PDF 需要是可复制文本的 PDF，扫描版或特殊字体编码可能无法解析。
- 学习画布当前是卡片网格，不是真正无限画布。
- 易忘点基于追问次数标记，尚未实现长期学习画像。
- RAG 回答只基于上传资料，不进行联网搜索。

## 测试与检查

```bash
# 前端类型检查
cd frontend
npm run type-check

# 后端测试，需要本地安装测试依赖
cd backend
.venv/bin/python -m pytest
```

## 文档

- [Docker 快速启动](DOCKER_QUICKSTART.md)
- [演示脚本](DEMO_SCRIPT.md)
- [演示检查清单](DEMO_CHECKLIST.md)
- [项目总结](SUBMISSION_SUMMARY.md)
- [开发者指南](docs/DEVELOPER_GUIDE.md)

## 许可

MIT License
