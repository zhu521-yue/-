"""   
AssessmentAgent — 评估 Agent（纯算法驱动）
     
  职责：
    - 接收答题结果，执行 BKT 更新
    - 触发情绪状态机 + 学习阶段状态机
    - 生成结构化评估报告
  
  设计要点：
    - Single Writer 原则：只有 AssessmentAgent 更新 mastery
    - 不调 LLM，纯算法驱动，延迟极低
    - 封装所有"答题后"的副作用（BKT + 状态机 + 报告）
 """

from src.agents.base_worker import BaseWorker
from src.core.student_manager import student_manager
from src.core.learner_model import MasteryLevel
from pathlib import Path
from loguru import logger

class AssessmentAgent(BaseWorker):
    def __init__(self):
        super().__init__(name="AssessmentAgent")

    async def execute(self,context:dict)->dict:
        learner_id = context["learner_id"]
        knowledge_id = context["knowledge_id"]
        is_correct = context["is_correct"]
        # 1. BKT 更新（Single Writer）
        model = student_manager.get_model(learner_id)
        old_state = model.get_state(knowledge_id)
        old_mastery = old_state.mastery
        old_level = old_state.level

        ks = model.update_mastery(knowledge_id, is_correct)        
        # 2. 触发情绪状态机
        engagement_fsm = student_manager.get_engagement_fsm(learner_id)
        tracker = student_manager.get_engagement_tracker(learner_id)
        tracker.on_answer(is_correct, ks.mastery, engagement_fsm)

        # 3. 触发学习阶段状态机
        session_fsm = student_manager.get_session_fsm(learner_id)
        session_tracker = student_manager.get_session_tracker(learner_id)
        session_tracker.on_answer(knowledge_id, is_correct, ks.mastery, session_fsm)
        
        # 4. 更新 SM-2 复习计划（新增）
        review_item = student_manager.update_review(learner_id, knowledge_id, ks.mastery)
        # 5. 判断等级是否变化
        level_changed = old_level != ks.level

        # 6. 获取薄弱点
        weak_points = [
            {"id": wp.knowledge_id, "mastery": round(wp.mastery, 3)}
            for wp in model.get_weak_points(threshold=0.4, limit=5)
        ]

        # 7. 整体进度
        progress = model.get_overall_progress()

        # 8. 生成评估报告
        response = self._build_report(
            knowledge_id, is_correct, old_mastery,
            ks.mastery, ks.level, level_changed,
            weak_points, progress,
        )

        logger.info(
            f"[AssessmentAgent] {learner_id}/{knowledge_id} "
            f"correct={is_correct}, mastery: {old_mastery:.3f} → {ks.mastery:.3f}"
        )

        return {
            "response": response,
            "metadata": {
                "agent": self.name,
                "knowledge_id": knowledge_id,
                "is_correct": is_correct,
                "mastery": ks.mastery,
                "mastery_level": ks.level.value,
                "level_changed": level_changed,
                "weak_points": weak_points,
                "session_state": session_fsm.current_state,
                "engagement_state": engagement_fsm.current_state,
                "progress": progress,
                "next_review": review_item.next_review.isoformat(),
                "review_interval_days": review_item.interval_days,
            },
        }
    def _build_report(
        self, knowledge_id, is_correct, old_mastery,
        new_mastery, level, level_changed, weak_points, progress,
    ) -> str:
        """生成人类可读的评估报告。"""
        lines = []

        result_emoji = "✅" if is_correct else "❌"
        lines.append(f"{result_emoji} 知识点 [{knowledge_id}] 答题{'正确' if is_correct else '错误'}")

        direction = "↑" if new_mastery > old_mastery else "↓"
        lines.append(f"掌握度：{old_mastery:.0%} {direction} {new_mastery:.0%}（{level.value}）")

        if level_changed:
            lines.append(f"🎉 等级提升！当前等级：{level.value}")

        if weak_points:
            wp_str = "、".join(wp["id"] for wp in weak_points[:3])
            lines.append(f"薄弱知识点：{wp_str}")

        if progress.get("total_knowledge_points", 0) > 0:
            lines.append(
                f"整体进度：{progress['total_knowledge_points']} 个知识点，"
                f"平均掌握度 {progress['avg_mastery']:.0%}，"
                f"正确率 {progress['accuracy']:.0%}"
            )

        return "\n".join(lines)