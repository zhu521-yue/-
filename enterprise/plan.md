# 题库系统 + 自动判题 实现计划

## 1. 题目数据结构

### YAML 格式（开发阶段）

文件：`src/data/questions.yaml`

```yaml
questions:
  - id: "q_001"
    knowledge_id: "quadratic_eq"
    type: "choice"              # choice / fill / open
    difficulty: 0.3
    stem: "方程 x²-5x+6=0 的解是？"
    options:                    # 仅 choice 类型
      A: "x=2, x=3"
      B: "x=-2, x=-3"
      C: "x=2, x=-3"
      D: "x=-2, x=3"
    answer: "A"                 # choice→选项字母, fill→精确值, open→参考答案
    tolerance: null             # fill 类型的数值容差（如 0.01）
    explanation: "因式分解 (x-2)(x-3)=0"

  - id: "q_002"
    knowledge_id: "quadratic_eq"
    type: "fill"
    difficulty: 0.4
    stem: "方程 x²-4=0 的正数解是 x=____"
    answer: "2"
    tolerance: 0.01

  - id: "q_003"
    knowledge_id: "quadratic_eq"
    type: "open"
    difficulty: 0.6
    stem: "请用求根公式求解方程 2x²+3x-2=0，写出完整步骤。"
    answer: "x=1/2 或 x=-2。代入求根公式 x=(-3±√(9+16))/4=(-3±5)/4"
    rubric:                     # 评分要点（给 LLM 判题用）
      - "正确写出求根公式"
      - "正确计算判别式 Δ=9+16=25"
      - "得到两个正确的根"
```

### DB 表结构（生产阶段）

```sql
CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(50) PRIMARY KEY,
    knowledge_id VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,        -- choice / fill / open
    difficulty FLOAT DEFAULT 0.5,
    stem TEXT NOT NULL,
    options JSONB,                     -- {"A": "...", "B": "..."}
    answer TEXT NOT NULL,
    tolerance FLOAT,
    explanation TEXT,
    rubric JSONB,                      -- ["要点1", "要点2"]
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 2. 判题逻辑

新建 `src/core/grader.py`：

```
Grader
  ├── grade(question, student_answer) → GradeResult
  │     ├── choice → 精确匹配 answer 字段
  │     ├── fill → 数值/字符串匹配（支持 tolerance）
  │     └── open → LLM 判题（传 rubric + 标准答案 + 学生答案）
  │
  └── GradeResult:
        is_correct: bool
        score: float (0-1，open 题可能部分正确)
        feedback: str (错误原因/部分正确说明)
```

## 3. 题目加载器

新建 `src/core/question_bank.py`：

```
QuestionBank
  ├── __init__(): 从 YAML 加载题目
  ├── get_question(question_id) → Question
  ├── get_by_knowledge(knowledge_id) → list[Question]
  └── get_random(knowledge_id, difficulty_range) → Question
```

## 4. /submit 接口改造

```
当前：{learner_id, knowledge_id, is_correct}
改为：{learner_id, question_id, answer}
```

流程：
1. QuestionBank 查题目
2. Grader 判对错
3. AssessmentAgent 更新 mastery
4. 返回判题结果 + 评估报告

## 5. 新增 prompt

`prompts/grader.yaml` — 给 LLM 判解答题用的 prompt

## 6. 文件清单

| 文件 | 说明 |
|------|------|
| `src/data/questions.yaml` | 题库数据（每个知识点 2-3 题） |
| `src/core/question_bank.py` | 题目加载器 |
| `src/core/grader.py` | 判题逻辑（三种题型） |
| `src/prompts/grader.yaml` | 解答题 LLM 判题 prompt |
| `src/api/routes.py` | /submit 接口改造 |
| `src/storage/schema.sql` | 新增 questions 表 |
| `tests/test_grader.py` | 判题逻辑单元测试 |

## 7. 实施顺序

1. questions.yaml — 先写几道示例题
2. question_bank.py — 加载器
3. grader.py — 判题逻辑（choice + fill 先做，open 后做）
4. grader.yaml — LLM 判题 prompt
5. routes.py 改造 — 接入新流程
6. 测试
