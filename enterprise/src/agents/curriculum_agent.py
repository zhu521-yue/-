"""   职责：
  - 根据学生当前 mastery，推荐下一个可学习的知识点
  - 检查 SM-2 复习计划，看有没有到期需要复习的
  - 生成学习路径建议

  这个 agent 不需要调 LLM，它是纯算法驱动的（知识图谱 + SM-2）： """

from src.agents.base_worker import BaseWorker
from src.core.knowledge_graph import KnowledgeGraph
from src.core.spaced_repetition import SpacedRepetition, ReviewItem
from pathlib import Path
from loguru import logger
from src.core.student_manager import student_manager
DATA_PATH = Path(__file__).parent.parent / "data" / "math_graph.yaml"
class CurriculumAgent(BaseWorker):
    def __init__(self):
        super().__init__(name="CurriculumAgent")
        self._graph = KnowledgeGraph.from_yaml(str(DATA_PATH))
        self._sr = SpacedRepetition()
    async def execute(self, context: dict) -> dict:
        mastery_data = context.get("mastery_data", {})  # {knowledge_id: mastery_value}
        current_knowledge_id = context.get("knowledge_id", "")
        session_state = context.get("session_state", "LEARNING")
        learner_id = context.get("learner_id", "")

        # 0. 检查是否有到期复习（优先级最高）
        due_reviews = student_manager.get_due_reviews(learner_id)
        if due_reviews:
            due_ids = [r.knowledge_id for r in due_reviews[:3]]
            due_names = [self._graph.nodes[rid].name for rid in due_ids if rid in self._graph.nodes]
            response = (
                f"📝 复习提醒：\n"
                f"- 有 {len(due_reviews)} 个知识点需要复习\n"
                f"- 优先复习：{', '.join(due_names)}\n"
                f"- 根据遗忘曲线，现在复习效果最好！\n"
            )
            logger.info(f"[CurriculumAgent] 推荐复习: {due_ids}")
            return {
                "response": response,
                "metadata": {
                    "agent": self.name,
                    "mode": "review",
                    "due_reviews": due_ids,
                    "recommended": due_ids[0],
                },
            }
        
        # 1. 找出已掌握的知识点（mastery >= 0.6）
        mastered_ids = {kid for kid, m in mastery_data.items() if m >= 0.6}
        # 2. 获取可学习的下一批知识点
        ready_nodes = self._graph.get_ready_nodes(mastered_ids)
        # 3. 如果有目标知识点，生成学习路径
        learning_path = []
        if current_knowledge_id:
            learning_path = self._graph.get_learning_path(current_knowledge_id, mastered_ids)
        # 4. 决定模式：复习阶段自动安排，学习阶段建议学生选
        if session_state == "REVIEWING":
            mode = "auto"
        else:
            mode = "suggest"
        # 5. 组装建议
        recommended = ready_nodes[0] if ready_nodes else None
        recommended_name = self._graph.nodes[recommended].name if recommended else "无"
        option_names = [self._graph.nodes[nid].name for nid in ready_nodes[:5]]

        response = (
            f"学习路径建议：\n"
            f"- 已掌握：{len(mastered_ids)} 个知识点\n"
            f"- 推荐下一个：{recommended_name}\n"
            f"- 可选知识点：{', '.join(option_names)}\n"
        )
        if learning_path:
            path_names = [self._graph.nodes[nid].name for nid in learning_path]
            response += f"- 到达目标的路径：{' → '.join(path_names)}\n"

        logger.info(f"[CurriculumAgent] 推荐: {recommended_name}, 模式: {mode}")

        return {
            "response": response,
            "metadata": {
                "agent": self.name,
                "recommended": recommended,
                "options": ready_nodes[:5],
                "learning_path": learning_path,
                "mode": mode,
            }
        }