"""
自动判题模块
三种题型的判题策略：
  - choice：精确匹配选项字母
  - fill：数值/字符串匹配（支持容差）
  - open：LLM 判题（基于 rubric + 标准答案）
"""

from pydantic import BaseModel
from src.core.question_bank import Question
from src.core.llm_client import chat
from src.core.prompt_loader import load_prompt
from loguru import logger
class GradeResult(BaseModel):
    """判题结果。"""
    is_correct: bool
    score: float          # 0-1，open 题可能部分正确
    feedback: str         # 反馈信息
class Grader:
    """自动判题器。"""
    def grade(self, question: Question, student_answer: str) -> GradeResult:
        """根据题型分发判题逻辑。"""
        student_answer = student_answer.strip()
        if question.type == "choice":
            return self._grade_choice(question, student_answer)
        elif question.type == "fill":
            return self._grade_fill(question, student_answer)
        elif question.type == "open":
            return self._grade_open(question, student_answer)
        else:
            return GradeResult(is_correct=False, score=0, feedback="未知题型")
    def _grade_choice(self, question: Question, answer: str) -> GradeResult:
        """选择题：精确匹配。"""
        is_correct = answer.upper() == question.answer.upper()
        return GradeResult(
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            feedback="" if is_correct else f"正确答案是 {question.answer}。{question.explanation or ''}",
        )
    def _grade_fill(self, question: Question, answer: str) -> GradeResult:
        """填空题：字符串匹配或数值容差匹配。"""
        tolerance = question.tolerance or 0
        # 先尝试数值比较
        try:
            student_val = self._parse_number(answer)
            correct_val = self._parse_number(question.answer)
            is_correct = abs(student_val - correct_val) <= tolerance
        except ValueError:
            # 非数值，字符串精确匹配（忽略空格）
            is_correct = answer.replace(" ", "") == question.answer.replace(" ", "")
        return GradeResult(
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            feedback="" if is_correct else f"正确答案是 {question.answer}。{question.explanation or ''}",
        )
    def _grade_open(self, question: Question, answer: str) -> GradeResult:
        """解答题：LLM 判题。"""
        prompt = load_prompt("grader")
        system_prompt = prompt["instruction"]
        rubric_text = "\n".join(f"- {r}" for r in (question.rubric or []))
        user_message = (
            f"题目：{question.stem}\n"
            f"标准答案：{question.answer}\n"
            f"评分要点：\n{rubric_text}\n"
            f"\n学生答案：{answer}\n"
            f"\n请判断学生答案的正确性，返回 JSON 格式：\n"
            f'{{"score": 0-1的小数, "is_correct": true/false, "feedback": "具体反馈"}}'
        )
        response = chat(system_prompt, user_message).strip()
        # 解析 LLM 返回的 JSON
        try:
            import json
            result = json.loads(response)
            return GradeResult(
                is_correct=result.get("is_correct", False),
                score=result.get("score", 0),
                feedback=result.get("feedback", ""),
            )
        except (json.JSONDecodeError, KeyError):
            # LLM 返回格式异常，降级处理
            logger.warning(f"[Grader] LLM 返回格式异常: {response}")
            return GradeResult(
                is_correct=False,
                score=0,
                feedback="判题系统异常，请重试",
            )
    def _parse_number(self, s: str) -> float:
        """解析数值，支持分数格式如 '1/3'。"""
        s = s.strip()
        if "/" in s:
            parts = s.split("/")
            return float(parts[0]) / float(parts[1])
        return float(s)
# 模块级单例
grader = Grader()


