"""
题库管理 — 加载题目、按知识点/难度检索
开发阶段从 YAML 加载，生产阶段可切换为 DB 查询。
"""
import yaml
import random
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from loguru import logger
DATA_PATH = Path(__file__).parent.parent / "data" / "questions.yaml"
class Question(BaseModel):
    """题目数据模型。"""
    id: str
    knowledge_id: str
    type: str                          # choice / fill / open
    difficulty: float
    stem: str
    options: Optional[dict] = None     # 仅 choice
    answer: str
    tolerance: Optional[float] = None  # 仅 fill
    explanation: Optional[str] = None
    rubric: Optional[list[str]] = None # 仅 open
class QuestionBank:
    """题库加载器。"""
    def __init__(self, path: str = None):
        self._questions: dict[str, Question] = {}
        self._by_knowledge: dict[str, list[Question]] = {}
        self._load(path or str(DATA_PATH))
    def _load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for item in data.get("questions", []):
            q = Question(**item)
            self._questions[q.id] = q
            self._by_knowledge.setdefault(q.knowledge_id, []).append(q)
        logger.info(f"[QuestionBank] 加载 {len(self._questions)} 道题目")
    def get_question(self, question_id: str) -> Optional[Question]:
        return self._questions.get(question_id)
    def get_by_knowledge(self, knowledge_id: str) -> list[Question]:
        return self._by_knowledge.get(knowledge_id, [])
    def get_random(
        self,
        knowledge_id: str,
        difficulty_range: tuple[float, float] = (0, 1),
    ) -> Optional[Question]:
        """按知识点和难度范围随机抽题。"""
        candidates = [
            q for q in self.get_by_knowledge(knowledge_id)
            if difficulty_range[0] <= q.difficulty <= difficulty_range[1]
        ]
        return random.choice(candidates) if candidates else None
# 模块级单例
question_bank = QuestionBank()