# 封装SessionTracker的触发逻辑
from typing import List

from src.core.state_machine import FSM
from src.core.spaced_repetition import SpacedRepetition,ReviewItem
from loguru import logger

class SessionTracker:
    def __init__(self,learner_id:str):
        self._review_items:dict[str,ReviewItem] = {}
        self._sr = SpacedRepetition()

    def on_chat(self,intent:str,mastery:float,session_fsm:FSM):
        # 用户发起会话时，判断是否需要转移学习阶段
        current = session_fsm.current_state
        # ONBOARDING → LEARNING：第一次学习
        if current == "ONBOARDING" and intent == "learn":
            session_fsm.trigger("start_learning")
            logger.info("用户开始学习")
        elif current == "BREAK" and intent == "learn":
            session_fsm.trigger("resume")
            logger.info("用户继续学习")

    def on_answer(self,knowledge_id:str,is_correct:bool,mastery:float,session_fsm:FSM):
        # 答题后，判断是否切换阶段
        current = session_fsm.current_state
        if current == "LEARNING" and mastery > 0.3:
            session_fsm.trigger("start_practice")
        

        if current == "REVIEWING" and is_correct:
            session_fsm.trigger("finish_review")

    def check_review_due(self,review_items:List[ReviewItem],session_fsm:FSM):
        due = self._sr.get_due_items(review_items)
        if due and session_fsm.current_state in ["LEARNING","PRACTICING"]:
            session_fsm.trigger("start_review")
            logger.info("用户开始复习")
        else:
            logger.info("用户当前阶段不是复习阶段，无需开始复习")