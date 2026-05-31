# 多Agent智能教育系统 - 企业级架构设计文档

## 1. 项目概述

### 1.1 项目定位

将现有的比赛级多Agent教育系统重构为企业级个人项目，升级架构模式、引入LLM智能、完善基础设施。

### 1.2 核心保留

- BKT（贝叶斯知识追踪）算法
- SM-2 间隔重复算法
- 知识图谱 DAG（扩展关系类型）

### 1.3 核心升级

| 维度 | 当前状态 | 目标状态 |
|------|---------|---------|
| Agent 模式 | 事件驱动 reactive worker | Plan-Execute-Evaluate + ReAct 混合 |
| 智能能力 | if/else + 模板 | LLM 推理 + 多模型路由 |
| 持久化 | 内存 | Event Sourcing + PostgreSQL |
| 可观测性 | 无 | Langfuse + OpenTelemetry |
| 知识检索 | 无 | Hybrid RAG（GraphRAG + Vector） |

---

## 2. 系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────┐    ┌────────────────────────────────────────────┐  │
│  │  React   │───▶│           FastAPI + LangGraph              │  │
│  │ Frontend │    │                                            │  │
│  └──────────┘    │  ┌────────┐                                │  │
│                  │  │ Router │ (DeepSeek) 意图分类 + 模型路由  │  │
│                  │  └───┬────┘                                 │  │
│                  │      │                                      │  │
│                  │  ┌───▼─────┐                                │  │
│                  │  │ Planner │ (GPT-5.5, 关键节点触发)       │  │
│                  │  └───┬─────┘                                │  │
│                  │      │                                      │  │
│                  │  ┌───▼──────────┐                           │  │
│                  │  │ Coordinator  │ 分发任务 / 收集结果       │  │
│                  │  └───┬─────▲────┘                           │  │
│                  │      │     │                                │  │
│                  │      ▼     │ 结果上报                       │  │
│                  │  ┌─────────┴──────────────────────┐        │  │
│                  │  │ Workers (DeepSeek, ReAct 对话)  │        │  │
│                  │  │ Tutor / Hint / Curriculum /     │        │  │
│                  │  │ Assessment / Engagement         │        │  │
│                  │  └────────────────────────────────┘        │  │
│                  │      │                                      │  │
│                  │  ┌───▼──────┐                               │  │
│                  │  │ Evaluate │ (DeepSeek/规则)               │  │
│                  │  └───┬──────┘                               │  │
│                  │      │ 偏离→re-plan（冷却期 3-5 轮）        │  │
│                  │      └──────────▶ Planner                   │  │
│                  └────────────────────┬───────────────────────┘  │
│                                       │                          │
│  ┌──────────┐  ┌─────────────────────┐  ┌──────────┐           │
│  │  Redis   │  │    PostgreSQL       │  │ Langfuse │           │
│  │          │  │    (pgvector)       │  │          │           │
│  │• 会话缓存 │  │• Event Store        │  │• LLM 观测 │           │
│  │• Stream  │  │• 物化视图           │  │• OTel    │           │
│  │• LG state│  │• 向量检索(pgvector) │  │  链路追踪 │           │
│  └──────────┘  │• 图存储(邻接表)     │  └──────────┘           │
│                └─────────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent 架构设计

### 3.1 架构模式：分层混合（中心调度 + Mesh）

**整体思想**：上层中心调度（Planner 做全局策略），下层 Mesh 协作（Worker 间局部协调），中间通过 Coordinator 节点衔接。

**分层通信设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  上层：中心调度（LangGraph 图执行，同步有序）                 │
│                                                             │
│  Router → Planner → Coordinator → Evaluator                 │
│                         │    ▲                              │
│                    分发任务  │ 收集结果                       │
│                         │    │                              │
├─────────────────────────┼────┼──────────────────────────────┤
│  下层：Mesh 协作（Worker 间直接函数调用）                     │
│                         ▼    │                              │
│              ┌──────────────────────────┐                   │
│              │  Tutor  Hint  Curriculum │                   │
│              │  Assessment  Engagement  │                   │
│              │                          │                   │
│              │  Tutor ──调用──▶ Hint    │                   │
│              └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘

EventBus 职责：系统级事件广播（Event Store 写入、前端推送、物化视图投影）
```

**信息流向原则**：
- Planner 拥有全局视野（mastery、session状态、engagement状态）
- Planner 下发**指令**给 Coordinator，不广播状态
- Coordinator 负责分发任务给 Worker、收集结果返回给 Evaluator
- Worker 只知道自己的任务和学生的直接反馈，不感知其他 agent 状态
- Worker 间局部协作通过直接函数调用（如 Tutor→Hint）

**Coordinator 节点职责**：

```python
async def coordinator_node(state):
    plan = state["current_plan"]
    
    # 1. 根据计划决定调用哪些 worker
    tasks = dispatch(plan)
    
    # 2. 并行/串行执行
    results = await asyncio.gather(*[
        execute_worker(task) for task in tasks
    ])
    
    # 3. 聚合结果，统一格式返回给 Evaluator
    return {"execution_results": aggregate(results)}
```

**Coordinator 的价值**：
- Planner 保持简洁：只输出"做什么"，不关心分发和收集
- Worker 保持简洁：只执行单一任务，不关心结果给谁
- 扩展时只改 Coordinator：新增 agent 只需在分发逻辑里加一条路由
- 可观测性集中：一个点看到所有 worker 的输入输出

### 3.2 执行循环：Plan-Execute-Evaluate

**宏观层（Plan-Execute-Evaluate）**：管理教学策略

```
Planner（GPT-5.5）→ Coordinator → Workers → Coordinator → Evaluator（DeepSeek/规则）
  ▲                                                            │
  └──────────────────── 偏离阈值时 re-plan ────────────────────┘
                        （冷却期：3-5 轮交互）
```

**微观层（ReAct）**：Worker 内部的单轮对话

```
Thought: 分析学生当前状态和意图
Action:  调用工具（检索知识、生成回复、更新状态）
Observation: 观察学生反馈
→ 循环直到对话目标达成
```

### 3.2 多模型路由策略

| 场景 | 模型 | 理由 |
|------|------|------|
| 意图分类 | DeepSeek | 分类任务，轻量够用 |
| 模型路由判断 | DeepSeek | 先分类再决定后续用哪个模型 |
| 苏格拉底式引导 | DeepSeek | 有模板约束 |
| 教学计划制定 | GPT-5.5 | 需要深度推理和多步规划 |
| 错误原因分析 | GPT-5.5 | 需要综合多维度信息 |
| Evaluate 偏离判断 | DeepSeek/规则 | 阈值判断为主 |
| 质量检查 fallback | GPT-5.5 | DeepSeek 质量不合格时升级 |

### 3.3 Planning Agent 触发时机

仅在关键节点触发，避免频繁调用 GPT-5.5：
- mastery 发生显著变化（跨越 level 阈值）
- EngagementFSM 状态切换（如进入 FRUSTRATED）
- Evaluate 节点检测到偏离阈值
- 学生主动请求切换学习内容

### 3.5 LangGraph 编排框架

使用 LangGraph 的 StateGraph 实现 agent 编排：
- 节点：Router、Planner、Coordinator、Evaluator
- Coordinator 内部调用 Worker agents（Tutor、Hint、Curriculum、Assessment、Engagement）
- 边：条件路由（基于意图分类、偏离判断）
- 状态：LangGraph 内置 checkpointing，支持中断恢复
- 人工介入：支持 human-in-the-loop（教师可干预教学计划）

### 3.6 EventBus 职责收窄

EventBus 不再负责 agent 间协调，只负责系统级事件广播：

| 通信场景 | 方式 |
|---------|------|
| Planner → Coordinator | LangGraph 图的边 |
| Coordinator → Worker | 直接函数调用 |
| Worker → Worker（执行中协作） | 直接函数调用 |
| 状态变更 → 外部系统（DB投影、前端推送） | EventBus |

---

## 4. 业务状态机

独立于 LangGraph 之外的业务领域模型，约束学生状态的合法转移。

### 4.1 SessionFSM（学习阶段状态机）

```
ONBOARDING → LEARNING → PRACTICING → REVIEWING → BREAK
     ▲           │           │           │          │
     └───────────┴───────────┴───────────┴──────────┘
```

- 驱动者：Curriculum Agent / Planner
- 消费者：Planner（决定教学策略）、Tutor（调整教学风格）

### 4.2 EngagementFSM（情绪状态机）

```
FOCUSED ⇄ STRUGGLING → FRUSTRATED → NEED_BREAK
   ↕
BORED
```

- 驱动者：学生行为数据（答题正确率、响应时间、连续错误数）
- 消费者：Tutor（调整难度）、Hint（调整提示级别）

### 4.3 跨状态机联动

```python
# EngagementFSM 进入 NEED_BREAK → 强制 SessionFSM 转移到 BREAK
engagement_fsm.on_enter("NEED_BREAK", lambda: session_fsm.trigger("force_break"))

# SessionFSM 进入 BREAK → EngagementFSM 重置为 FOCUSED
session_fsm.on_enter("BREAK", lambda: engagement_fsm.trigger("reset"))
```

---

## 5. Prompt 管理

### 5.1 分层继承架构

```
prompts/
├── system_base.yaml          ← 所有 agent 共享（语言、安全、输出格式）
├── edu_base.yaml             ← 教学类 agent（以学生为中心、引导式教学）
├── tutor.yaml                ← Tutor Agent 个性 prompt
├── hint.yaml                 ← Hint Agent 个性 prompt
├── planner.yaml              ← Planning Agent 个性 prompt
├── evaluator.yaml            ← Evaluate Agent 个性 prompt
└── notify_base.yaml          ← 通知类 agent（未来扩展）
```

### 5.2 继承规则

- `system_base.yaml`：全局约束，所有 agent 自动注入
- `edu_base.yaml`：继承 system_base，教学类 agent 共享
- 各 agent YAML：继承 edu_base，定义个性化行为

### 5.3 加载机制

```python
# 新增 agent 只需：
# 1. 创建 new_agent.yaml，声明 inherits: edu_base
# 2. 定义个性 prompt
# 无需修改任何已有文件
```

### 5.4 后续升级路径

当前：YAML 配置文件（git 可追踪）
未来：Prompt Registry（DB 存储 + 版本管理 + A/B 测试 + 热更新）

---

## 6. 持久化架构：Event Sourcing

### 6.1 设计理念

所有状态变更以事件形式不可变追加存储，当前状态通过事件投影计算得出。

### 6.2 架构图

```
Agent 决策
    │
    ▼ 写入
┌─────────────────────────────────────┐
│        Event Store (PostgreSQL)     │
│                                     │
│  event_id | stream_id | type | data │
└──────────────────┬──────────────────┘
                   │
                   │ Redis Stream（异步投影）
                   ▼
┌─────────────────────────────────────┐
│       物化视图 (PostgreSQL)          │
│                                     │
│  • student_current_state            │
│  • daily_progress_summary           │
│  • review_schedule                  │
└─────────────────────────────────────┘
```

### 6.3 异步投影实现

```python
# 事件写入后推入 Redis Stream
async def write_event(event):
    await event_store.append(event)
    await redis.xadd("event_stream", event.dict())
    return event

# 独立 worker 消费 Redis Stream，更新物化视图
async def projection_worker():
    while True:
        events = await redis.xread("event_stream", block=5000)
        for event in events:
            await update_materialized_view(event)
```

### 6.4 Event Sourcing 的价值

- 完整审计轨迹：可回放任意时间点的学生状态
- 教学效果分析：按时间窗口聚合，对比不同策略效果
- Bug 排查：完整重放复现问题
- 数据驱动优化：分析哪种教学路径转化率最高

### 6.5 用户会话恢复策略

用户意外退出（关闭页面、网络断开）后重新登录的数据恢复方案。

**数据分层存储与持久性**：

| 数据 | 存储位置 | 持久性 | 重新登录后 |
|------|---------|--------|-----------|
| 学习历史（所有答题记录） | Event Store (PostgreSQL) | 永久 | 完整保留 |
| 当前 mastery 状态 | 物化视图 (PostgreSQL) | 永久 | 完整保留 |
| SM-2 复习计划 | PostgreSQL | 永久 | 完整保留 |
| 知识图谱进度 | PostgreSQL | 永久 | 完整保留 |
| 状态机状态（SessionFSM/EngagementFSM） | PostgreSQL | 永久 | 可恢复 |
| 当前对话上下文 | Redis (TTL 24h) | 24小时 | 24h内可恢复 |
| LangGraph 执行状态 | PostgreSQL (checkpoint) | 永久 | 可从中断点继续 |

**LangGraph Checkpoint 持久化**：

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(conn_string)
graph = StateGraph(...).compile(checkpointer=checkpointer)
```

LangGraph 执行状态持久化到 PostgreSQL，即使 Redis 对话上下文过期，系统仍能从上次中断的节点继续执行。

**用户重新登录恢复流程**：

```
1. 用户登录
   → 从 PostgreSQL 加载 mastery、学习记录、状态机状态

2. 检查 Redis 是否有未完成的对话上下文
   ├─ 有 → 恢复对话，继续上次的教学
   └─ 无 → 检查 LangGraph checkpoint
        ├─ 有未完成的 plan → 从中断点继续执行
        └─ 无 → 开始新的学习会话

3. 展示恢复提示：
   "欢迎回来！你上次学到了「一元二次方程」，掌握度 65%。要继续上次的学习吗？"
```

**设计原则**：
- 长期状态（学习进度、执行 checkpoint）→ PostgreSQL（永久保存）
- 短期状态（对话上下文、临时计算）→ Redis（TTL 24h）
- 无论何时回来，学习进度永不丢失；对话上下文尽力恢复

---

## 7. Hybrid RAG 架构

### 7.1 双路检索

```
学生输入
    │
    ├──────────────────┬─────────────────────┐
    ▼                  ▼                     │
┌────────────┐  ┌──────────────┐            │
│ Vector RAG │  │  Graph RAG   │            │
│            │  │              │            │
│ query      │  │ 提取实体      │            │
│ → embedding│  │ → 图遍历      │            │
│ → pgvector │  │ → 关联节点    │            │
│ → top-k    │  │ → 结构化上下文│            │
└─────┬──────┘  └──────┬───────┘            │
      │                │                    │
      └────────┬───────┘                    │
               ▼                            │
        合并 + 排序 + 去重                   │
               │                            │
               ▼                            │
        注入 LLM prompt                     │
```

### 7.2 知识图谱扩展

当前知识图谱只有 prerequisites 关系，扩展为：

```
knowledge_node:
  id: "quadratic_eq"
  prerequisites: [factoring, algebraic_expr]
  related_to: [discriminant, vieta_theorem]
  common_errors: ["忘记Δ=0的情况", "配方法符号错误"]
  teaching_analogies: ["抛物线与x轴的交点"]
  difficulty_variants: [easy_id, medium_id, hard_id]
```

### 7.3 GraphRAG 检索策略

| 学生行为 | 图遍历方向 | 检索内容 |
|---------|-----------|---------|
| 答错题 | 沿 prerequisites 回溯 | 前置知识是否牢固 |
| 提问概念 | 沿 related_to 扩展 | 关联概念辅助理解 |
| 需要 hint | 查 common_errors | 针对性提示 |
| 教学生成 | 查 teaching_analogies | 类比解释 |

### 7.4 技术选型

- 向量检索：pgvector（PostgreSQL 扩展）
- 图存储：PostgreSQL 邻接表 + 递归 CTE 查询
- 不引入额外组件，一个 PostgreSQL 承担三重角色

---

## 8. 并发安全与多用户隔离

### 8.1 隔离策略

| 层面 | 隔离方式 |
|------|---------|
| LangGraph | thread_id per user |
| 状态机 | per-user 实例，状态持久化到 DB |
| Redis | key 前缀带 learner_id |
| Event Store | stream_id = learner_id |
| 进程内存 | 不存用户状态，全部外置 |

### 8.2 并发场景分析

| 场景 | 是否有问题 | 原因 |
|------|-----------|------|
| 不同用户同时使用 | 无问题 | 数据按 learner_id 完全隔离 |
| 同一用户正常操作 | 无问题 | 人的操作速度不会产生并发 |
| 同一用户重复点击/网络重试 | 有风险 | 需要 per-user 锁保护 |

### 8.3 竞态条件与解决方案

**问题场景**：同一用户快速重复提交（网络延迟、重复点击）

asyncio 协程在 await 点让出控制权，导致两个请求交叉执行：

```
请求1: 读 mastery=0.3 → await LLM调用（暂停，让出CPU）
请求2:                    读 mastery=0.3 → 计算=0.45 → 写入DB
请求1: （LLM返回，恢复）→ 基于旧值0.3计算=0.45 → 写入DB（覆盖请求2）

结果：两次答对只记录了一次 mastery 更新
```

**解决方案**：前端防抖 + 后端 per-user 锁

```python
# 前端：按钮点击后禁用，防止重复提交

# 后端：同一用户的请求串行化
user_locks: dict[str, asyncio.Lock] = {}

async def handle_request(learner_id: str, data):
    lock = user_locks.setdefault(learner_id, asyncio.Lock())
    async with lock:
        await process(data)
```

加锁后执行顺序：
```
请求1: 获得锁 → 读0.3 → await LLM → 算出0.45 → 写入 → 释放锁
请求2:          等待锁...                                获得锁 → 读0.45 → 算出0.58 → 写入
```

### 8.4 扩展考虑

当前阶段：单实例 FastAPI + asyncio.Lock（进程内锁）
未来多实例：升级为 Redis 分布式锁（代码改动小，只替换锁实现）

---

## 9. 可观测性

### 9.1 Langfuse（自托管）

- LLM 调用全链路追踪：prompt / response / token / cost / latency
- 原生 OpenTelemetry 协议支持
- Docker Compose 自托管，零成本

### 9.2 OpenTelemetry

- 通用链路追踪：HTTP 请求 → Agent 编排 → DB 读写 → 响应
- 与 Langfuse 融合，统一平台查看

### 9.3 业务指标

从 Event Sourcing 物化视图聚合：
- 学生进步速度（mastery 变化率）
- Hint 使用率（Level 1/2/3 分布）
- Re-plan 触发频率
- 各模型调用成本占比
- 教学策略有效性对比

---

## 10. 基础设施

### 10.1 Docker Compose 服务清单

```yaml
services:
  app:           # FastAPI + LangGraph 应用
  frontend:      # React 前端
  postgres:      # pgvector/pgvector:pg16（Event Store + 物化视图 + 向量 + 图）
  redis:         # Redis 7（会话缓存 + Stream + LangGraph checkpoint）
  langfuse:      # Langfuse 可观测性平台
```

### 10.2 部署策略

| 阶段 | 环境 | 说明 |
|------|------|------|
| 开发 | 本地 Docker Compose | 一键启动，快速迭代 |
| 展示 | 云端轻量服务器 | 阿里云/腾讯云，Docker Compose 全家桶 |
| 未来 | CI/CD | GitHub Actions 自动部署 |

---

## 11. 技术栈总览

| 层面 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| Agent 编排 | LangGraph |
| LLM（简单任务） | DeepSeek |
| LLM（复杂任务） | GPT-5.5 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/消息 | Redis 7（Stream） |
| 向量检索 | pgvector |
| 图存储 | PostgreSQL 邻接表 |
| 可观测性 | Langfuse + OpenTelemetry |
| 前端 | React |
| 容器化 | Docker Compose |
| Prompt 管理 | YAML 分层继承 |

---

## 12. 实施路径

### Phase 1：基础骨架
- LangGraph StateGraph 搭建（Router → Planner → Executor → Evaluator）
- Docker Compose 环境（PostgreSQL + Redis + App）
- YAML prompt 加载机制

### Phase 2：核心智能
- 多模型路由 + fallback 机制
- Plan-Execute-Evaluate 循环实现
- ReAct 对话循环实现
- 业务状态机（SessionFSM + EngagementFSM）

### Phase 3：数据层
- Event Sourcing 实现（Event Store + Redis Stream 异步投影）
- 物化视图设计与投影 worker
- 并发安全（per-user 锁 + 前端防抖）

### Phase 4：RAG
- 知识图谱扩展（新增关系类型）
- pgvector 向量检索
- Hybrid RAG 双路检索 + 融合

### Phase 5：可观测性与部署
- Langfuse 集成
- OpenTelemetry 链路追踪
- 云端部署 + CI/CD
