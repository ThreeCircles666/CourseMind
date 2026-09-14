# CourseMind - AI 驱动的学习画布

> 把课件变成可追问的知识画布，让 AI 帮学生找到自己的易忘点

CourseMind（课灵）不只是问答工具，而是将课程资料转化为可视化学习画布的 AI 学习平台。通过智能提炼知识点、支持局部追问、自动标记易忘点，帮助学生更高效地复习和理解课程内容。

## ✨ 核心特性

### 🎨 学习画布（Hackathon 核心展示）
- **AI 知识卡片生成**：自动从课件提炼 6-10 个核心知识点
- **可视化组织**：彩色标签分类（定义、公式、例子、易错点、考点）
- **局部追问**：针对单个知识点深入提问
- **子卡片回写**：追问结果作为新卡片追加到画布
- **来源追溯**：显示页码和原文片段，建立可信引用链
- **易忘点自动标记**：多次追问的知识点自动标为"易忘点"
- **中英双语**：完整的多语言支持

### 📚 知识库 RAG（真实实现）
- **文档上传**：支持 TXT、Markdown、PDF 格式
- **智能问答**：基于上传资料的 RAG 问答
- **来源引用**：每个回答显示引用来源和相似度
- **文档管理**：上传、查看、删除、重新处理

### 🔐 用户系统
- 完整的注册、登录、Token 刷新机制
- 文档所有权隔离

## 🚀 快速启动（Docker 一键启动）

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存

### 一键启动
```bash
# 克隆项目
cd CourseMind

# 启动所有服务（首次会自动构建）
docker compose up --build

# 或使用自动验证脚本
chmod +x start-docker.sh
./start-docker.sh
```

**启动后访问**：
- 前端：http://127.0.0.1:5174
- 后端 API：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

### 快速 Demo 流程

1. 访问前端：http://127.0.0.1:5174
2. 注册账号（用户名：`demo_user`，密码：`demo123456`）
3. 登录后点击「学习画布」
4. 点击「加载演示画布」
5. 点击任意知识卡片查看详情
6. 点击「解释得更简单」→ 观察子卡片生成
7. 再点击「举一个例子」→ 观察易忘点标记
8. 切换语言到 English 测试多语言

**完整演示脚本**: 见 [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)

## 🎯 功能边界说明

### ✅ 已完整实现

**学习画布 - 演示模式**：
- 内置 6 张演示知识卡片（线性代数主题）
- 追问功能（真实 AI 失败时自动 fallback）
- 子卡片生成和画布回写
- 易忘点标记（基于追问次数）
- 来源显示（演示数据）
- 多语言切换

**知识库系统**：
- 文档上传（TXT、Markdown、PDF）
- 文档解析和分块
- DashScope Embedding 向量化
- pgvector 余弦相似度检索
- RAG 问答（需要 API Key）
- 来源引用和置信度

**用户系统**：
- JWT 认证
- 文档权限隔离
- Token 刷新机制

### ⚠️ 需要 DashScope API Key 的功能

如果没有配置 `DASHSCOPE_API_KEY`：
- ✅ **仍可使用**：登录、注册、演示画布、追问 fallback
- ❌ **无法使用**：文档处理（embedding）、真实 RAG 问答、基于文档生成画布

**配置方式**（可选）：
编辑 `docker-compose.yml`：
```yaml
backend:
  environment:
    DASHSCOPE_API_KEY: sk-your-key-here
```

### 📋 当前不支持

为保持 Hackathon MVP 聚焦，以下功能未实现：
- ❌ PPTX、DOCX、图片上传
- ❌ OCR 识别
- ❌ 图片局部框选
- ❌ 真正无限画布和拖拽
- ❌ 完整学习者模型（当前易忘点基于追问次数的简单规则）
- ❌ 长期学习记录持久化
- ❌ 课外知识联网搜索

### 🎨 设计理念

**核心问题**：学生复习时，面对整本课件不知道重点在哪，哪些知识点需要反复看。

**解决方案**：
1. **AI 提炼**：从课件自动提炼核心知识点
2. **可视化**：用彩色卡片画布组织，比列表更直观
3. **交互式**：点击卡片局部追问，不是全文问答
4. **个性化**：多次追问的变成"易忘点"，反映学生自己的薄弱环节
5. **可追溯**：每个知识点显示页码和原文，建立信任

## 🏗️ 技术架构

### 技术栈
- **前端**：Vue 3 + TypeScript + Vite + Element Plus + vue-i18n
- **后端**：Python 3.11 + FastAPI + SQLAlchemy + Alembic
- **数据库**：PostgreSQL 17 + pgvector
- **AI**：阿里云 DashScope (Qwen + text-embedding-v3)
- **容器**：Docker + Docker Compose

### 系统架构
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌─────────────┐
│  Frontend   │
│  (Vue 3)    │
└──────┬──────┘
       │ /api proxy
       ↓
┌─────────────┐      ┌──────────────┐
│   Backend   │─────→│  DashScope   │
│  (FastAPI)  │      │ Qwen/Embedding│
└──────┬──────┘      └──────────────┘
       │ SQL
       ↓
┌─────────────┐
│ PostgreSQL  │
│  + pgvector │
└─────────────┘
```

### AI 使用方式

**Embedding**（文档向量化）：
- 模型：`text-embedding-v3`
- 用途：将文档分块转为向量存储在 pgvector
- 检索：余弦相似度匹配

**LLM**（问答生成）：
- 模型：`qwen-turbo`
- 用途：基于检索到的文档片段生成回答
- Prompt：包含知识点上下文，适合学生复习场景

**Fallback 机制**：
- 前端内置 6 张演示卡片（线性代数主题）
- AI 失败时自动切换，保证 Demo 不中断
- 明确标注"演示模式"，不伪装
- Docker 开发环境中，前端默认通过 Vite `/api` 代理访问后端，避免浏览器跨域问题

## 📂 项目结构

```
CourseMind/
├── frontend/           # Vue 3 前端
│   ├── src/
│   │   ├── views/      # 页面组件
│   │   │   ├── LearningCanvasView.vue  # 学习画布
│   │   │   ├── KnowledgeAskView.vue     # 知识库问答
│   │   │   └── DocumentsView.vue        # 文档管理
│   │   ├── i18n/       # 多语言
│   │   └── api/        # API 客户端
│   └── Dockerfile
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── api/        # API 路由
│   │   ├── services/   # 业务逻辑
│   │   ├── models/     # 数据库模型
│   │   └── ai/         # AI 适配器
│   ├── alembic/        # 数据库迁移
│   └── Dockerfile
├── docker-compose.yml  # Docker 编排
├── DEMO_SCRIPT.md      # 演示脚本
├── SUBMISSION_SUMMARY.md  # 项目总结
└── DEMO_CHECKLIST.md   # 演示检查清单
```

## 📖 文档导航

- **[Docker 快速启动](DOCKER_QUICKSTART.md)** - Docker 使用指南
- **[演示脚本](DEMO_SCRIPT.md)** - 3 分钟/5 分钟演示流程
- **[项目总结](SUBMISSION_SUMMARY.md)** - 提交给评委的总结
- **[演示检查清单](DEMO_CHECKLIST.md)** - 现场演示前检查
- **[开发者指南](docs/DEVELOPER_GUIDE.md)** - 开发环境配置

## 🛠️ 开发模式

如需本地开发（不使用 Docker）：

```bash
# 终端 1: 数据库
docker compose up postgres

# 终端 2: 后端
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env  # 配置环境变量
alembic upgrade head
uvicorn app.main:app --reload

# 终端 3: 前端
cd frontend
npm install
npm run dev
```

## 🤝 贡献

这是一个 Hackathon 项目，当前聚焦 MVP 功能展示。

## 📄 许可

MIT License

## 🎓 致谢

- 阿里云 DashScope
- pgvector
- FastAPI、Vue 3 社区

---

**Demo 视频**（如有）：[链接]

**团队**：[团队名称]

**Hackathon**：[活动名称]
