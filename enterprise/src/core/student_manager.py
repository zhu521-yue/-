from src.core.learner_model import LearnerModel
from src.core.engagement_fsm import create_engagement_fsm
from src.core.state_machine import FSM, Transition
from src.core.session_fsm import create_session_fsm
from src.core.engagement_tracker import EngagementTracker
from src.core.session_tracker import SessionTracker
import json
from loguru import logger
from src.core.spaced_repetition import SpacedRepetition, ReviewItem
# 用于管理所有学生的状态
class StudentManager:
    def __init__(self):
        self._models:dict[str, LearnerModel] = {}
        self._session_fsm:dict[str,FSM] = {}
        self._engagement_fsm:dict[str,FSM] = {}
        self._engagement_trackers:dict[str,EngagementTracker] = {}
        self._session_trackers:dict[str,SessionTracker] = {}
        self._review_items: dict[str, dict[str, ReviewItem]] = {}  # {learner_id: {knowledge_id: ReviewItem}}
        self._sr = SpacedRepetition()


    def get_model(self,learner_id:str)->LearnerModel:
        if learner_id not in self._models:
            self._models[learner_id] = LearnerModel(learner_id)
        return self._models[learner_id]
    
    def get_session_fsm(self,learner_id:str)->FSM:
        if learner_id not in self._session_fsm:
            self._session_fsm[learner_id] = create_session_fsm()
        return self._session_fsm[learner_id]
    # 跨状态机联动
    def get_engagement_fsm(self,learner_id:str)->FSM:
        if learner_id not in self._engagement_fsm:
            engagement_fsm = create_engagement_fsm()
            session_fsm = self.get_session_fsm(learner_id)
            engagement_fsm.on_enter("NEED_BREAK", lambda: session_fsm.trigger("force_break"))
            self._engagement_fsm[learner_id] = engagement_fsm
        return self._engagement_fsm[learner_id]
    
    # 创建一个状态跟踪器
    def get_engagement_tracker(self,learner_id:str)->EngagementTracker:
        if learner_id not in self._engagement_trackers:
            self._engagement_trackers[learner_id] = EngagementTracker(learner_id)
        return self._engagement_trackers[learner_id]
    
    # 创建一个会话状态跟踪器
    def get_session_tracker(self,learner_id:str)->SessionTracker:
        if learner_id not in self._session_trackers:
            self._session_trackers[learner_id] = SessionTracker(learner_id)
        return self._session_trackers[learner_id]

    def get_review_items(self, learner_id: str) -> dict[str, ReviewItem]:
        if learner_id not in self._review_items:
            self._review_items[learner_id] = {}
        return self._review_items[learner_id]

    def update_review(self, learner_id: str, knowledge_id: str, mastery: float) -> ReviewItem:
        """答题后更新 SM-2 复习计划。"""
        items = self.get_review_items(learner_id)
        if knowledge_id not in items:
            items[knowledge_id] = ReviewItem(knowledge_id=knowledge_id)

        # mastery 映射为 quality
        quality = self._mastery_to_quality(mastery)
        items[knowledge_id] = self._sr.review(items[knowledge_id], quality)
        return items[knowledge_id]

    def get_due_reviews(self, learner_id: str) -> list[ReviewItem]:
        """获取到期需要复习的知识点。"""
        items = list(self.get_review_items(learner_id).values())
        return self._sr.get_due_items(items)

    def _mastery_to_quality(self, mastery: float) -> int:
        """mastery 映射为 SM-2 的 quality (0-5)。"""
        if mastery >= 0.90:
            return 5
        elif mastery >= 0.75:
            return 4
        elif mastery >= 0.60:
            return 3
        elif mastery >= 0.40:
            return 2
        elif mastery >= 0.20:
            return 1
        else:
            return 0


    # 从数据库恢复学生状态
    async def restore_from_db(self,learner_id:str):
        from src.storage.event_store import event_store
        async with event_store._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM student_state WHERE learner_id = $1",
                learner_id,
            )
        if row:
            # 恢复熟练度
            model = self.get_model(learner_id)
            mastery_data = row["mastery"]
            if isinstance(mastery_data, str):
                mastery_data = json.loads(mastery_data)
            for knowledge_id,mastery_value in mastery_data.items():
                state = model.get_state(knowledge_id)
                state.mastery = mastery_value

            # 恢复状态机
            session_fsm = self.get_session_fsm(learner_id)
            engagement_fsm = self.get_engagement_fsm(learner_id)
            # 直接设置当前状态
            session_fsm._current_state = row["session_state"]
            engagement_fsm._current_state = row["engagement_state"]
            logger.info(f"Restored state for {learner_id} from DB")
            return True
        return False


student_manager = StudentManager()