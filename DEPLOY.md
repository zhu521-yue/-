# 🚀 部署指南

## 服务器要求

- 2核4G 以上（推荐 4核4G）
- Docker + Docker Compose
- 开放端口：80（前端）、8000（API）、3000（Langfuse）

## 部署步骤

### 1. 上传代码到服务器

```bash
# 方式一：Git 拉取
cd /opt
git clone https://github.com/你的用户名/multi-agent-education.git
cd multi-agent-education

# 方式二：本地打包上传
# 本地执行：
tar -czf edu-project.tar.gz --exclude=node_modules --exclude=__pycache__ .
scp edu-project.tar.gz root@你的服务器IP:/opt/

# 服务器执行：
cd /opt && mkdir multi-agent-education && cd multi-agent-education
tar -xzf ../edu-project.tar.gz
```

### 2. 一键部署

```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. 验证

```bash
# 检查容器状态
docker ps

# 检查后端健康
curl http://localhost:8000/health

# 浏览器访问
http://你的服务器IP
```

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | Nginx 托管 + 反代 API |
| 后端 | 8000 | FastAPI |
| Langfuse | 3000 | LLM 可观测性 |
| PostgreSQL | 5432 | 仅内部访问 |
| Redis | 6379 | 仅内部访问 |

## 腾讯云安全组配置

在腾讯云控制台 → 安全组 → 入站规则，添加：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 80 | 0.0.0.0/0 | 前端访问 |
| TCP | 8000 | 0.0.0.0/0 | API（可选） |
| TCP | 3000 | 你的IP/32 | Langfuse（建议限制IP） |

## 常用运维命令

```bash
# 查看所有容器状态
docker ps

# 查看日志
docker compose -f enterprise/docker-compose.yml logs -f app
docker compose -f enterprise/docker-compose.yml logs -f frontend

# 重启单个服务
docker compose -f enterprise/docker-compose.yml restart app

# 更新代码后重新部署
git pull
docker compose -f enterprise/docker-compose.yml up -d --build

# 完全停止
docker compose -f enterprise/docker-compose.yml down

# 清除数据重来（慎用）
docker compose -f enterprise/docker-compose.yml down -v
```
