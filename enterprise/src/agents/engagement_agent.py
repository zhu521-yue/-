"""
EngagementAgent — 情绪干预 Agent（规则路由 + LLM 生成）
职责：
  - 规则层：根据情绪状态 + 时间维度决定干预类型（确定性）
  - LLM 层：生成个性化干预内容（仅在需要干预时调用）
  - 返回 suggested_action 供 Coordinator 路由
设计要点：
  - FOCUSED 状态且无时间异常时短路返回，不调 LLM
  - 时间维度优先级高于 FSM 状态（疲劳/闲置需要立即干预）
  - 6 种状态：FOCUSED / STRUGGLING / FRUSTRATED / BORED / FATIGUED / IDLE
"""
from src.agents.base_worker import BaseWorker
from src.core.llm_client import chat
from src.core.prompt_loader import load_prompt
from loguru import logger
# 规则层：FSM 情绪状态 → (干预类型, Coordinator路由建议)
INTERVENTION_RULES = {
    "FOCUSED": ("none", "continue"),
    "STRUGGLING": ("encourage", "hint"),
    "FRUSTRATED": ("hint_escalate", "direct_hint"),
    "BORED": ("challenge", "advance"),
    "NEED_BREAK": ("force_break", "break"),
}
class EngagementAgent(BaseWorker):
    def __init__(self):
        super().__init__(name="EngagementAgent")
    def _decide_intervention(
        self,
        engagement_state: str,
        session_duration: float,
        idle_seconds: float,
        recent_accuracy: float,
    ) -> tuple[str, str]:
        """
        规则层：综合 FSM 状态 + 时间维度做决策。
        优先级：idle > fatigue > FSM 状态
        """
        # 时间维度优先（这些 FSM 检测不到）
        if idle_seconds > 300:
            return ("idle_alert", "pause")
        if session_duration > 2700 and recent_accuracy < 0.5:
            return ("fatigue", "break")
        # FSM 状态
        return INTERVENTION_RULES.get(engagement_state, ("none", "continue"))
    
    
    async def execute(self, context: dict) -> dict:
        engagement_state = context.get("engagement_state", "FOCUSED")
        learner_id = context.get("learner_id", "")
        session_duration = context.get("session_duration", 0)
        idle_seconds = context.get("idle_seconds", 0)
        recent_accuracy = context.get("recent_accuracy", 1.0)
        # 1. 规则层决策
        intervention_type, suggested_action = self._decide_intervention(
            engagement_state, session_duration, idle_seconds, recent_accuracy
        )
        # 2. FOCUSED + 无时间异常 → 短路返回
        if intervention_type == "none":
            logger.info(f"[EngagementAgent] {learner_id} FOCUSED, 无需干预")
            return {
                "response": "",
                "metadata": {
                    "agent": self.name,
                    "engagement_state": engagement_state,
                    "intervention_type": "none",
                    "suggested_action": "continue",
                },
            }
        # 3. LLM 生成个性化干预内容
        prompt = load_prompt("engagement")
        system_prompt = prompt["instruction"]
        user_message = (
            f"学生当前情绪状态：{engagement_state}\n"
            f"干预类型：{intervention_type}\n"
            f"知识点：{context.get('knowledge_id', '')}\n"
            f"掌握度：{context.get('mastery', 0):.0%}\n"
            f"连续错误次数：{context.get('consecutive_errors', 0)}\n"
            f"学习时长：{session_duration / 60:.0f} 分钟\n"
            f"闲置时间：{idle_seconds:.0f} 秒\n"
            f"\n请生成干预内容。"
        )
        response = chat(system_prompt, user_message,model="gpt").strip()
        logger.info(
            f"[EngagementAgent] {learner_id} state={engagement_state}, "
            f"intervention={intervention_type}, action={suggested_action}"
        )
        return {
            "response": response,
            "metadata": {
                "agent": self.name,
                "engagement_state": engagement_state,
                "intervention_type": intervention_type,
                "suggested_action": suggested_action,
            },
        }