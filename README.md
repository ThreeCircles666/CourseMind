# CourseMind
CourseMind is a secure AI teaching assistant for educators and students, enabling AI-assisted lesson and assessment creation, personalized tutoring, and private question-bank protection. 课灵是一款面向教师与学生的安全 AI 教学助手，支持智能备课与出题、个性化学习辅导，并通过权限隔离保护教师私有题库。

试图更新


主分支测试

分支测试
分支测试2

# AI 教学辅助平台（YWP Labs）

前后端分离的 Monorepo 项目骨架。

## 1. 项目简介

本仓库是 YWP Labs 「AI 教学辅助平台」的项目骨架，采用前后端分离的
Monorepo 结构：Vue 3 前端 + FastAPI 后端。

## 2. 当前阶段

**仅项目骨架与前后端连通测试。** 尚未实现任何核心业务功能（无登录、无课程管理、
无文件上传、无 RAG、无大模型调用、无数据库业务表等）。目标是获得结构清晰、可运行、
可验证前后端连通性的框架。

## 3. 技术栈

前端：Vue 3 · Vite · TypeScript · Element Plus · Vue Router · Pinia · ESLint（npm）

后端：Python 3.11+ · FastAPI · Pydantic / Pydantic-Settings · Uvicorn ·
SQLAlchemy 2 · Psycopg 3 · Alembic

数据库（未来）：本地 PostgreSQL + pgvector（当前不创建表、不连接）

## 4. 项目目录

```text
项目根目录/
├── frontend/            # Vue 3 前端
│   └── src/
│       ├── api/         # 统一的接口封装（client.ts, health.ts）
│       ├── router/
│       ├── stores/
│       └── views/
├── backend/             # FastAPI 后端
│   ├── app/
│   │   ├── api/         # router.py + routes/health.py
│   │   ├── core/        # config.py（Pydantic Settings）
│   │   ├── schemas/     # 响应模型
│   │   └── main.py
│   ├── tests/
│   └── alembic/         # 迁移框架（当前无迁移）
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .env.example
└── README.md
```

## 5. 前置软件要求

- Node.js 18+ 与 npm
- Python 3.11+
- Git
- （可选，未来才需要）PostgreSQL —— **运行连通测试不需要它**

## 6. 前端安装与启动

```bash
cd frontend
npm install
cp .env.example .env        # macOS / Linux
# Windows PowerShell: Copy-Item .env.example .env
npm run dev
```

前端默认运行在 http://localhost:5173

其他脚本：

```bash
npm run type-check   # TypeScript 类型检查
npm run lint         # ESLint 检查
npm run build        # 生产构建
```

## 7. 后端安装与启动

```bash
cd backend
# 见下方虚拟环境命令，激活后：
pip install -e ".[dev]"
cp .env.example .env        # macOS / Linux
# Windows PowerShell: Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

后端默认运行在 http://127.0.0.1:8000

## 8. macOS 虚拟环境命令

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

退出：`deactivate`

## 9. Windows PowerShell 虚拟环境命令

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

退出：`deactivate`

> 若 PowerShell 提示脚本被禁用，可执行一次：
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## 10. 前后端连通测试方法

1. 先启动后端（端口 8000）。
2. 再启动前端（端口 5173）。
3. 打开 http://localhost:5173 ，首页会自动请求后端健康检查接口。
4. 成功时显示：

   ```text
   后端连接成功
   Service: courseguard-api
   Status: ok
   Version: 0.1.0
   ```

5. 点击「重新测试后端连接」可手动复测。
6. 停止后端后再点击复测，页面会显示「后端连接失败」并给出排查提示，页面不会崩溃。

## 11. 后端 Swagger 地址

http://127.0.0.1:8000/docs

## 12. 前端地址

http://localhost:5173

## 13. 健康检查地址

http://127.0.0.1:8000/api/v1/health

返回：

```json
{ "status": "ok", "service": "courseguard-api", "version": "0.1.0" }
```

## 14. 环境变量配置方法

仓库提供三个示例文件（均已提交，且不含真实密钥）：

- `.env.example`（根，说明共享/默认值）
- `frontend/.env.example` → 复制为 `frontend/.env`
- `backend/.env.example` → 复制为 `backend/.env`

关键变量：

- 前端 `VITE_API_BASE_URL`：后端基地址，默认 `http://127.0.0.1:8000`
- 后端 `CORS_ORIGINS`：允许的前端来源（逗号分隔）
- 后端 `DATABASE_URL`：未来使用，当前不会在启动时连接

真实 `.env` 已被 `.gitignore` 忽略，请勿提交真实密钥或数据库密码。

## 15. 常见错误处理

- **前端显示「后端连接失败」**：确认后端已在 8000 端口运行，接口路径为
  `/api/v1/health`。
- **浏览器控制台出现 CORS 错误**：确认后端 `CORS_ORIGINS` 包含当前前端来源
  （`http://localhost:5173` 与 `http://127.0.0.1:5173`）。注意 `localhost` 与
  `127.0.0.1` 属于不同来源。
- **`npm run dev` 端口被占用**：关闭占用 5173 的进程，或修改 `vite.config.ts` 端口。
- **PowerShell 无法激活虚拟环境**：见第 9 节的执行策略说明。
- **`uvicorn` 命令找不到**：确认已激活虚拟环境并完成 `pip install -e ".[dev]"`。
- **连接数据库报错**：当前骨架不需要数据库，健康检查不依赖它；无需为连通测试启动
  PostgreSQL。

## 16. 关于业务功能

**当前版本不包含任何业务功能。** 仅提供可运行的前后端骨架与健康检查连通测试，
用于后续在此基础上继续开发。
