# CourseMind Docker 快速启动指南

## 一键启动

```bash
# 启动所有服务（首次运行会自动构建镜像）
docker compose up --build

# 后台运行
docker compose up -d --build
```

## 访问服务

- **前端**: http://127.0.0.1:5174
- **后端 API**: http://127.0.0.1:8000
- **API 文档**: http://127.0.0.1:8000/docs
- **健康检查**: http://127.0.0.1:8000/api/v1/health
- **数据库**: `localhost:5432` (用户: coursemind, 密码: coursemind_dev)

## 快速测试 Demo 流程

1. 访问前端: http://127.0.0.1:5174
2. 注册新账号:
   - 用户名: `demo_user`
   - 昵称: `Demo`
   - 密码: `demo123456`
3. 登录后进入学习画布: http://127.0.0.1:5174/canvas
4. 点击 "加载演示画布"
5. 点击任意卡片查看详情
6. 点击 "解释得更简单" 和 "举一个例子"
7. 观察子卡片生成和易忘点标记

## 服务说明

### PostgreSQL + pgvector
- 自动启动并启用 pgvector 扩展
- 数据持久化在 Docker volume
- 健康检查确保服务就绪

### Backend (FastAPI)
- 自动等待数据库就绪
- 自动执行数据库迁移 (`alembic upgrade head`)
- 暴露 8000 端口
- 上传文件存储在 `backend/data/uploads`

### Frontend (Vue 3 + Vite)
- 开发服务器模式（支持热重载）
- 暴露 5174 端口
- 自动连接到后端 API

## 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除卷（清空数据库）
docker compose down -v
```

## 重新构建

```bash
# 重新构建所有镜像
docker compose build --no-cache

# 重新构建并启动
docker compose up --build
```

## 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

## 环境变量配置

### 后端环境变量

默认配置已在 `docker-compose.yml` 中设置，适合本地 Demo。

**可选配置**：

如果需要使用真实 AI 功能（RAG 问答），可以设置 DashScope API Key：

```bash
# 方式1: 直接在 docker-compose.yml 中设置
environment:
  DASHSCOPE_API_KEY: your-api-key-here

# 方式2: 使用 .env 文件
echo "DASHSCOPE_API_KEY=your-api-key-here" > .env
docker compose --env-file .env up
```

**注意**: 
- 没有 API Key 时，登录、注册、文档上传、演示画布功能仍然可用
- 只有真实 RAG 问答和生成画布需要 API Key
- 演示画布使用 Fallback 数据，无需 API Key

### 前端环境变量

默认 API Base URL 留空，前端会通过同源 `/api` 代理访问后端，避免浏览器跨域问题。

如需修改，在 `frontend/.env` 中设置：
```
VITE_API_BASE_URL=http://your-backend-url:8000
```

## 常见问题

### 1. 端口冲突

如果 5432、8000 或 5174 端口被占用：

```yaml
# 修改 docker-compose.yml 中的端口映射
services:
  postgres:
    ports:
      - "15432:5432"  # 使用 15432 代替 5432
  
  backend:
    ports:
      - "18000:8000"  # 使用 18000 代替 8000
  
  frontend:
    ports:
      - "15174:5174"  # 使用 15174 代替 5174
```

### 2. 数据库迁移失败

```bash
# 进入后端容器手动运行
docker compose exec backend alembic upgrade head
```

### 3. 前端无法连接后端

默认 Docker 配置会把前端 `/api` 代理到后端容器。若自行修改过 `frontend/.env`，请先清空 `VITE_API_BASE_URL`，或确认它指向可访问的后端地址。

### 4. 重置所有数据

```bash
# 停止并删除所有容器和卷
docker compose down -v

# 重新启动
docker compose up --build
```

## 开发模式

Docker Compose 已配置为开发友好模式：

- **前端**: 源代码挂载，支持热重载
- **后端**: 上传目录持久化
- **数据库**: 数据持久化

可以直接编辑代码，更改会自动生效（前端立即，后端需重启）。

## 生产部署

此配置为本地开发和 Hackathon Demo 设计。

生产环境建议：
- 使用环境变量或密钥管理工具
- 替换为生产级密钥
- 使用 Nginx 代理
- 构建前端静态文件
- 配置 HTTPS
- 设置合适的资源限制

## 最小系统要求

- Docker: 20.10+
- Docker Compose: 2.0+
- 可用内存: 4GB+
- 可用磁盘: 10GB+

## 技术栈

- **数据库**: PostgreSQL 17 + pgvector
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + Alembic
- **前端**: Node 20 + Vue 3 + Vite + TypeScript + Element Plus
- **容器**: Docker + Docker Compose
