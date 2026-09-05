# CourseMind

CourseMind（课灵）是一个面向教育场景的知识库问答与 AI 助手。项目采用 Vue 3、FastAPI、PostgreSQL/pgvector 和阿里云 DashScope。

## 已实现

- 用户注册、登录、刷新令牌与退出；
- Qwen 流式聊天与会话历史；
- TXT、Markdown、PDF 上传、解析、切片和重复检测；
- DashScope Embedding 与 pgvector 余弦相似度检索；
- 带来源引用和资料不足判断的 RAG 问答；
- 文档所有权隔离、删除与失败后重新处理；
- 文档管理和知识库问答页面。

## 快速入口

- [开发者手册](docs/DEVELOPER_GUIDE.md)
- [后端说明](backend/README.md)
- API 文档（启动后）：<http://127.0.0.1:8000/docs>
- 前端（启动后）：<http://127.0.0.1:5173>

## 最小启动流程

```bash
# 仓库根目录
docker compose up -d postgres

# 终端 1
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 2
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

运行前请从 `backend/.env.example` 和 `frontend/.env.example` 创建本地 `.env`，并配置数据库、JWT 密钥和 DashScope API Key。完整命令及安全注意事项见开发者手册。
