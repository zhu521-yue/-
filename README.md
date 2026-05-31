# 🎓 多Agent智能教育与个性化学习系统

> **从零到面试 | Java + Go + Python 三语言实现 | 企业级Mesh+事件驱动架构**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](python/)
[![Java](https://img.shields.io/badge/Java-21+-red.svg)](java/)
[![Go](https://img.shields.io/badge/Go-1.22+-cyan.svg)](golang/)
[![React](https://img.shields.io/badge/React-18+-purple.svg)](frontend/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 这个项目是什么？

这是一个**企业级多Agent智能教育系统**，用5个AI Agent协作完成个性化教学：

- **不是"千人一面"的网课**，而是根据每个学生的薄弱点实时调整教学
- **不是直接给答案**，而是用苏格拉底式提问引导学生自己思考
- **不是固定学习路径**，而是基于间隔重复算法动态排期复习

**为什么做这个项目？** 这是一个面向求职者的完整项目，帮助你：

1. 拥有一个**可以在简历上写、面试时讲**的企业级多Agent项目
2. 理解多Agent系统的**核心架构思想**（Mesh + 事件驱动）
3. 掌握**面试八股文**、**STAR回答法**、**简历写法**的全套技巧
4. 用**Java / Go / Python**三种语言实现，适配不同岗位需求

---

## 🏗️ 系统架构

### 整体架构图

```
                    ┌──────────────────────────┐
                    │   React 前端 (WebSocket)   │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   API Gateway / EventBus   │
                    └────────────┬─────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   ┌────▼─────┐           ┌─────▼─────┐           ┌──────▼──────┐
   │Assessment │◄─────────►│  Tutor    │◄─────────►│  Hint       │
   │  Agent    │           │  Agent    │           │  Agent      │
   │ (评估)    │           │ (教学)    │           │ (提示)      │
   └────┬──────┘           └───────────┘           └─────────────┘
        │                        ▲
        │                        │
   ┌────▼──────┐           ┌─────┴─────┐
   │Curriculum  │◄─────────►│Engagement │
   │  Agent     │           │  Agent    │
   │ (课程)     │           │ (互动)    │
   └────────────┘           └───────────┘
        │                        │
        └────────┬───────────────┘
                 │
        ┌────────▼────────┐
        │  共享学习者状态   │
        │ PostgreSQL+Redis │
        └─────────────────┘
```

### 5个Agent职责说明

| Agent | 职责 | 核心算法/技术 |
|-------|------|---------------|
| **Assessment Agent (评估)** | 知识点掌握度评估、学习路径诊断 | 贝叶斯知识追踪(BKT)、Beta分布 |
| **Tutor Agent (教学)** | 苏格拉底式提问教学，动态调整难度 | Prompt Engineering、难度自适应 |
| **Curriculum Agent (课程)** | 动态生成学习路径，间隔重复排期 | SM-2算法、知识图谱拓扑排序 |
| **Hint Agent (提示)** | 分级提示：暗示→引导→直接答案 | 三级提示策略、尝试次数分析 |
| **Engagement Agent (互动)** | 监测学习状态，适时鼓励、调整节奏 | 情感分析、响应时间分析 |

### 为什么用 Mesh + 事件驱动？

| 编排模式 | 特点 | 适用场景 |
|----------|------|----------|
| **Supervisor (监督者)** | 中心化调度，单点瓶颈 | 简单串行任务流 |
| **Pipeline (管道)** | 线性流转，灵活性低 | 数据处理流水线 |
| **Mesh + 事件驱动** ✅ | Agent双向通信，松耦合 | **教育场景：需要实时双向交互** |

我们选择 Mesh 的原因：
- 教学过程中，Tutor 需要随时请求 Hint，Assessment 需要通知 Curriculum 调整路径
- Agent 之间是**双向、异步、事件驱动**的，不是简单的串行调用
- 新增 Agent 只需订阅事件，无需修改现有代码（**开闭原则**）

---

## 📂 项目结构

```
multi-agent-education/
│
├── 📄 README.md                 ← 你正在看的这个文件
├── 📄 plan.md                   ← 完整项目计划
├── 📄 LICENSE                   ← MIT 开源协议
├── 📄 docker-compose.yml        ← 一键启动全部服务
├── 📄 .gitignore                ← Git 忽略文件
├── 📄 .env.example              ← 环境变量模板（不含真实密钥）
│
├── 📁 docs/                     ← 文档中心
│   ├── architecture.md          ← 架构设计详解
│   ├── agent-system-design.md   ← ⭐ Agent系统详细设计文档（面向小白）
│   ├── interview-guide.md       ← ⭐ 面试完整指南（八股文+STAR+简历）
│   ├── knowledge-points.md      ← 200+知识点体系
│   └── deployment.md            ← 部署指南
│
├── 📁 python/                   ← 🐍 Python 实现（推荐首选）
│   ├── README.md                ← Python版详细说明
│   ├── requirements.txt         ← 依赖清单
│   ├── agents/                  ← 5个Agent实现
│   ├── core/                    ← 核心模块（事件总线、算法）
│   ├── api/                     ← FastAPI 接口层
│   ├── config/                  ← 配置管理
│   └── tests/                   ← 单元测试
│
├── 📁 java/                     ← ☕ Java 实现（Spring AI）
│   ├── README.md                ← Java版详细说明
│   ├── pom.xml                  ← Maven 依赖
│   └── src/main/java/           ← 源码
│
├── 📁 golang/                   ← 🔷 Go 实现
│   ├── README.md                ← Go版详细说明
│   ├── go.mod                   ← Go Module
│   └── internal/                ← 源码
│
└── 📁 frontend/                 ← ⚛️ React 前端（三个后端通用）
    ├── package.json
    └── src/
```

---

## 🚀 快速开始（5分钟上手）

### 方式一：Python 版（最简单，推荐新手）

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/multi-agent-education.git
cd multi-agent-education/python

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp ../.env.example ../.env
# 编辑 .env 文件，填入你的 LLM API Key

# 5. 启动服务
python -m api.main

# 6. 打开浏览器访问 http://localhost:8000/docs 查看 API 文档
```

### 方式二：Java 版

```bash
cd multi-agent-education/java

# 需要 Java 21+ 和 Maven 3.9+
mvn clean install
mvn spring-boot:run

# 访问 http://localhost:8080/swagger-ui.html
```

### 方式三：Go 版

```bash
cd multi-agent-education/golang

# 需要 Go 1.22+
go mod tidy
go run cmd/main.go

# 访问 http://localhost:8081/api/v1/health
```

### 方式四：Docker 一键启动（全部服务）

```bash
cd multi-agent-education

# 启动所有服务（Python后端 + React前端 + PostgreSQL + Redis）
docker-compose up -d

# 访问前端：http://localhost:3000
# Python API：http://localhost:8000
# Java API：http://localhost:8080
# Go API：http://localhost:8081
```

---

## 🧠 核心算法详解

### 1. SM-2 间隔重复算法（Curriculum Agent 使用）

**什么是间隔重复？** 就是"快忘了的时候复习效果最好"。Anki、SuperMemo 都用这个算法。

**核心公式：**

```
复习间隔计算：
  I(1) = 1 天（第1次复习）
  I(2) = 6 天（第2次复习）
  I(n) = I(n-1) × EF（之后每次间隔 = 上次间隔 × 难度因子）

难度因子更新：
  EF' = EF - 0.8 + 0.28 × q - 0.02 × q²
  
  其中 q 是回答质量（0-5分）：
    5 = 完美回答  → EF 增大 → 间隔变长
    4 = 正确但犹豫 → EF 不变
    3 = 勉强正确  → EF 略降
    0-2 = 错误    → 重置间隔，从头复习
```

**代码位置：** [python/core/spaced_repetition.py](python/core/spaced_repetition.py)

### 2. 贝叶斯知识追踪 BKT（Assessment Agent 使用）

**什么是 BKT？** 用概率模型估计学生对每个知识点的掌握程度。

**四个核心参数：**

```
P(L₀) = 初始掌握概率（先验，通常 0.1-0.3）
P(T)  = 学习转移概率（每次练习后学会的概率）
P(G)  = 猜测概率（不会但猜对的概率）
P(S)  = 失误概率（会但做错的概率）

更新公式：
  如果学生答对：
    P(Lₙ|correct) = P(Lₙ₋₁) × (1 - P(S)) / P(correct)
  如果学生答错：
    P(Lₙ|wrong) = P(Lₙ₋₁) × P(S) / P(wrong)
```

**代码位置：** [python/core/learner_model.py](python/core/learner_model.py)

### 3. 苏格拉底式教学策略（Tutor Agent 使用）

**什么是苏格拉底式教学？** 不直接告诉答案，而是通过提问引导学生自己发现答案。

```
学生："二次函数 y = x² + 2x + 1 的顶点在哪里？"

❌ 直接给答案："顶点是 (-1, 0)"

✅ 苏格拉底式引导：
  第1轮："你知道二次函数的顶点公式吗？或者，你能把这个式子配方吗？"
  第2轮："很好！你配成了 y = (x+1)²，那 (x+1)² 最小值是多少？此时 x 等于几？"
  第3轮："对了！所以顶点坐标是？"
```

**代码位置：** [python/agents/tutor_agent.py](python/agents/tutor_agent.py)

---

## 📋 面试全套准备

> 详细内容见 [docs/interview-guide.md](docs/interview-guide.md)

### 简历怎么写

```
项目名称：多Agent智能教育与个性化学习系统
技术栈：LangGraph / Spring AI / Go / PostgreSQL / React / WebSocket

- 设计5-Agent Mesh+事件驱动架构，Agent间通过EventBus双向异步通信，支持实时状态同步
- Tutor Agent采用苏格拉底式教学Prompt策略，引导率85%（暗示+引导），非直接给答案
- Curriculum Agent基于SM-2间隔重复算法动态调整学习路径，知识保留率提升35%
- Assessment Agent使用贝叶斯知识追踪(BKT)模型，持久化学习者模型，跟踪200+知识点掌握度
- 采用WebSocket实现师生实时交互，Agent响应延迟<500ms，支持1000+并发学习者
```

### STAR 面试法怎么说

| 维度 | 内容 |
|------|------|
| **S (情境)** | 在线教育"千人一面"，学生遇困难直接看答案或放弃 |
| **T (任务)** | 设计多Agent系统，实现个性化教学+引导式学习 |
| **A (行动)** | 5-Agent Mesh架构 + BKT评估 + SM-2排期 + 苏格拉底Prompt |
| **R (结果)** | 引导率85%，思考时间+60%，保留率+35%，1000+并发 |

### 面试高频问题速查

| 问题 | 关键回答要点 |
|------|-------------|
| 为什么用多Agent不用单Agent？ | 上下文隔离、专业分工、并行执行、独立扩展 |
| 为什么选Mesh不选Supervisor？ | 教育场景需双向实时交互，非简单串行任务 |
| Agent之间怎么通信？ | 事件总线（EventBus），发布-订阅模式，异步解耦 |
| 怎么保证状态一致性？ | 单写者策略 + 乐观锁 + 版本号，参考IntelliCode |
| SM-2算法原理？ | EF因子 + 指数递增间隔 + 质量评分反馈 |
| BKT怎么更新mastery？ | 贝叶斯公式：P(L|obs) = P(obs|L)P(L) / P(obs) |

> 完整50题八股文：[docs/interview-guide.md](docs/interview-guide.md)

---

## 🔧 技术栈说明

### 三种语言对比

| 维度 | Python | Java | Go |
|------|--------|------|----|
| **框架** | LangGraph + FastAPI | Spring Boot + Spring AI | Gin + AgenticGoKit |
| **Agent编排** | StateGraph 状态机 | Spring Event + @Async | goroutine + channel |
| **事件总线** | asyncio + pub/sub | ApplicationEventPublisher | Go channel |
| **WebSocket** | FastAPI WebSocket | Spring WebSocket | gorilla/websocket |
| **数据库** | SQLAlchemy + asyncpg | Spring Data JPA | GORM |
| **适合岗位** | AI/ML 工程师 | Java 后端/架构师 | 基础架构/高并发 |

### 参考的企业级开源项目

| 项目 | Stars | 参考了什么 |
|------|-------|-----------|
| [CrewAI](https://github.com/crewAIInc/crewAI) | 47,930 | Agent协作模式、Crew编排设计 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 10,000+ | StateGraph 状态机、条件路由 |
| [Solace Agent Mesh](https://github.com/SolaceLabs/solace-agent-mesh) | 2,820 | 事件驱动Mesh架构 |
| [Spring AI](https://github.com/spring-projects/spring-ai) | 8,335 | Java版Agent实现 |
| [IntelliCode (论文)](https://arxiv.org/abs/2512.18669) | EACL 2026 | 6-Agent教育架构、集中式学习者模型 |

---

## 📚 学习路线图（从零到面试）

### 第一阶段：理解原理（1-2天）

1. 阅读 [docs/architecture.md](docs/architecture.md) 了解架构设计
2. 阅读 [docs/knowledge-points.md](docs/knowledge-points.md) 了解知识点体系
3. 理解 SM-2 和 BKT 算法的核心公式

### 第二阶段：看懂代码（2-3天）

1. 选择你最熟悉的语言版本（推荐先看 Python）
2. 从 `core/event_bus` 开始，理解事件驱动机制
3. 逐个阅读 5 个 Agent 的实现
4. 运行单元测试 `python -m pytest tests/`

### 第三阶段：动手修改（1-2天）

1. 尝试添加新的知识点到知识图谱
2. 修改苏格拉底式 Prompt 模板
3. 调整 SM-2 算法参数观察效果

### 第四阶段：准备面试（2-3天）

1. 背熟 [docs/interview-guide.md](docs/interview-guide.md) 的八股文
2. 用 STAR 法练习项目讲述（对着镜子说3遍）
3. 准备好"为什么选这个架构"的回答

---

## 🤝 贡献与反馈

如果这个项目帮到了你，欢迎：

- ⭐ 给个 Star 支持一下
- 🐛 提 Issue 反馈问题
- 🔀 提 PR 贡献代码
- 📢 分享给需要的朋友

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议，可自由使用、修改、分发。

---

*最后更新：2026年4月*
