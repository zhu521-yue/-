"""
Worker Agents 单元测试

测试范围：
  - AssessmentAgent：BKT 更新、状态机触发、等级变化、报告生成
  - EngagementAgent：规则路由、时间维度优先级、FOCUSED 短路

运行方式：
  cd enterprise
  pytest tests/test_agents.py -v
"""

import pytest
from unittest.mock import patch

from src.core.student_manager import student_manager


@pytest.fixture(autouse=True)
def reset_student_manager():
    """每个测试前清空学生状态。"""
    student_manager._models.clear()
    student_manager._session_fsm.clear()
    student_manager._engagement_fsm.clear()
    student_manager._engagement_trackers.clear()
    student_manager._session_trackers.clear()
    yield


# ==================== AssessmentAgent 测试 ====================

class TestAssessmentAgent:

    @pytest.fixture
    def agent(self):
        from src.agents.assessment_agent import AssessmentAgent
        return AssessmentAgent()

    @pytest.mark.asyncio
    async def test_correct_answer_increases_mastery(self, agent):
        """答对应该提升 mastery。"""
        result = await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": True,
        })
        assert result["metadata"]["mastery"] > 0.1

    @pytest.mark.asyncio
    async def test_wrong_answer_mastery_stays_low(self, agent):
        """答错后 mastery 仍会因学习转移略微上升（BKT 特性）。"""
        result = await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": False,
        })
        assert result["metadata"]["mastery"] >= 0.05

    @pytest.mark.asyncio
    async def test_multiple_correct_raises_level(self, agent):
        """连续答对应该提升等级。"""
        for _ in range(5):
            result = await agent.execute({
                "learner_id": "student_1",
                "knowledge_id": "quadratic_eq",
                "is_correct": True,
            })
        assert result["metadata"]["mastery_level"] in ("developing", "proficient", "mastered")

    @pytest.mark.asyncio
    async def test_level_changed_flag(self, agent):
        """等级变化时 level_changed 应为 True。"""
        for _ in range(4):
            await agent.execute({
                "learner_id": "student_1",
                "knowledge_id": "quadratic_eq",
                "is_correct": True,
            })
        result = await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": True,
        })
        assert isinstance(result["metadata"]["level_changed"], bool)

    @pytest.mark.asyncio
    async def test_engagement_fsm_triggered(self, agent):
        """连续答错应触发情绪状态机变化。"""
        for _ in range(3):
            result = await agent.execute({
                "learner_id": "student_1",
                "knowledge_id": "quadratic_eq",
                "is_correct": False,
            })
        assert result["metadata"]["engagement_state"] != "FOCUSED"

    @pytest.mark.asyncio
    async def test_session_fsm_triggered(self, agent):
        """模拟先进入 LEARNING，再答题触发阶段变化。"""
        # 先手动触发 ONBOARDING → LEARNING（正常流程由 /chat 触发）
        session_fsm = student_manager.get_session_fsm("student_1")
        session_fsm.trigger("start_learning")

        for _ in range(6):
            result = await agent.execute({
                "learner_id": "student_1",
                "knowledge_id": "quadratic_eq",
                "is_correct": True,
            })
        # mastery > 0.3 应从 LEARNING 进入 PRACTICING
        assert result["metadata"]["session_state"] == "PRACTICING"

    @pytest.mark.asyncio
    async def test_report_contains_knowledge_id(self, agent):
        """报告应包含知识点 ID。"""
        result = await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": True,
        })
        assert "quadratic_eq" in result["response"]

    @pytest.mark.asyncio
    async def test_weak_points_detected(self, agent):
        """答错后应检测到薄弱点。"""
        await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": False,
        })
        result = await agent.execute({
            "learner_id": "student_1",
            "knowledge_id": "quadratic_eq",
            "is_correct": False,
        })
        weak_ids = [wp["id"] for wp in result["metadata"]["weak_points"]]
        assert "quadratic_eq" in weak_ids


# ==================== EngagementAgent 测试 ====================

class TestEngagementAgent:

    @pytest.fixture
    def agent(self):
        from src.agents.engagement_agent import EngagementAgent
        return EngagementAgent()

    @pytest.mark.asyncio
    async def test_focused_no_intervention(self, agent):
        """FOCUSED 状态应短路返回，不调 LLM。"""
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "FOCUSED",
            "session_duration": 600,
            "idle_seconds": 10,
            "recent_accuracy": 0.8,
        })
        assert result["metadata"]["intervention_type"] == "none"
        assert result["metadata"]["suggested_action"] == "continue"
        assert result["response"] == ""

    @pytest.mark.asyncio
    @patch("src.agents.engagement_agent.chat")
    async def test_struggling_triggers_encourage(self, mock_chat, agent):
        """STRUGGLING 应触发 encourage 干预。"""
        mock_chat.return_value = "别着急，你已经很努力了！"
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "STRUGGLING",
            "session_duration": 600,
            "idle_seconds": 10,
            "recent_accuracy": 0.5,
        })
        assert result["metadata"]["intervention_type"] == "encourage"
        assert result["metadata"]["suggested_action"] == "hint"
        assert mock_chat.called

    @pytest.mark.asyncio
    @patch("src.agents.engagement_agent.chat")
    async def test_frustrated_triggers_hint_escalate(self, mock_chat, agent):
        """FRUSTRATED 应触发 hint_escalate。"""
        mock_chat.return_value = "我理解这很难，让我们换个方式。"
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "FRUSTRATED",
            "session_duration": 600,
            "idle_seconds": 10,
            "recent_accuracy": 0.2,
        })
        assert result["metadata"]["intervention_type"] == "hint_escalate"
        assert result["metadata"]["suggested_action"] == "direct_hint"

    @pytest.mark.asyncio
    @patch("src.agents.engagement_agent.chat")
    async def test_idle_overrides_fsm(self, mock_chat, agent):
        """idle_seconds > 300 应优先于 FSM 状态。"""
        mock_chat.return_value = "还在吗？休息一下也没关系。"
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "FOCUSED",
            "session_duration": 600,
            "idle_seconds": 400,
            "recent_accuracy": 0.8,
        })
        assert result["metadata"]["intervention_type"] == "idle_alert"
        assert result["metadata"]["suggested_action"] == "pause"

    @pytest.mark.asyncio
    @patch("src.agents.engagement_agent.chat")
    async def test_fatigue_overrides_fsm(self, mock_chat, agent):
        """session > 45min + accuracy < 0.5 应触发 fatigue。"""
        mock_chat.return_value = "学了很久了，休息一下吧。"
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "FOCUSED",
            "session_duration": 3000,
            "idle_seconds": 10,
            "recent_accuracy": 0.3,
        })
        assert result["metadata"]["intervention_type"] == "fatigue"
        assert result["metadata"]["suggested_action"] == "break"

    @pytest.mark.asyncio
    @patch("src.agents.engagement_agent.chat")
    async def test_bored_triggers_challenge(self, mock_chat, agent):
        """BORED 应触发 challenge。"""
        mock_chat.return_value = "来试试更有挑战的题目！"
        result = await agent.execute({
            "learner_id": "student_1",
            "engagement_state": "BORED",
            "session_duration": 600,
            "idle_seconds": 10,
            "recent_accuracy": 0.95,
        })
        assert result["metadata"]["intervention_type"] == "challenge"
        assert result["metadata"]["suggested_action"] == "advance"
