from src.core.state_machine import FSM, Transition

def create_session_fsm()->FSM:
    states = ["ONBOARDING", "LEARNING", "PRACTICING", "REVIEWING", "BREAK"]
    transitions = [
          Transition("ONBOARDING", "start_learning", "LEARNING"),
          Transition("LEARNING", "start_practice", "PRACTICING"),
          Transition("PRACTICING", "start_review", "REVIEWING"),
          Transition("REVIEWING", "finish_review", "LEARNING"),
          # 任何状态都可以强制休息
          Transition("ONBOARDING", "force_break", "BREAK"),
          Transition("LEARNING", "force_break", "BREAK"),
          Transition("PRACTICING", "force_break", "BREAK"),
          Transition("REVIEWING", "force_break", "BREAK"),
          # 休息后恢复
          Transition("BREAK", "resume", "LEARNING"),
      ]
    return FSM(states, transitions, initial_state="ONBOARDING")

if __name__ == "__main__":
    fsm = create_session_fsm()
    print(fsm.current_state)          # ONBOARDING
    fsm.trigger("start_learning")     # → LEARNING
    print(fsm.current_state)          # LEARNING
    fsm.trigger("force_break")        # → BREAK
    print(fsm.current_state)          # BREAK
    fsm.trigger("start_practice")     # 非法转移，应该警告
    print(fsm.current_state)          # 还是 BREAK