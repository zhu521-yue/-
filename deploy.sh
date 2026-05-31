#!/bin/bash
# ============================================
# 多Agent智能教育系统 - 一键部署脚本
# 适用于：腾讯云 OpenCloudOS / CentOS / Ubuntu
# ============================================

set -e

echo "🎓 多Agent智能教育系统 - 部署开始"
echo "=================================="

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker 未安装，开始安装...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请手动安装"
    exit 1
fi

echo -e "${GREEN}✅ Docker 环境就绪${NC}"

# 进入项目目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "📦 构建并启动服务..."
echo "---"

# 停止旧容器（如果有）
docker compose -f enterprise/docker-compose.yml down 2>/dev/null || true

# 构建并启动
docker compose -f enterprise/docker-compose.yml up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo ""
echo "🔍 健康检查..."

if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo -e "${GREEN}✅ 后端 API 正常 (端口 8000)${NC}"
else
    echo -e "${YELLOW}⚠️  后端 API 还在启动中，请稍后检查${NC}"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:80 | grep -q "200"; then
    echo -e "${GREEN}✅ 前端页面正常 (端口 80)${NC}"
else
    echo -e "${YELLOW}⚠️  前端还在启动中，请稍后检查${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "访问地址："
echo "  🌐 前端页面: http://<你的服务器IP>"
echo "  🔌 后端 API: http://<你的服务器IP>:8000"
echo "  📊 Langfuse:  http://<你的服务器IP>:3000"
echo ""
echo "常用命令："
echo "  查看日志: docker compose -f enterprise/docker-compose.yml logs -f"
echo "  重启服务: docker compose -f enterprise/docker-compose.yml restart"
echo "  停止服务: docker compose -f enterprise/docker-compose.yml down"
echo ""
