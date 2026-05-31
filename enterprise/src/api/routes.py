from src.graph.education_graph import graph
from pydantic import BaseModel
from fastapi import APIRouter
from src.core.student_manager import student_manager
from src.storage.event_store import event_store
from src.core.user_lock import user_lock_manager
router = APIRouter(prefix="/api/v1")
from src.agents.assessment_agent import AssessmentAgent
assessment_agent = AssessmentAgent()
from src.core.grader import grader
from src.core.question_bank import question_bank
class Request(BaseModel):
    learner_id: str
    message:str
    idle_seconds:float = 0
    session_duration:float = 0

class SubmitRequest(BaseModel):
    learner_id:str
    question_id:str
    answer:str

@router.post("/chat")
async def chat(request:Request):
    lock = user_lock_manager.get_lock(request.learner_id)
    
    async with lock:
        if request.learner_id not in student_manager._models:
            await student_manager.restore_from_db(request.learner_id)
        result = await graph.ainvoke({
            "learner_id":request.learner_id,
            "message":request.message,
            "idle_seconds":request.idle_seconds,
            "session_duration":request.session_duration,
            "current_node":""
            })
        await event_store.append(
            stream_id=request.learner_id,
            event_type="TEACHING_INTERACTION",
            source="chat_api",
            data={
                "message": request.message,
                "intent": result.get("intent", ""),
                "plan": result.get("plan", ""),
                "response": result.get("response", ""),
                "evaluation": result.get("evaluation", ""),
                "session_state": result.get("session_state", ""),
                "engagement_state": result.get("engagement_state", ""),
            },
        )
        return {"response":result}

@router.post("/submit")
async def submit_answer(request: SubmitRequest):
    lock = user_lock_manager.get_lock(request.learner_id)
    async with lock:
        if request.learner_id not in student_manager._models:
            await student_manager.restore_from_db(request.learner_id)
        # 1. 查题
        question = question_bank.get_question(request.question_id)
        if not question:
            return {"error": "题目不存在"}
        # 2. 判题
        grade_result = grader.grade(question, request.answer)
        # 3. AssessmentAgent 更新 mastery
        result = await assessment_agent.execute({
            "learner_id": request.learner_id,
            "knowledge_id": question.knowledge_id,
            "is_correct": grade_result.is_correct,
        })
        # 4. 写入事件
        metadata = result["metadata"]
        await event_store.append(
            stream_id=request.learner_id,
            event_type="STUDENT_ANSWER",
            source="submit_api",
            data={
                "question_id": request.question_id,
                "student_answer": request.answer,
                "is_correct": grade_result.is_correct,
                "score": grade_result.score,
                "knowledge_id": question.knowledge_id,
                "mastery": metadata["mastery"],
                "mastery_level": metadata["mastery_level"],
            },
        )
        return {
            "is_correct": grade_result.is_correct,
            "score": grade_result.score,
            "feedback": grade_result.feedback,
            "mastery": metadata["mastery"],
            "mastery_level": metadata["mastery_level"],
            "level_changed": metadata["level_changed"],
            "session_state": metadata["session_state"],
            "engagement_state": metadata["engagement_state"],
            "report": result["response"],
        }
    
@router.get("/question")
async def get_question(knowledge_id: str):
    """随机获取一道题目（不暴露答案）。"""
    question = question_bank.get_random(knowledge_id)
    if not question:
        return {"error": "该知识点暂无题目"}
    # 不返回 answer、rubric（防作弊）
    return {
        "id": question.id,
        "knowledge_id": question.knowledge_id,
        "type": question.type,
        "difficulty": question.difficulty,
        "stem": question.stem,
        "options": question.options,
    }

@router.get("/backgrounds")
async def get_backgrounds():
    """获取背景图片列表。"""
    from pathlib import Path
    img_dir = Path(__file__).parent.parent / "data" / "img"
    images = [f"/static/img/{f.name}" for f in img_dir.iterdir() if f.suffix in ('.jpg', '.png', '.jpeg')]
    return {"images": images}