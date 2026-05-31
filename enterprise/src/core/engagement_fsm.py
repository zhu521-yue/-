from src.core.state_machine import FSM, Transition

def create_engagement_fsm()->FSM:
    states = ["FOCUSED", "STRUGGLING", "FRUSTRATED", "BORED", "NEED_BREAK"]
    transitions = [
          Transition("FOCUSED", "error", "STRUGGLING"),
          Transition("FOCUSED", "too_easy", "BORED"),
          Transition("STRUGGLING", "repeated_error", "FRUSTRATED"),
          Transition("STRUGGLING", "success", "FOCUSED"),
          Transition("STRUGGLING", "error", "STRUGGLING"),
          Transition("FRUSTRATED", "continued_failure", "NEED_BREAK"),
          Transition("FRUSTRATED", "encouragement", "STRUGGLING"),
          Transition("FRUSTRATED", "success", "STRUGGLING"), 
          Transition("BORED", "challenge", "FOCUSED"),
          Transition("NEED_BREAK", "rest_complete", "FOCUSED"),
      ]
    return FSM(states, transitions, initial_state="FOCUSED")

if __name__ == "__main__":
    fsm = create_engagement_fsm()
    print(fsm.current_state)            # FOCUSED
    fsm.trigger("error")                # → STRUGGLING
    fsm.trigger("repeated_error")       # → FRUSTRATED
    fsm.trigger("continued_failure")    # → NEED_BREAK
    fsm.trigger("error")                # 非法转移
    print(fsm.current_state) 