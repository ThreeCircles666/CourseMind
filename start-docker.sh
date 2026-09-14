#!/bin/bash

# CourseMind Docker 启动验证脚本

echo "====================================="
echo "CourseMind Docker 启动验证"
echo "====================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否运行
echo "1. 检查 Docker 服务..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 正在运行${NC}"
echo ""

# 检查 Docker Compose 版本
echo "2. 检查 Docker Compose..."
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker Compose 不可用${NC}"
    exit 1
fi
COMPOSE_VERSION=$(docker compose version --short)
echo -e "${GREEN}✓ Docker Compose 版本: ${COMPOSE_VERSION}${NC}"
echo ""

# 检查端口占用
echo "3. 检查端口占用..."
check_port() {
    PORT=$1
    SERVICE=$2
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠ 端口 $PORT ($SERVICE) 已被占用${NC}"
        lsof -Pi :$PORT -sTCP:LISTEN | grep LISTEN
        return 1
    else
        echo -e "${GREEN}✓ 端口 $PORT ($SERVICE) 可用${NC}"
        return 0
    fi
}

ALL_PORTS_FREE=true
check_port 5432 "PostgreSQL" || ALL_PORTS_FREE=false
check_port 8000 "Backend" || ALL_PORTS_FREE=false
check_port 5174 "Frontend" || ALL_PORTS_FREE=false
echo ""

if [ "$ALL_PORTS_FREE" = false ]; then
    echo -e "${YELLOW}建议: 停止占用端口的服务，或修改 docker-compose.yml 中的端口映射${NC}"
    echo ""
fi

# 启动服务
echo "4. 启动 Docker Compose 服务..."
echo -e "${YELLOW}执行: docker compose up --build${NC}"
echo ""

docker compose up --build -d

echo ""
echo "等待服务启动..."
sleep 5
echo ""

# 检查服务状态
echo "5. 检查服务状态..."
docker compose ps
echo ""

# 等待服务就绪
echo "6. 等待服务就绪（最多等待 60 秒）..."
WAIT_TIME=0
MAX_WAIT=60

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -f http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务就绪${NC}"
        break
    fi
    echo "等待后端服务... ($WAIT_TIME/$MAX_WAIT 秒)"
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}✗ 后端服务启动超时${NC}"
    echo "查看日志："
    echo "docker compose logs backend"
    exit 1
fi
echo ""

# 验证各个端点
echo "7. 验证服务端点..."

# 后端健康检查
echo -n "- 后端健康检查... "
if curl -f http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# 前端访问
echo -n "- 前端页面... "
if curl -f http://127.0.0.1:5174 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (可能需要更多时间)${NC}"
fi

# API 文档
echo -n "- API 文档... "
if curl -f http://127.0.0.1:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo ""

# 显示访问信息
echo "====================================="
echo -e "${GREEN}启动完成！${NC}"
echo "====================================="
echo ""
echo "📱 访问地址："
echo "  - 前端: http://127.0.0.1:5174"
echo "  - 后端 API: http://127.0.0.1:8000"
echo "  - API 文档: http://127.0.0.1:8000/docs"
echo ""
echo "🧪 Demo 测试流程："
echo "  1. 访问: http://127.0.0.1:5174"
echo "  2. 注册账号: demo_user / demo123456"
echo "  3. 进入学习画布: http://127.0.0.1:5174/canvas"
echo "  4. 点击「加载演示画布」"
echo "  5. 点击卡片 → 点击「解释得更简单」"
echo "  6. 再次点击「举一个例子」→ 观察易忘点标记"
echo ""
echo "📋 常用命令："
echo "  - 查看日志: docker compose logs -f"
echo "  - 停止服务: docker compose down"
echo "  - 重启服务: docker compose restart"
echo ""
echo "💡 提示："
echo "  - 没有 DashScope API Key 时，演示画布仍可正常使用"
echo "  - 真实 RAG 问答需要配置 API Key"
echo ""
