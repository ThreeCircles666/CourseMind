# Qwen 大模型接入使用说明

## 快速开始

### 1. 确认环境变量

确保 `DASHSCOPE_API_KEY` 已设置：

```bash
# 检查是否已设置
echo $DASHSCOPE_API_KEY

# 如果未设置，在 ~/.zshrc 或 ~/.bash_profile 中添加：
export DASHSCOPE_API_KEY="your_actual_api_key_here"

# 重新加载配置
source ~/.zshrc  # 或 source ~/.bash_profile
```

### 2. 安装后端依赖

```bash
cd backend

# 创建虚拟环境（如果尚未创建）
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖（包括 httpx）
pip install -e ".[dev]"
```

### 3. 启动后端服务器

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

启动成功后，访问 http://127.0.0.1:8000/docs 查看 API 文档。

### 4. 启动前端（新终端）

```bash
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 运行。

### 5. 测试聊天功能

1. 打开浏览器访问 http://localhost:5173
2. 点击"进入聊天界面"按钮
3. 在输入框中输入消息，例如："你好，请介绍一下你自己"
4. 点击"发送"或按 Ctrl/Command + Enter
5. 观察 AI 助手的流式回复

## 测试 Qwen 连接（独立测试）

在启动完整服务器之前，可以先测试 Qwen API 连接：

```bash
cd backend
source .venv/bin/activate
python3 test_qwen_quick.py
```

此脚本会：
- 检查 API Key 配置
- 发送测试消息到 `qwen3.8-flash` 模型
- 显示流式响应
- 报告错误（如果有）

## API 端点

### 流式聊天

**端点**: `POST /api/v1/chat/stream`

**请求体**:
```json
{
  "message": "你好，请介绍一下你自己"
}
```

**响应**: SSE (Server-Sent Events) 流

**事件格式**:
```
data: {"type":"content","content":"我","error":""}
data: {"type":"content","content":"是","error":""}
...
data: {"type":"done","content":"","error":""}
```

### 使用 curl 测试

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}' \
  --no-buffer
```

## 常见问题

### Q: 显示"API key not configured"

**解决方法**:
1. 确认环境变量已设置：`echo $DASHSCOPE_API_KEY`
2. 重启终端或重新加载配置文件
3. 确认 uvicorn 进程能继承环境变量

### Q: 收到 404 或"模型不存在"错误

**可能原因**:
- 模型 ID `qwen3.8-flash` 不存在或账号无权限访问
- 账号未开通百炼服务

**解决方法**:
1. 访问 [阿里云百炼控制台](https://dashscope.console.aliyun.com/)
2. 查看"模型广场"获取可用模型列表
3. 确认账号已开通模型访问权限
4. 如需更换模型，修改 `backend/app/api/routes/chat.py` 中的 `model` 参数

### Q: 前端显示"后端连接失败"

**解决方法**:
1. 确认后端已启动在 8000 端口
2. 检查 CORS 配置（`backend/.env` 中的 `CORS_ORIGINS`）
3. 确认防火墙未阻止连接

### Q: 流式输出中断或不完整

**可能原因**:
- 网络超时
- API 限流
- 模型生成被中断

**解决方法**:
- 检查网络连接
- 查看浏览器控制台和后端日志
- 确认 API 配额未超限

## 运行测试

### 后端单元测试

```bash
cd backend
source .venv/bin/activate
pytest tests/test_chat.py -v
```

### 手动连通性测试

```bash
cd backend
source .venv/bin/activate
pytest tests/manual_test_qwen.py -v -s
```

### 前端类型检查

```bash
cd frontend
npm run type-check
```

### 前端 Lint 检查

```bash
cd frontend
npm run lint
```

## 安全提醒

- ❌ 不要将 `DASHSCOPE_API_KEY` 写入源码
- ❌ 不要提交 `.env` 文件到 Git
- ✅ 仅在后端使用 API Key
- ✅ 前端通过后端代理访问 DashScope

## 项目结构

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py       # 聊天路由
│   │   │   └── health.py
│   │   └── router.py
│   ├── core/
│   │   └── config.py         # 配置管理（包含 API Key）
│   ├── schemas/
│   │   └── chat.py           # 聊天数据模型
│   └── services/
│       └── qwen.py           # Qwen 服务层
└── tests/
    ├── test_chat.py          # 单元测试
    └── manual_test_qwen.py   # 手动测试

frontend/
├── src/
│   ├── api/
│   │   └── chat.ts           # 聊天 API 封装
│   ├── composables/
│   │   └── useStreamChat.ts  # 流式聊天逻辑
│   ├── views/
│   │   ├── ChatView.vue      # 聊天界面
│   │   └── HomeView.vue
│   └── router/
│       └── index.ts
```

## 下一步

完成基础功能测试后，可以考虑：
1. 添加多轮对话支持
2. 实现对话历史持久化
3. 支持多模型切换
4. 添加 Token 消耗统计
5. 优化 UI/UX
