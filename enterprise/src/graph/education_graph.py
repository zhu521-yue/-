from langgraph.graph import StateGraph,END
from typing import TypedDict
from loguru import logger
from src.core.llm_client import chat
from src.core.prompt_loader import load_prompt
from src.core.student_manager import student_manager
from src.storage.rag import hybrid_rag

from src.agents.tutor_agent import TutorAgent
from src.agents.hint_agent import HintAgent
from src.agents.curriculum_agent import CurriculumAgent
from src.agents.engagement_agent import EngagementAgent
# 实例化 workers（模块级别，复用）
tutor_agent = TutorAgent()
hint_agent = HintAgent()
curriculum_agent = CurriculumAgent()
engagement_agent = EngagementAgent()

class GraphState(TypedDict):
    """图状态定义"""
    learner_id: str
    message:str
    current_node:str
    # 路由意图
    intent:str
    # 教学计划
    plan:str
    response:str
    evaluation:str
    # 学生状态信息
    mastery:float
    mastery_level:str
    knowledge_id:str
    # 重试次数
    retry_count:int

    # 会话状态
    session_state:str
    # 参与状态
    engagement_state:str
    # 空闲时间
    idle_seconds:float
    # 会话时长
    session_duration:float

def Router(state:GraphState):
    router_prompt = load_prompt("router")
    system_prompt = router_prompt["instruction"]
    intent = chat(system_prompt,state["message"]).strip()
    if intent not in ["learn","chat"]:
        intent = "chat"
    model = student_manager.get_model(state["learner_id"])
    knowledge_id = state.get("knowledge_id","quadratic_eq")
    ks=model.get_state(knowledge_id)
    session_fsm = student_manager.get_session_fsm(state["learner_id"])
    engagement_fsm = student_manager.get_engagement_fsm(state["learner_id"])
    session_tracker = student_manager.get_session_tracker(state["learner_id"])
    session_tracker.on_chat(intent,ks.mastery,session_fsm)
    logger.info(f"[node1]处理中，意图分类为: {intent}")
    return {"current_node":"router","intent":intent,"knowledge_id":knowledge_id,"mastery":ks.mastery,"mastery_level":ks.level.value,"session_state":session_fsm.current_state,"engagement_state":engagement_fsm.current_state}
    
def Planner(state:GraphState):
    planner_prompt = load_prompt("planner")
    system_prompt = planner_prompt["instruction"]
    user_message = f"学生的问题：{state['message']}\n学生当前水平：{state['mastery_level']}\n掌握度：{state['mastery']:.0%}"  
    plan = chat(system_prompt,user_message,model="gpt").strip()
    retry_count = state.get("retry_count",0)+1    
    logger.info(f"[node2]处理中，计划为: {plan}")
    logger.info(f"[node2]重试次数为: {retry_count}")
    return {"current_node":"node2","plan":plan,"retry_count":retry_count}

async def Coordinator(state:GraphState):
    learner_id = state["learner_id"]

    # 1. 从后端获取 recent_accuracy 和 consecutive_errors
    model = student_manager.get_model(learner_id)
    progress = model.get_overall_progress()
    tracker = student_manager.get_engagement_tracker(learner_id)

    # 2. 组装 context
    context = {
        "learner_id": learner_id,
        "message": state["message"],
        "knowledge_id": state["knowledge_id"],
        "mastery": state["mastery"],
        "mastery_level": state["mastery_level"],
        "plan": state.get("plan", ""),
        "engagement_state": state["engagement_state"],
        "session_state": state["session_state"],
        # 前端传入
        "session_duration": state.get("session_duration", 0),
        "idle_seconds": state.get("idle_seconds", 0),
        # 后端计算
        "recent_accuracy": progress.get("accuracy", 1.0),
        "consecutive_errors": tracker.consecutive_errors,
        # HintAgent 需要
        "attempts": model.get_state(state["knowledge_id"]).attempts,
    }

    # 3. 先问 EngagementAgent
    engagement_result = await engagement_agent.execute(context)
    suggested_action = engagement_result["metadata"]["suggested_action"]

    # 4. 根据 suggested_action 路由到对应 Worker
    if suggested_action in ("break", "pause"):
        response = engagement_result["response"]

    elif suggested_action == "direct_hint":
        context["attempts"] = 3  # 强制 Level 3
        hint_result = await hint_agent.execute(context)
        response = f"{engagement_result['response']}\n\n{hint_result['response']}"

    elif suggested_action == "advance":
        # 需要传 mastery_data 给 CurriculumAgent
        context["mastery_data"] = {
            kid: ks.mastery for kid, ks in model.knowledge_states.items()
        }
        curriculum_result = await curriculum_agent.execute(context)
        response = f"{engagement_result['response']}\n\n{curriculum_result['response']}"

    elif suggested_action == "hint":
        hint_result = await hint_agent.execute(context)
        response = f"{engagement_result['response']}\n\n{hint_result['response']}"

    else:
        # continue → TutorAgent 正常教学
        tutor_result = await tutor_agent.execute(context)
        response = tutor_result["response"]

    logger.info(f"[Coordinator] action={suggested_action}, dispatched")
    return {"current_node": "coordinator", "response": response}

def Evaluator(state:GraphState):
    evaluator_prompt = load_prompt("evaluator")
    system_prompt = evaluator_prompt["instruction"]
    user_message = (
        f"教学计划：{state.get('plan', '')}\n"
        f"实际回复：{state['response']}\n"
        f"学生水平：{state['mastery_level']}\n"
        f"\n请评估回复是否符合教学计划，返回 JSON：\n"
        f'{{"result": "pass/fail", "reason": "原因"}}'
    )

    evaluation = chat(system_prompt, user_message).strip()

    # 解析结果
    result = "pass"
    try:
        import json
        parsed = json.loads(evaluation)
        result = parsed.get("result", "pass")
    except (json.JSONDecodeError, KeyError):
        if "fail" in evaluation.lower():
            result = "fail"
        else:
            result = "pass"

    # 冷却期：retry_count >= 2 强制 pass
    if state.get("retry_count", 0) >= 2:
        result = "pass"
        logger.info("[Evaluator] 达到重试上限，强制 pass")

    logger.info(f"[Evaluator] result={result}, retry={state.get('retry_count', 0)}")
    return {"current_node": "evaluator", "evaluation": result}
def route_by_intent(state: GraphState) -> str:
    return state["intent"]
def route_by_evaluation(state: GraphState) -> str:
    if state["evaluation"] == "pass":
          return "pass"
    if state.get("retry_count", 0) >= 2:
          return "pass"  # 已经重试2次了，不再循环，强制结束
    return "fail"
education_graph = StateGraph(GraphState)
education_graph.add_node("Router",Router)
education_graph.add_node("Planner",Planner)
education_graph.add_node("Coordinator",Coordinator)
education_graph.add_node("Evaluator",Evaluator)
education_graph.add_conditional_edges("Router",
                                      route_by_intent,
                                      {
                                          "learn":"Planner",
                                          "chat":"Coordinator",
                                      })


education_graph.add_edge("Planner","Coordinator")
education_graph.add_edge("Coordinator","Evaluator")
education_graph.add_conditional_edges(
    "Evaluator",
    route_by_evaluation,
    {
        "pass":END,
        "fail":"Planner",
    }
)
workflow =education_graph.set_entry_point("Router")
graph = workflow.compile()

if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await graph.ainvoke({"learner_id":"123","message":"我想学习一元二次方程","current_node":""})
        logger.info("Graph execution completed")
        print(result)

    asyncio.run(main())
