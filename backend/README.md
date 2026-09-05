# CourseMind Backend

CourseMind 后端是基于 FastAPI、SQLAlchemy、PostgreSQL/pgvector 和 DashScope 的认证、文档处理、向量检索与 RAG 服务。

完整架构、数据流、API、安全规则和故障排查见 [开发者手册](../docs/DEVELOPER_GUIDE.md)。

## 本地启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

需先在仓库根目录启动 PostgreSQL：

```bash
docker compose up -d postgres
```

配置 `backend/.env` 中的 `DATABASE_URL`、`JWT_SECRET_KEY` 和 `DASHSCOPE_API_KEY`。真实密钥不得提交到 Git。

## 常用地址

- API 根路径：<http://127.0.0.1:8000/api/v1>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>
- Swagger UI：<http://127.0.0.1:8000/docs>

## 测试

```bash
.venv/bin/pytest -q
```

真实 Embedding/RAG/HTTP 闭环可使用 `scripts/` 下的验收脚本。当前完整后端基线（2026-09-05）为 `298 passed`，以最新本地运行结果为准。

## 上传存储

默认路径是 `backend/data/uploads`，相对路径始终从 `backend` 目录解析，不受启动时工作目录影响。该目录为运行时数据，已被 Git 忽略。
