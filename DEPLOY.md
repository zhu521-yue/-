# 🚀 部署指南

## 当前部署状态

- **服务器**：腾讯云 4核3.6G OpenCloudOS 9.4
- **访问地址**：http://122.51.6.139
- **后端 API**：http://122.51.6.139:8000
- **Langfuse**：http://122.51.6.139:3000
- **项目路径**：/opt/multi-agent-education

## 服务器要求

- 2核4G 以上（推荐 4核4G）
- Docker + Docker Compose
- 开放端口：80（前端）、8000（API）、3000（Langfuse）

## 部署步骤

### 1. 上传代码到服务器

```bash
# Git 拉取
cd /opt
git clone https://github.com/zhu521-yue/-.git multi-agent-education
cd multi-agent-education
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

| 服务 | 端口 | 容器名 | 说明 |
|------|------|--------|------|
| 前端 | 80 | edu_frontend | Nginx 托管 + 反代 API |
| 后端 | 8000 | edu_app | FastAPI |
| Langfuse | 3000 | edu_langfuse | LLM 可观测性 |
| PostgreSQL | 5432 | edu_postgres | 仅内部访问 |
| Redis | 6379 | edu_redis | 仅内部访问 |

## 腾讯云安全组配置

在腾讯云控制台 → 安全组 → 入站规则，添加：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 80 | 0.0.0.0/0 | 前端访问 |
| TCP | 8000 | 0.0.0.0/0 | API（可选） |
| TCP | 3000 | 你的IP/32 | Langfuse（建议限制IP） |

## 踩坑记录

首次部署遇到的问题及解决方案：

| 问题 | 原因 | 解决 |
|------|------|------|
| apt-get 安装极慢（10分钟+） | Debian 官方源从国内访问慢 | Dockerfile 加 `sed` 换清华源 |
| 数据库表不存在 | 没有自动建表逻辑 | init.sql 挂载到 PG 初始化目录 |
| `No module named 'langfuse.decorators'` | langfuse v4 移除了该模块 | 锁定 `langfuse==2.36.2` |
| LLM 返回 HTML 而非 JSON | GPT_BASE_URL 缺少 `/v1` | 新版 openai SDK 不自动拼接 |
| `'str' object has no attribute 'choices'` | openai v2 不兼容第三方网关 | 锁定 `openai>=1.0.0,<2.0.0` |
| `@observe` 装饰器报错 | Langfuse 认证失败时破坏返回值 | 注释掉装饰器 |
| docker restart 后 env 不变 | restart 不重读 env_file | 用 `docker compose up -d` 重建 |
| 内存不够装 sentence_transformers | 3.6G 内存限制 | 部署版不装，Vector RAG 禁用 |

## 常用运维命令

```bash
# 查看所有容器状态
docker ps

# 查看日志
docker compose -f enterprise/docker-compose.yml logs -f app
docker compose -f enterprise/docker-compose.yml logs -f frontend

# 重启单个服务（注意：改了 env_file 要用 up 不要用 restart）
docker compose -f enterprise/docker-compose.yml up -d app

# 重新构建后端（改了代码或依赖后）
docker compose -f enterprise/docker-compose.yml up -d --build app

# 更新代码后重新部署
git pull
docker compose -f enterprise/docker-compose.yml up -d --build

# 完全停止
docker compose -f enterprise/docker-compose.yml down

# 清除数据重来（慎用）
docker compose -f enterprise/docker-compose.yml down -v
```

## 项目进度

```
Phase 1 ████████████████████ 100%  基础骨架
Phase 2 ████████████████████ 100%  核心智能
Phase 3 ████████████████████ 100%  数据层
Phase 4 ████████████████████ 100%  Hybrid RAG
Phase 5 ████████████████████ 100%  可观测性与部署
Agent   ████████████████████ 100%  5个 Worker Agents
题库    ████████████████████ 100%  题库 + 自动判题
前端    ████████████████████ 100%  可爱风格 + 背景图轮播
部署    ████████████████████ 100%  腾讯云 Docker 全容器化
```

### 可选优化（锦上添花）

- [ ] CI/CD（GitHub Actions）— 自动构建测试部署
- [ ] Langfuse 修复 — 本地容器需创建新 API Key
- [ ] Vector RAG — 需要更大内存服务器
