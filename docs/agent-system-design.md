# 多 Agent 智能教育系统设计文档

本文档面向刚开始学习项目架构和 Agent 设计的同学。你可以把它当成一份“从业务问题到代码实现”的讲解稿：先理解系统为什么这样拆，再看每个 Agent 做什么，最后看代码如何把这些 Agent 串起来。

## 1. 项目一句话说明

这个项目做的是一个“个性化学习系统”：

学生答题、提问或发送消息后，系统不是只返回一个固定答案，而是让多个专业 Agent 协作：

- Assessment Agent 判断学生掌握得怎么样。
- Tutor Agent 像老师一样用提问引导学生。
- Curriculum Agent 根据掌握度安排下一步学习和复习。
- Hint Agent 在学生卡住时给分级提示。
- Engagement Agent 观察学生是否挫败、无聊或疲劳。

最终目标是把传统在线教育里的“所有学生看同一套课、做同一套题”，改造成“根据每个学生状态实时调整教学策略”。

## 2. 先讲清楚：什么是 Agent

在这个项目里，Agent 不是一个神秘概念。你可以先把 Agent 理解成一个“有明确职责的小专家”。

普通函数通常只做一次输入输出，例如：

```text
输入：答题结果
输出：对或错
```

Agent 更像一个持续工作的角色：

```text
收到事件 -> 判断是不是自己负责 -> 读取学习者状态 -> 做专业决策 -> 发布新事件
```

所以 Agent 至少包含四个要素：

- 角色：它是谁，例如评估老师、课程规划师、提示老师。
- 职责：它负责什么，不负责什么。
- 输入事件：它监听哪些事件。
- 输出事件：它处理后会通知谁。

本项目的所有 Agent 都继承自 [BaseAgent](../python/agents/base_agent.py)。基类统一规定了 Agent 的基本行为：

```text
BaseAgent
  -> 保存 Agent 名称
  -> 保存 EventBus 引用
  -> 保存共享 learner_models
  -> 注册自己订阅的事件
  -> 提供 emit() 发布事件
  -> 提供 get_learner_model() 获取学生模型
```

这种设计叫“模板方法 + 依赖注入”：

- 模板方法：父类规定通用流程，子类只写自己的业务逻辑。
- 依赖注入：EventBus 和 learner_models 从外面传进来，Agent 不自己创建，方便测试和替换。

## 3. 当前项目真实架构

当前仓库里主要可运行实现是 Python 后端 + React 前端。

```text
multi-agent-education/
  docs/                  文档
  python/                Python 后端
    api/                 FastAPI 接口层
    agents/              5 个 Agent
    core/                事件总线、学习者模型、知识图谱、SM-2
    config/              配置
    tests/               单元测试
  frontend/              React 前端
  docker-compose.yml     PostgreSQL、Redis、Python API、前端容器编排
```

需要注意一个现实差异：README 和 docker-compose 描述了 PostgreSQL、Redis、OpenAI、LangGraph 等企业级组件，但当前核心代码主要是一个内存态演示版本：

- 学习者模型保存在 `AgentOrchestrator.learner_models` 字典里。
- 事件历史保存在 `EventBus._event_history` 列表里。
- 复习条目保存在 `CurriculumAgent._review_items` 字典里。
- 提示历史保存在 `HintAgent._hint_history` 字典里。
- Tutor Agent 和 Hint Agent 当前用模板文本模拟教学回复，没有真正调用 LLM。
- requirements 中包含 LangGraph/OpenAI/SQLAlchemy/Redis，但当前业务链路没有实际使用它们。

这不是坏事。对学习来说，当前实现更容易看懂；对生产来说，还需要补数据库持久化、消息队列、LLM 调用、权限、安全和可观测性。

## 4. 整体架构图

从运行链路看，系统可以分成四层：

```text
┌──────────────────────────────────────────────┐
│                  React 前端                   │
│  触发答题/提问/消息，展示 Agent 事件流          │
└───────────────────┬──────────────────────────┘
                    │ HTTP / WebSocket
┌───────────────────▼──────────────────────────┐
│                FastAPI 接口层                  │
│  routes.py 提供 REST，websocket.py 提供实时连接 │
└───────────────────┬──────────────────────────┘
                    │ 调用 Orchestrator
┌───────────────────▼──────────────────────────┐
│              AgentOrchestrator                │
│  创建 EventBus，初始化 5 个 Agent，共享学生状态 │
└───────────────────┬──────────────────────────┘
                    │ 发布/订阅事件
┌───────────────────▼──────────────────────────┐
│                 EventBus + Agents             │
│  Assessment / Tutor / Curriculum / Hint /      │
│  Engagement 通过事件协作                       │
└──────────────────────────────────────────────┘
```

对应代码：

- FastAPI 入口：[python/api/main.py](../python/api/main.py)
- REST 路由：[python/api/routes.py](../python/api/routes.py)
- WebSocket 路由：[python/api/websocket.py](../python/api/websocket.py)
- 编排器：[python/api/orchestrator.py](../python/api/orchestrator.py)
- 事件总线：[python/core/event_bus.py](../python/core/event_bus.py)
- Agent 基类：[python/agents/base_agent.py](../python/agents/base_agent.py)

## 5. 为什么选择 Mesh + 事件驱动

多 Agent 系统常见有三种组织方式。

### 5.1 Supervisor 模式

Supervisor 模式是“一个总管调度所有 Agent”。

```text
用户请求 -> Supervisor -> Agent A -> Supervisor -> Agent B -> Supervisor -> 返回
```

优点是简单、容易控制流程。

缺点是所有决策都依赖中心调度器，中心调度器会变成复杂大脑，也可能成为瓶颈。

在教育场景里，学生答错一道题后可能同时触发评估、鼓励、提示、课程调整。如果所有事情都让 Supervisor 判断，Supervisor 会越来越臃肿。

### 5.2 Pipeline 模式

Pipeline 模式是固定流水线。

```text
输入 -> Agent A -> Agent B -> Agent C -> 输出
```

它适合流程稳定的任务，例如文件解析、数据清洗、报表生成。

但教学不是固定流水线。学生可能答题、提问、沉默、连续错误、突然变强，每种情况都可能走不同路径。

### 5.3 Mesh + 事件驱动模式

本项目选择 Mesh + 事件驱动。

```text
EventBus 是通信层
Agent 自己订阅感兴趣的事件
谁产生变化，谁发布事件
谁关心这个变化，谁自动响应
```

例如学生答题后：

```text
api 发布 STUDENT_SUBMISSION
  -> Assessment Agent 订阅它，更新掌握度
  -> Engagement Agent 订阅它，记录行为状态

Assessment Agent 发布 ASSESSMENT_COMPLETE
  -> Tutor Agent 订阅它，生成教学反馈
  -> Engagement Agent 订阅它，分析学习状态

Assessment Agent 发布 MASTERY_UPDATED
  -> Curriculum Agent 订阅它，安排复习和推荐下个知识点
```

这样做的好处：

- 松耦合：Assessment Agent 不需要直接调用 Tutor Agent。
- 易扩展：新增一个 ParentNotifyAgent，只要订阅事件，不需要改原有 Agent。
- 支持并行：同一个事件可以被多个 Agent 同时处理。
- 更符合教育场景：学习过程是非线性的，不是固定步骤。

核心代码在 [python/core/event_bus.py](../python/core/event_bus.py)：

```text
subscribe(event_type, handler)  注册订阅者
publish(event)                  发布事件
_safe_handle(handler, event)     捕获异常，避免一个 Agent 失败影响其他 Agent
get_history(...)                 查询事件历史
```

EventBus 发布事件时使用 `asyncio.gather` 并发通知所有订阅者，这就是异步事件驱动的核心。

## 6. 核心数据模型

### 6.1 Event：系统里的消息信封

所有 Agent 之间都通过 Event 通信。Event 定义在 [python/core/event_bus.py](../python/core/event_bus.py)。

一个事件包含：

```text
id              事件唯一 ID
type            事件类型
source          谁发出的事件
timestamp       发生时间
learner_id      哪个学生
data            具体业务数据
correlation_id  事件链追踪 ID，当前预留
```

为什么要统一事件格式？

因为只要所有消息都长得一样，EventBus 就不需要理解业务细节。它只负责转发，业务逻辑交给 Agent。

### 6.2 EventType：系统支持的事件类型

当前主要事件可以分为几类：

```text
学生输入类
  STUDENT_SUBMISSION
  STUDENT_QUESTION
  STUDENT_MESSAGE

评估类
  ASSESSMENT_COMPLETE
  MASTERY_UPDATED
  WEAKNESS_DETECTED

教学类
  TEACHING_RESPONSE
  HINT_NEEDED
  DIFFICULTY_ADJUSTED

课程类
  PATH_UPDATED
  REVIEW_SCHEDULED
  NEXT_TOPIC

提示类
  HINT_RESPONSE

互动类
  ENGAGEMENT_ALERT
  ENCOURAGEMENT
  PACE_ADJUSTMENT
```

初学者可以把 EventType 理解成“系统内部的通知名称”。

### 6.3 LearnerModel：学生画像

LearnerModel 定义在 [python/core/learner_model.py](../python/core/learner_model.py)。

它记录一个学生在多个知识点上的状态：

```text
learner_id
knowledge_states
  arithmetic -> KnowledgeState
  quadratic_eq -> KnowledgeState
  ...
total_interactions
session_start
metadata
```

每个 KnowledgeState 记录：

```text
knowledge_id      知识点 ID
mastery           掌握概率，0 到 1
alpha/beta        Beta 分布参数，当前辅助表示成功/失败证据
attempts          尝试次数
correct_count     正确次数
last_attempt      上次尝试时间
streak            连续正确次数
level             根据 mastery 分段得到的等级
confidence        根据数据量得到的置信度
```

这就是个性化学习的核心。没有 LearnerModel，系统就不知道学生是谁、学到了哪里、弱点在哪里。

## 7. 核心业务流程

### 7.1 学生答题流程

入口在 [python/api/orchestrator.py](../python/api/orchestrator.py) 的 `submit_answer()`。

完整流程如下：

```text
1. 前端发送 submit 动作
2. WebSocket 或 REST 调用 orch.submit_answer()
3. Orchestrator 发布 STUDENT_SUBMISSION
4. EventBus 把事件分发给：
   Assessment Agent
   Engagement Agent
5. Assessment Agent 更新 BKT 掌握度
6. Assessment Agent 发布：
   MASTERY_UPDATED
   WEAKNESS_DETECTED，满足薄弱条件时
   ASSESSMENT_COMPLETE
7. Curriculum Agent 收到 MASTERY_UPDATED：
   更新 SM-2 复习计划
   如果掌握度达标，推荐下一个知识点
8. Tutor Agent 收到 ASSESSMENT_COMPLETE：
   答对则继续追问
   答错则苏格拉底式引导
   多次答错则发布 HINT_NEEDED
9. Hint Agent 收到 HINT_NEEDED：
   生成分级提示
   发布 HINT_RESPONSE
10. Tutor Agent 收到 HINT_RESPONSE：
   转成 TEACHING_RESPONSE 给学生
11. Engagement Agent 分析连续错误、正确率、学习时长：
   必要时发布 ENGAGEMENT_ALERT 或 PACE_ADJUSTMENT
```

这个流程不是一条死板链路，而是一组事件触发的协作。

### 7.2 学生提问流程

入口是 `ask_question()`。

```text
1. Orchestrator 发布 STUDENT_QUESTION
2. Assessment Agent 判断问题对应知识点当前掌握度
3. Assessment Agent 发布 ASSESSMENT_COMPLETE，context=student_question
4. Tutor Agent 根据掌握等级生成苏格拉底式回复
5. 前端展示 TEACHING_RESPONSE
```

这体现了一个关键设计：学生问同一个问题，系统不应该给所有人一样的回答。初学者需要更基础的类比，熟练者需要更深层的追问。

### 7.3 学生自由消息流程

入口是 `send_message()`。

```text
1. Orchestrator 发布 STUDENT_MESSAGE
2. Tutor Agent 读取当前知识点掌握度
3. Tutor Agent 生成对话回复
4. Engagement Agent 记录学生有活动
```

当前实现里自由消息没有调用 LLM，只是模板生成。

## 8. 五个 Agent 的详细设计

### 8.1 Assessment Agent：评估老师

代码位置：[python/agents/assessment_agent.py](../python/agents/assessment_agent.py)

#### 它解决什么问题

教育系统首先要知道“学生到底会不会”。

很多系统只用正确率判断：

```text
做了 10 题，对了 7 题 -> 正确率 70%
```

但正确率有明显问题：

- 学生可能猜对。
- 学生可能会但粗心做错。
- 刚开始做题少，正确率不稳定。
- 正确率不能很好表达“学习后变会了”的过程。

所以本项目用 BKT，中文叫贝叶斯知识追踪。

#### 它订阅什么事件

```text
STUDENT_SUBMISSION
STUDENT_QUESTION
```

#### 它发布什么事件

```text
MASTERY_UPDATED       掌握度更新
WEAKNESS_DETECTED    检测到薄弱点
ASSESSMENT_COMPLETE  评估完成
```

#### 核心算法：BKT

BKT 的核心思想：

```text
学生答对/答错只是一个观察结果
真正想估计的是学生是否掌握知识点
```

BKT 用四个参数：

```text
P(L0) 初始掌握概率，默认 0.1
P(T)  学习转移概率，默认 0.15
P(G)  猜对概率，默认 0.2
P(S)  失误概率，默认 0.1
```

举个直观例子：

学生答对了，不代表 100% 会，因为可能猜对。

学生答错了，也不代表 0% 会，因为可能粗心失误。

BKT 会根据当前 mastery 和答题结果更新概率。

答对时：

```text
P(correct | 已掌握) = 1 - P(S)
P(correct | 未掌握) = P(G)
```

答错时：

```text
P(wrong | 已掌握) = P(S)
P(wrong | 未掌握) = 1 - P(G)
```

更新后还要加上学习转移：

```text
学生做完一次练习后，即使刚才不会，也可能学会一部分
```

所以代码最后会做：

```text
P(new) = P(after_observation) + (1 - P(after_observation)) * P(T)
```

#### 为什么它应该单独成为一个 Agent

因为评估是系统的“状态事实来源”。如果 Tutor Agent、Curriculum Agent、Hint Agent 都自己计算掌握度，会出现三个问题：

- 逻辑重复。
- 结论不一致。
- 后续不好调参和测试。

让 Assessment Agent 独占掌握度更新，就形成“单写者策略”：mastery 只由 Assessment Agent 写，其他 Agent 只读或订阅结果。

### 8.2 Tutor Agent：教学老师

代码位置：[python/agents/tutor_agent.py](../python/agents/tutor_agent.py)

#### 它解决什么问题

学生不会时，系统不应该直接甩答案。

直接给答案的短期效果很好，学生马上知道结果；长期效果很差，因为学生没有经历思考过程。

Tutor Agent 的职责是“引导学生思考”，也就是苏格拉底式教学。

#### 它订阅什么事件

```text
ASSESSMENT_COMPLETE
STUDENT_MESSAGE
HINT_RESPONSE
ENGAGEMENT_ALERT
```

#### 它发布什么事件

```text
TEACHING_RESPONSE
HINT_NEEDED
DIFFICULTY_ADJUSTED
```

#### 苏格拉底式教学是什么

普通回答：

```text
二次函数 y=x²+2x+1 的顶点是 (-1,0)。
```

苏格拉底式回答：

```text
你能先试试把 x²+2x+1 配方吗？
如果写成 (x+1)²，那么平方项最小是多少？
此时 x 应该等于多少？
```

区别在于：

- 不是直接给结论。
- 用问题引导学生回忆已有知识。
- 让学生参与推理过程。

#### 当前代码如何实现

代码里定义了 `SOCRATIC_PROMPTS`，按掌握等级分为四类：

```text
beginner    初学者，用简单语言和例子
developing  发展中，引导发现关键步骤
proficient  熟练者，追问为什么和其他方法
mastered    已掌握者，总结方法论和挑战题
```

当前 `_generate_teaching_response()` 使用模板生成回复：

- 答对：肯定表现，并追问更深问题。
- 答错：不直接给答案，问卡在哪一步。
- 提问：先让学生说已有理解。

如果同一学生同一知识点连续答错达到 2 次，Tutor Agent 不继续自己生成回复，而是发布 `HINT_NEEDED` 让 Hint Agent 专门处理提示。

#### 为什么它应该单独成为一个 Agent

教学策略和评估策略是两件事。

Assessment Agent 关心“学生掌握度是多少”，Tutor Agent 关心“下一句话怎么教”。把它们拆开后：

- 评估算法可以从 BKT 换成深度知识追踪，不影响教学话术。
- 教学策略可以从模板换成 LLM Prompt，不影响 mastery 更新。
- Tutor Agent 可以独立订阅情绪警报，调整语气和难度。

### 8.3 Curriculum Agent：课程规划师

代码位置：[python/agents/curriculum_agent.py](../python/agents/curriculum_agent.py)

#### 它解决什么问题

学生学完一个知识点后，系统要回答两个问题：

```text
下一步学什么？
什么时候复习？
```

这就是 Curriculum Agent 的职责。

#### 它订阅什么事件

```text
MASTERY_UPDATED
WEAKNESS_DETECTED
PACE_ADJUSTMENT
```

#### 它发布什么事件

```text
NEXT_TOPIC
REVIEW_SCHEDULED
PATH_UPDATED
```

#### 知识图谱：决定学什么

知识图谱定义在 [python/core/knowledge_graph.py](../python/core/knowledge_graph.py)。

它是一个 DAG，也就是有向无环图。

例如：

```text
四则运算 -> 分数运算 -> 概率初步
四则运算 -> 负数 -> 代数式 -> 一元一次方程 -> 一元二次方程
```

为什么要用图？

因为知识点不是一条直线。一个知识点可能有多个前置知识：

```text
一元二次方程 需要：
  因式分解
  一元一次方程
```

图比树更灵活，因为一个节点可以有多个父节点。

Curriculum Agent 用 `get_ready_nodes(mastered_ids)` 找出“前置知识都掌握了，但自己还没掌握”的知识点，然后按难度排序推荐。

#### SM-2：决定什么时候复习

SM-2 算法定义在 [python/core/spaced_repetition.py](../python/core/spaced_repetition.py)。

核心思想：

```text
不是每天重复所有内容
而是在快忘记的时候复习
```

每个复习条目有：

```text
easiness_factor  难度因子，默认 2.5
interval_days    当前复习间隔
repetition       成功复习次数
next_review      下次复习时间
```

回答质量 quality 从 0 到 5：

```text
5 完美回答
4 正确但思考了一下
3 勉强正确
2 错误但看答案熟悉
1 错误但有点印象
0 完全不会
```

当前项目没有直接让学生打 quality，而是把 mastery 映射成 quality：

```text
mastery >= 0.90 -> quality 5
mastery >= 0.75 -> quality 4
mastery >= 0.60 -> quality 3
mastery >= 0.40 -> quality 2
mastery >= 0.20 -> quality 1
其他              -> quality 0
```

#### 为什么它应该单独成为一个 Agent

课程规划和实时教学不同。

Tutor Agent 关注“这一刻怎么回复学生”，Curriculum Agent 关注“长期学习路径怎么走”。拆开后：

- 可以独立优化推荐算法。
- 可以独立接入课程库和题库。
- 可以把学习路径、复习计划、补救路径作为长期状态持久化。

### 8.4 Hint Agent：提示老师

代码位置：[python/agents/hint_agent.py](../python/agents/hint_agent.py)

#### 它解决什么问题

学生卡住时，系统要给帮助，但帮助不能一步到位给答案。

提示太弱，学生继续卡住。

提示太强，学生失去思考机会。

所以 Hint Agent 采用三级提示。

#### 它订阅什么事件

```text
HINT_NEEDED
```

#### 它发布什么事件

```text
HINT_RESPONSE
```

#### 三级提示策略

```text
Level 1: Metacognitive 元认知暗示
让学生反思题目信息、解题方向、已知条件。

Level 2: Scaffolding 脚手架引导
给出关键步骤或关键概念，但不直接给最终答案。

Level 3: Targeted 直接提示
在多次失败后给具体解法，并要求学生重做巩固。
```

代码中的升级规则：

```text
mastery < 0.15 且 attempts >= 3 -> 直接 Level 3
提示次数 <= 1 -> Level 1
提示次数 <= 3 -> Level 2
其他 -> Level 3
```

#### 为什么它应该单独成为一个 Agent

提示系统很容易变复杂：

- 要考虑尝试次数。
- 要考虑掌握度。
- 要考虑之前已经给过什么提示。
- 未来还可能根据具体题目生成不同层级提示。

如果把这些逻辑塞进 Tutor Agent，Tutor Agent 会变成大杂烩。单独拆 Hint Agent，能保持 Tutor Agent 专注对话教学。

### 8.5 Engagement Agent：学习状态观察员

代码位置：[python/agents/engagement_agent.py](../python/agents/engagement_agent.py)

#### 它解决什么问题

学生学习效果不只取决于会不会，还取决于状态：

- 连续错很多题，可能挫败。
- 连续对很多题，可能无聊。
- 学了很久正确率下降，可能疲劳。
- 长时间没操作，可能离开了。

Engagement Agent 负责观察这些行为信号。

#### 它订阅什么事件

```text
STUDENT_SUBMISSION
ASSESSMENT_COMPLETE
STUDENT_MESSAGE
```

#### 它发布什么事件

```text
ENGAGEMENT_ALERT
PACE_ADJUSTMENT
ENCOURAGEMENT
```

#### 当前状态检测规则

代码里定义了这些学习状态：

```text
FOCUSED      专注
STRUGGLING   遇到困难
FRUSTRATED   挫败
BORED        无聊
FATIGUED     疲劳
IDLE         闲置
```

检测规则：

```text
idle_seconds > 300 -> IDLE
consecutive_errors >= 3 -> FRUSTRATED
session_duration > 45 分钟 且 recent_accuracy < 0.5 -> FATIGUED
recent_accuracy > 0.9 且 consecutive_correct >= 5 -> BORED
consecutive_errors >= 1 -> STRUGGLING
否则 -> FOCUSED
```

对应干预：

```text
FRUSTRATED -> 发送挫败警报，通知 Tutor 降低难度，通知 Curriculum 放慢节奏
BORED -> 发送无聊警报，通知 Tutor 提高挑战，通知 Curriculum 加快节奏
FATIGUED -> 建议休息
FOCUSED 且连续正确 -> 鼓励
```

#### 为什么它应该单独成为一个 Agent

因为学习状态监测是横切关注点。

它不属于评估，也不属于课程，也不属于提示。它要观察多个事件，并影响多个 Agent。

如果没有 Engagement Agent，系统可能只看到“学生答错了”，却看不到“学生已经连续错三题，需要降难度和鼓励”。

## 9. Agent 协作关系表

| Agent | 订阅事件 | 主要输出 | 设计定位 |
| --- | --- | --- | --- |
| Assessment | STUDENT_SUBMISSION, STUDENT_QUESTION | MASTERY_UPDATED, WEAKNESS_DETECTED, ASSESSMENT_COMPLETE | 判断学生掌握度，是学习状态的事实来源 |
| Tutor | ASSESSMENT_COMPLETE, STUDENT_MESSAGE, HINT_RESPONSE, ENGAGEMENT_ALERT | TEACHING_RESPONSE, HINT_NEEDED, DIFFICULTY_ADJUSTED | 决定怎么教、怎么说 |
| Curriculum | MASTERY_UPDATED, WEAKNESS_DETECTED, PACE_ADJUSTMENT | NEXT_TOPIC, REVIEW_SCHEDULED, PATH_UPDATED | 决定学什么、何时复习 |
| Hint | HINT_NEEDED | HINT_RESPONSE | 学生卡住时给分级提示 |
| Engagement | STUDENT_SUBMISSION, ASSESSMENT_COMPLETE, STUDENT_MESSAGE | ENGAGEMENT_ALERT, PACE_ADJUSTMENT, ENCOURAGEMENT | 判断学习情绪和节奏 |

## 10. Orchestrator 的作用

代码位置：[python/api/orchestrator.py](../python/api/orchestrator.py)

很多人看到 `AgentOrchestrator` 会疑惑：既然说不是 Supervisor，为什么还有 Orchestrator？

这里要区分两个概念：

```text
Orchestrator 负责初始化和对外入口
Supervisor 负责业务决策和调度
```

当前 Orchestrator 做的是：

- 创建 EventBus。
- 创建共享 `learner_models`。
- 初始化 5 个 Agent。
- 对 API 层提供 `submit_answer()`、`ask_question()`、`send_message()`。

它不负责决定“答错后该谁处理”。这个决定来自 Agent 自己的事件订阅。

所以它更像“装配器”或“应用服务入口”，不是中心化大脑。

## 11. 前端设计

前端在 [frontend/src/App.tsx](../frontend/src/App.tsx)。

它当前是一个演示台：

```text
左侧：
  选择知识点
  点击答对/答错
  输入问题

右侧：
  展示 Agent 事件流
```

WebSocket Hook 在 [frontend/src/hooks/useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts)。

它做了：

- 建立 `/ws/{learnerId}` 连接。
- 收到消息后追加到事件列表。
- 断开后指数退避重连。
- 提供 `send()` 给页面发送动作。

开发模式下，Vite 配置在 [frontend/vite.config.ts](../frontend/vite.config.ts)：

```text
/api -> http://localhost:8000
/ws  -> ws://localhost:8000
```

容器部署时，Nginx 配置在 [frontend/nginx.conf](../frontend/nginx.conf)，会把 `/api/` 和 `/ws/` 代理到 `python-api:8000`。

## 12. 为什么要拆成 5 个 Agent，而不是 1 个大 Agent

一个大 Agent 当然也能做：

```text
收到学生输入
判断掌握度
生成回复
安排复习
检测情绪
给提示
```

但这样会带来几个问题。

### 12.1 职责混乱

评估、教学、课程规划、提示、情绪干预是五种不同思维方式。

一个大 Agent 的 prompt 或代码会越来越长，最后谁也看不懂。

### 12.2 难以测试

如果一个大函数同时更新 mastery、生成回复、安排复习，你很难单独验证“BKT 算法是否正确”。

拆开后可以分别测试：

- LearnerModel 更新是否正确。
- SM-2 间隔是否正确。
- KnowledgeGraph 拓扑排序是否正确。
- EventBus 发布订阅是否正确。

当前测试在 [python/tests/test_agents.py](../python/tests/test_agents.py)。

### 12.3 难以扩展

未来想新增“家长通知 Agent”：

如果是一体化代码，你要修改主流程。

如果是事件驱动，只需要：

```text
订阅 WEAKNESS_DETECTED
订阅 ENCOURAGEMENT
发送家长通知
```

### 12.4 难以替换模型

未来 Assessment Agent 可以从 BKT 换成 DKT，Tutor Agent 可以从模板换成真实 LLM，Curriculum Agent 可以从规则推荐换成强化学习推荐。

拆分后，每个 Agent 可以独立进化。

### 12.5 更贴近真实团队分工

在真实公司里，这五件事往往对应不同团队或模块：

- 学习诊断
- 智能辅导
- 课程推荐
- 题目提示
- 用户增长/学习体验

多 Agent 架构天然表达这种专业分工。

## 13. 为什么 EventBus 不直接互相调用

不用 EventBus 时，可能写成：

```python
assessment.handle_submission()
tutor.handle_assessment()
curriculum.update_path()
engagement.analyze()
```

这叫直接调用。简单项目可以这么写。

但直接调用的问题是调用方必须知道所有下游：

```text
Assessment Agent 要知道 Tutor Agent
Assessment Agent 要知道 Curriculum Agent
Assessment Agent 要知道 Engagement Agent
```

这会导致强耦合。

用 EventBus 后：

```text
Assessment Agent 只发布 ASSESSMENT_COMPLETE
它不关心谁订阅
```

这样 Assessment Agent 更纯粹，也更容易复用。

## 14. 状态一致性设计

当前项目是内存态单进程演示，所以状态一致性相对简单。

但设计上已经体现了几个重要原则。

### 14.1 单写者策略

mastery 只由 Assessment Agent 更新。

其他 Agent 不直接修改 mastery，只根据 `MASTERY_UPDATED` 和 `ASSESSMENT_COMPLETE` 做自己的事。

好处是：

- 避免多个 Agent 同时改同一个字段。
- 出问题时容易定位。
- 后续持久化时可以只给 Assessment Agent 写权限。

### 14.2 事件历史

EventBus 保存 `_event_history`。

这不是完整生产级事件溯源，但体现了思路：

```text
发生过什么事件
谁发的
什么时候发的
对哪个学生
携带什么数据
```

有了事件历史，就可以排查：

- 为什么学生收到了这个提示？
- mastery 是哪次答题后变化的？
- 哪个 Agent 发出了难度调整？

### 14.3 生产环境应该怎么演进

如果要做成真实产品，需要把内存状态换成持久化状态：

```text
LearnerModel -> PostgreSQL
EventHistory -> PostgreSQL 或 Kafka/Pulsar
短期会话缓存 -> Redis
WebSocket 连接状态 -> Redis Pub/Sub 或网关层管理
Agent 内部计数 -> Redis 或数据库
```

并补充：

- version 字段做乐观锁。
- event_id 做幂等。
- correlation_id 追踪完整事件链。
- outbox pattern 保证数据库写入和事件发布一致。

## 15. 当前代码的优点与不足

### 15.1 优点

- 架构清晰：EventBus、Orchestrator、Agent、Core 算法分层明确。
- 适合学习：没有过早引入数据库和复杂消息队列，能直接看懂 Agent 协作。
- Agent 职责拆分合理：评估、教学、课程、提示、互动没有混在一起。
- 核心算法有实现：BKT、SM-2、知识图谱拓扑排序都不是空概念。
- 前后端闭环完整：前端能通过 WebSocket 触发事件并展示结果。
- 测试覆盖核心模块：事件总线、BKT、SM-2、知识图谱都有基础测试。

### 15.2 不足

- 没有真正接入 LLM，教学回复和提示目前是模板。
- 没有真正使用 LangGraph，虽然 requirements 和文档提到了它。
- 没有数据库持久化，服务重启后学生状态会丢失。
- EventBus 是进程内实现，不能跨多个后端实例通信。
- WebSocket 当前每次返回最近事件，可能重复推送历史事件。
- `correlation_id` 字段预留但没有贯穿事件链。
- README 中提到 Java/Go 三语言实现，但当前 git 状态显示相关目录已删除，实际可分析主体是 Python + React。
- `docker-compose.yml` 启动了 PostgreSQL 和 Redis，但当前 Python 业务代码没有真正读写它们。

这些不足不是架构失败，而是当前项目处于“可演示、可学习”的阶段，还没有进入生产强化阶段。

## 16. 如果要升级成生产级系统，建议路线

### 阶段 1：让状态可持久化

先做最关键的一步：学生状态不能丢。

建议新增：

```text
learners 表
knowledge_states 表
events 表
review_items 表
hint_histories 表
engagement_states 表
```

然后把当前内存字典逐步替换成 Repository。

### 阶段 2：接入真实 LLM

Tutor Agent 和 Hint Agent 最适合先接 LLM。

注意不要直接把所有学生信息丢给 LLM，应控制上下文：

```text
学生当前问题
知识点
mastery
level
最近几次错误摘要
需要的教学风格
禁止直接给答案的约束
```

还应增加：

- prompt 模板版本。
- 输出结构化校验。
- 敏感内容过滤。
- 超时和降级模板。

### 阶段 3：把 EventBus 升级成可分布式

单进程 EventBus 适合演示，不适合多实例部署。

生产可选：

```text
Redis Streams
Kafka
RabbitMQ
NATS
Pulsar
```

选择标准：

- 小项目优先 Redis Streams。
- 大规模事件流优先 Kafka/Pulsar。
- 低延迟服务通信可考虑 NATS。

### 阶段 4：完善可观测性

需要能回答：

```text
一次学生答题触发了哪些 Agent？
每个 Agent 耗时多少？
哪个事件失败了？
LLM 花了多少钱？
哪个知识点最容易导致挫败？
```

建议增加：

- 结构化日志。
- trace_id/correlation_id。
- metrics 指标。
- Agent 执行耗时统计。
- LLM token 和成本统计。

### 阶段 5：完善权限和安全

教育系统涉及学生数据，必须重视隐私。

需要补充：

- 用户登录。
- learner_id 不能由前端随便指定。
- API 鉴权。
- CORS 限制。
- WebSocket 鉴权。
- 学生数据脱敏。
- API Key 不进入仓库。

## 17. 新手应该按什么顺序读代码

建议不要一上来就看所有文件。按这个顺序读：

1. [python/core/event_bus.py](../python/core/event_bus.py)
   先理解事件是什么、怎么发布、怎么订阅。

2. [python/agents/base_agent.py](../python/agents/base_agent.py)
   理解所有 Agent 的共同结构。

3. [python/api/orchestrator.py](../python/api/orchestrator.py)
   看 5 个 Agent 是如何被创建和连接到 EventBus 的。

4. [python/agents/assessment_agent.py](../python/agents/assessment_agent.py)
   看学生答题后 mastery 如何更新。

5. [python/core/learner_model.py](../python/core/learner_model.py)
   深入理解 BKT。

6. [python/agents/tutor_agent.py](../python/agents/tutor_agent.py)
   看如何根据评估结果生成教学回复。

7. [python/agents/hint_agent.py](../python/agents/hint_agent.py)
   看连续答错后提示如何升级。

8. [python/agents/curriculum_agent.py](../python/agents/curriculum_agent.py)
   看知识图谱和复习计划如何工作。

9. [python/agents/engagement_agent.py](../python/agents/engagement_agent.py)
   看学习状态监测如何影响教学节奏。

10. [frontend/src/App.tsx](../frontend/src/App.tsx)
    看前端如何触发事件并展示结果。

## 18. 面试讲解版本

如果你面试时要讲这个项目，可以这样讲：

```text
这个项目是一个多 Agent 个性化教育系统。我把教学过程拆成 5 个专业 Agent：Assessment 负责知识追踪，Tutor 负责苏格拉底式教学，Curriculum 负责学习路径和复习计划，Hint 负责分级提示，Engagement 负责学习状态监测。

架构上我没有用固定 Pipeline，也没有让一个 Supervisor 管所有逻辑，而是使用 Mesh + 事件驱动。每个 Agent 订阅自己关心的事件，处理后发布新的事件。这样 Assessment 不需要知道 Tutor 和 Curriculum 的存在，只需要发布 mastery 更新事件，系统就能自然触发后续教学、复习和干预。

核心算法上，Assessment 使用 BKT 考虑猜测和失误，比简单正确率更适合动态知识追踪；Curriculum 使用知识图谱保证前置知识先学，并用 SM-2 算法安排复习；Tutor 和 Hint 使用苏格拉底式教学和三级提示策略，避免直接给答案；Engagement 根据连续错误、正确率、学习时长判断挫败、无聊和疲劳。

当前实现是 Python + FastAPI + asyncio EventBus + React WebSocket 演示版，状态主要在内存中。生产化方向是把 LearnerModel、事件历史和复习计划持久化到 PostgreSQL/Redis，把进程内 EventBus 替换成 Kafka 或 Redis Streams，并接入真实 LLM 做结构化教学回复。
```

## 19. 一句话总结设计思想

这个项目的核心不是“有 5 个类叫 Agent”，而是把教育过程拆成 5 个可独立决策、可独立测试、可独立演进的专业角色，再用事件总线把它们松耦合地连接起来。

这就是多 Agent 架构真正有价值的地方。
