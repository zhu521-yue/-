from src.core.state_machine import FSM



class EngagementTracker:
    def __init__(self,learner_id:str):
        self.consecutive_errors:int =0
        self.consecutive_successes:int =0

    def on_answer(self,is_correct:bool,mastery:float,engagement_fsm:FSM):
        # 根据答题结果触发状态机事件
        if is_correct:
            self.consecutive_successes += 1
            self.consecutive_errors = 0
            if self.consecutive_successes >= 5 and mastery >= 0.9:
                # 触发正确事件
                if engagement_fsm.current_state == "FOCUSED": 
                    # 触发正确事件
                    engagement_fsm.trigger("too_easy")
            elif engagement_fsm.current_state != "FOCUSED":
                # 触发成功事件
                engagement_fsm.trigger("success")
        else:
            self.consecutive_errors += 1
            self.consecutive_successes = 0
            if engagement_fsm.current_state == "FRUSTRATED":
                # 触发错误事件
                engagement_fsm.trigger("continued_failure")
            else:    
                
                if self.consecutive_errors < 3:
                    # 触发错误事件
                    engagement_fsm.trigger("error")
                else:
                    # 触发重复错误事件
                    engagement_fsm.trigger("repeated_error")
