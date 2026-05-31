"""
判题模块单元测试

测试范围：
  - QuestionBank：加载、检索
  - Grader：选择题、填空题、解答题（mock LLM）
"""

import pytest
from unittest.mock import patch

from src.core.question_bank import QuestionBank, Question
from src.core.grader import Grader


class TestQuestionBank:

    @pytest.fixture
    def bank(self):
        return QuestionBank()

    def test_load_questions(self, bank):
        """应成功加载题目。"""
        assert len(bank._questions) > 0

    def test_get_question_by_id(self, bank):
        """按 ID 查题。"""
        q = bank.get_question("q_quad_001")
        assert q is not None
        assert q.knowledge_id == "quadratic_eq"
        assert q.type == "choice"

    def test_get_by_knowledge(self, bank):
        """按知识点查题。"""
        questions = bank.get_by_knowledge("quadratic_eq")
        assert len(questions) >= 2

    def test_get_random(self, bank):
        """随机抽题。"""
        q = bank.get_random("arithmetic", (0, 0.5))
        assert q is not None
        assert q.knowledge_id == "arithmetic"

    def test_get_nonexistent(self, bank):
        """查不存在的题目返回 None。"""
        assert bank.get_question("nonexistent") is None


class TestGrader:

    @pytest.fixture
    def grader(self):
        return Grader()

    # ===== 选择题 =====

    def test_choice_correct(self, grader):
        """选择题答对。"""
        q = Question(
            id="test", knowledge_id="test", type="choice",
            difficulty=0.5, stem="test",
            options={"A": "1", "B": "2"}, answer="A",
        )
        result = grader.grade(q, "A")
        assert result.is_correct is True
        assert result.score == 1.0

    def test_choice_case_insensitive(self, grader):
        """选择题大小写不敏感。"""
        q = Question(
            id="test", knowledge_id="test", type="choice",
            difficulty=0.5, stem="test",
            options={"A": "1", "B": "2"}, answer="A",
        )
        result = grader.grade(q, "a")
        assert result.is_correct is True

    def test_choice_wrong(self, grader):
        """选择题答错。"""
        q = Question(
            id="test", knowledge_id="test", type="choice",
            difficulty=0.5, stem="test",
            options={"A": "1", "B": "2"}, answer="A",
            explanation="答案是A",
        )
        result = grader.grade(q, "B")
        assert result.is_correct is False
        assert "A" in result.feedback

    # ===== 填空题 =====

    def test_fill_exact_number(self, grader):
        """填空题数值精确匹配。"""
        q = Question(
            id="test", knowledge_id="test", type="fill",
            difficulty=0.5, stem="test", answer="15", tolerance=0,
        )
        result = grader.grade(q, "15")
        assert result.is_correct is True

    def test_fill_with_tolerance(self, grader):
        """填空题数值容差匹配。"""
        q = Question(
            id="test", knowledge_id="test", type="fill",
            difficulty=0.5, stem="test", answer="3.14", tolerance=0.01,
        )
        result = grader.grade(q, "3.14159")
        assert result.is_correct is True  # |3.14159-3.14|=0.00159 < 0.01

        result2 = grader.grade(q, "3.2")
        assert result2.is_correct is False  # |3.2-3.14|=0.06 > 0.01

    def test_fill_fraction(self, grader):
        """填空题分数格式。"""
        q = Question(
            id="test", knowledge_id="test", type="fill",
            difficulty=0.5, stem="test", answer="1/3", tolerance=0.01,
        )
        result = grader.grade(q, "1/3")
        assert result.is_correct is True

    def test_fill_string_match(self, grader):
        """填空题字符串匹配。"""
        q = Question(
            id="test", knowledge_id="test", type="fill",
            difficulty=0.5, stem="test", answer="x+3", tolerance=0,
        )
        result = grader.grade(q, "x+3")
        assert result.is_correct is True

        result2 = grader.grade(q, "x + 3")
        assert result2.is_correct is True  # 忽略空格

    # ===== 解答题 =====

    @patch("src.core.grader.chat")
    def test_open_correct(self, mock_chat, grader):
        """解答题 LLM 判正确。"""
        mock_chat.return_value = '{"score": 1.0, "is_correct": true, "feedback": "完全正确"}'
        q = Question(
            id="test", knowledge_id="test", type="open",
            difficulty=0.5, stem="求解 x+1=0",
            answer="x=-1", rubric=["得到 x=-1"],
        )
        result = grader.grade(q, "x=-1")
        assert result.is_correct is True
        assert result.score == 1.0
        assert mock_chat.called

    @patch("src.core.grader.chat")
    def test_open_partial(self, mock_chat, grader):
        """解答题部分正确。"""
        mock_chat.return_value = '{"score": 0.5, "is_correct": false, "feedback": "思路正确但计算错误"}'
        q = Question(
            id="test", knowledge_id="test", type="open",
            difficulty=0.5, stem="test", answer="x=-1",
            rubric=["步骤正确", "答案正确"],
        )
        result = grader.grade(q, "x=1")
        assert result.is_correct is False
        assert result.score == 0.5

    @patch("src.core.grader.chat")
    def test_open_llm_error_fallback(self, mock_chat, grader):
        """LLM 返回异常时降级处理。"""
        mock_chat.return_value = "这不是JSON格式"
        q = Question(
            id="test", knowledge_id="test", type="open",
            difficulty=0.5, stem="test", answer="x=-1",
        )
        result = grader.grade(q, "随便写的")
        assert result.is_correct is False
        assert "异常" in result.feedback
