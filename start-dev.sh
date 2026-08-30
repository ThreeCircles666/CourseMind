#!/bin/bash
# CourseMind 开发环境启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== CourseMind 启动脚本 ==="
echo ""

# 检查环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "⚠️  警告: DASHSCOPE_API_KEY 未设置"
    echo "   聊天功能将无法使用"
    echo "   请在终端中设置: export DASHSCOPE_API_KEY=your-key-here"
    echo ""
else
    echo "✓ DASHSCOPE_API_KEY 已配置"
    echo ""
fi

# 启动后端
echo "启动后端服务器 (端口 8000)..."
cd backend

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "安装后端依赖..."
    pip3 install --user fastapi httpx pydantic pydantic-settings uvicorn
fi

# 后台启动 uvicorn
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "后端进程 PID: $BACKEND_PID"

cd ..

# 启动前端
echo ""
echo "启动前端开发服务器 (端口 5173)..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "前端进程 PID: $FRONTEND_PID"

cd ..

echo ""
echo "=== 服务已启动 ==="
echo ""
echo "后端 API: http://127.0.0.1:8000"
echo "后端文档: http://127.0.0.1:8000/docs"
echo "前端界面: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待中断信号
trap "echo ''; echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
