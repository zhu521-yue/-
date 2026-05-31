# 多Agent智能教育系统 — 项目文档

## 项目概述

基于 LangGraph 的多 Agent 智能教育与个性化学习系统，面向面试展示的企业级项目。

核心架构：LangGraph 编排 + 5 个 Worker Agent + 事件驱动 + 多模型路由

---

## 当前进度总览

```
Phase 1  ████████████████████ 100%  基础骨架
Phase 2  ████████████████████ 100%  核心智能
Phase 3  ████████████████████ 100%  数据层
Phase 4  ████████████████████ 100%  Hybrid RAG
Phase 5  ████████████████░░░░  80%  可观测性与部署（Langfuse+OTel done，云端部署进行中）
Agent    ████████████████████ 100%  Worker Agents
题库     ████████████████████ 100%  题库 + 自动判题
前端     ████████████████████ 100%  React 前端适配
联调     ████████████████████ 100%  前后端联调通过
SM-2     ████████████████████ 100%  间隔重复接入
多模型   ████████████████████ 100%  DeepSeek + GPT 路由
VecRAG   ████████████████████ 100%  启动时自动初始化
投影     ████████████████████ 100%  Projection Worker 后台任务
评估     ████████████████████ 100%  Evaluator 增强
部署     ██░░░░░░░░░░░░░░░░░░  10%  服务器已购买，待部署
```

---

## 已完成功能

### 1. LangGraph 图编排
- Router → Planner → Coordinator → Evaluator 四节点图
- 条件路由：intent 分类（learn/chat）
- Plan-Execute-Evaluate 循环 + 冷却期（retry_count >= 2 强制 pass）

### 2. 五个 Worker Agent
| Agent | 驱动方式 | 职责 |
|-------|----------|------|
| AssessmentAgent | 纯算法 | BKT 更新 + SM-2 + 状态机触发 + 评估报告 |
| TutorAgent | GPT + RAG | 苏格拉底式教学内容生成 |
| HintAgent | GPT + RAG | 三级提示（元认知→脚手架→直接） |
| CurriculumAgent | 纯算法 | 知识图谱 + SM-2 复习推荐 |
| EngagementAgent | 规则 + GPT | 情绪干预（时间维度 + FSM 状态） |

### 3. Coordinator 调度器
- 先调 EngagementAgent 获取 suggested_action
- 根据 action 路由到对应 Worker（continue→Tutor, hint→Hint, advance→Curriculum, break→直接返回）

### 4. 核心算法
- **BKT（贝叶斯知识追踪）**：P(L|obs) 贝叶斯更新 + 学习转移
- **SM-2（间隔重复）**：mastery→quality 映射，动态复习间隔
- **知识图谱 DAG**：拓扑排序、前置知识检查、学习路径规划

### 5. 双状态机
- **SessionFSM**：ONBOARDING → LEARNING → PRACTICING → REVIEWING → BREAK
- **EngagementFSM**：FOCUSED ⇄ STRUGGLING → FRUSTRATED → NEED_BREAK
- 跨状态机联动：NEED_BREAK 自动触发 force_break

### 6. 多模型路由
- DeepSeek：简单任务（Router、Evaluator、Grader）
- GPT（中转站）：复杂任务（Tutor、Hint、Planner、Engagement）
- Fallback：GPT 未配置或失败时自动降级到 DeepSeek

### 7. 题库 + 自动判题
- 三种题型：选择题（精确匹配）、填空题（数值容差）、解答题（LLM 判题）
- QuestionBank 从 YAML 加载，支持按知识点/难度检索
- Grader 返回 is_correct + score + feedback

### 8. Event Sourcing
- PostgreSQL events 表（append-only 事件记录）
- Redis Stream 实时事件流
- Projection Worker 后台消费 → 更新 student_state 物化视图

### 9. Hybrid RAG
- GraphRAG：从知识图谱获取常见错误、教学类比、关键公式
- Vector RAG：pgvector 语义检索（启动时自动初始化 embeddings）
- hybrid_rag() 合并去重

### 10. 可观测性
- Langfuse：LLM 调用追踪（@observe 装饰器）
- OpenTelemetry：FastAPI 请求链路追踪
- Loguru：结构化日志

### 11. 前端
- React + TypeScript + Vite
- REST API 调用（/chat, /submit, /question）
- 题目展示（选择题 radio、填空题 input、解答题 textarea）
- 判题结果 + mastery 展示 + 评估报告
- 可爱风格 + 背景图 30 秒轮播
- 时间追踪（idle_seconds, session_duration）

### 12. 测试
- 29 个单元测试全部通过
- test_agents.py：AssessmentAgent（8 个）+ EngagementAgent（6 个）
- test_grader.py：QuestionBank（5 个）+ Grader（10 个）

---

## 未完成 / 待做

### 优先级 1：云端部署（进行中）
- [x] 服务器已购买（腾讯云 2 核 3.6G，OpenCloudOS 9.4）
- [ ] 安装 Docker + Docker Compose
- [ ] 编写 Dockerfile（FastAPI app）
- [ ] 编写 Dockerfile（React 前端）
- [ ] 补全 docker-compose.yml（加 app + frontend 服务）
- [ ] 部署上线，公网可访问

### 优先级 2：锦上添花
- [ ] CI/CD（GitHub Actions：push → test → build → deploy）
- [ ] 认证鉴权（JWT token，learner_id 不由前端随意指定）
- [ ] QuestionBank 切 DB（从 YAML 切到 PostgreSQL）
- [ ] 集成测试（完整 /chat + /submit 流程自动化测试）
- [ ] API 文档补充说明

---

## 项目结构

```
enterprise/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI + OTel + startup(embeddings+projection)
│   │   └── routes.py            # /chat + /submit + /question + /backgrounds
│   ├── graph/
│   │   └── education_graph.py   # LangGraph 图（4 节点 + 条件路由）
│   ├── core/
│   │   ├── llm_client.py        # 多模型路由（DeepSeek + GPT + fallback）
│   │   ├── student_manager.py   # 学生状态 + SM-2 复习管理
│   │   ├── grader.py            # 自动判题（3 种题型）
│   │   ├── question_bank.py     # 题库加载器
│   │   ├── learner_model.py     # BKT 贝叶斯知识追踪
│   │   ├── spaced_repetition.py # SM-2 间隔重复
│   │   ├── knowledge_graph.py   # 知识图谱 DAG
│   │   ├── state_machine.py     # 通用 FSM 基类
│   │   ├── session_fsm.py       # 学习阶段状态机
│   │   ├── engagement_fsm.py    # 情绪状态机
│   │   ├── engagement_tracker.py# 情绪触发逻辑
│   │   ├── session_tracker.py   # 学习阶段触发逻辑
│   │   ├── prompt_loader.py     # YAML prompt 分层加载
│   │   └── user_lock.py         # per-user 并发锁
│   ├── agents/
│   │   ├── base_worker.py       # Worker Agent 基类
│   │   ├── assessment_agent.py  # BKT + SM-2 + 状态机 + 报告
│   │   ├── tutor_agent.py       # 苏格拉底教学（GPT + RAG）
│   │   ├── hint_agent.py        # 三级提示（GPT + RAG）
│   │   ├── curriculum_agent.py  # 知识图谱 + SM-2 复习推荐
│   │   └── engagement_agent.py  # 规则路由 + GPT 干预
│   ├── storage/
│   │   ├── event_store.py       # PostgreSQL + Redis Stream
│   │   ├── vector_store.py      # pgvector 向量检索
│   │   ├── rag.py               # Hybrid RAG（Graph + Vector）
│   │   ├── projection_worker.py # 后台投影任务
│   │   ├── init_embeddings.py   # 自动导入 embeddings
│   │   └── schema.sql           # 数据库表定义
│   ├── prompts/                  # 9 个 YAML prompt（分层继承）
│   └── data/
│       ├── math_graph.yaml      # 知识图谱（20 节点）
│       ├── questions.yaml       # 题库（12 道题，3 种题型）
│       └── img/                 # 背景图片（8 张）
├── tests/
│   ├── test_agents.py           # 14 个测试
│   └── test_grader.py           # 15 个测试
├── docker-compose.yml           # PostgreSQL + Redis + Langfuse
├── .env                         # API Keys + DB/Redis + Langfuse
└── requirements.txt
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 编排 | LangGraph (StateGraph) |
| LLM | DeepSeek + GPT (OpenAI 兼容接口) |
| 后端 | FastAPI + asyncio |
| 数据库 | PostgreSQL (pgvector) |
| 缓存/消息 | Redis (Stream) |
| 向量检索 | pgvector + sentence-transformers |
| 可观测性 | Langfuse + OpenTelemetry |
| 前端 | React + TypeScript + Vite |
| 部署 | Docker + Docker Compose |

---

## 关键设计决策

1. **Coordinator 调度模式**：先调 EngagementAgent 获取干预建议，再路由到对应 Worker
2. **Single Writer 原则**：只有 AssessmentAgent 更新 mastery
3. **多模型成本控制**：简单任务 DeepSeek，复杂任务 GPT，失败自动 fallback
4. **时间数据分工**：idle_seconds/session_duration 前端传，recent_accuracy/consecutive_errors 后端算
5. **SM-2 触发时机**：答题后更新 ReviewItem，下次 /chat 时 CurriculumAgent 检查到期复习
6. **Evaluator 冷却期**：retry_count >= 2 强制 pass，避免无限循环
7. **Vector RAG 懒加载**：启动时检查表是否为空，空则自动导入

---

## 部署计划（下一步）

### 服务器信息
- 腾讯云轻量应用服务器
- 2 核 3.6GB 内存
- OpenCloudOS 9.4
- 宝塔面板已安装

### 部署方案
- 不部署 Langfuse（省内存，面试时本地演示）
- 可能禁用 sentence-transformers（省内存，只用 GraphRAG）
- Docker Compose 部署：PostgreSQL + Redis + FastAPI + Frontend

### 待确认
- Docker 是否已安装
- 是否需要域名
- 防火墙端口开放（8000, 5173）
