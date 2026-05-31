"""   Tutor Agent 的职责：
  - 根据学生水平和教学计划，生成引导式教学内容
  - 使用 RAG 检索相关知识作为参考
  - 调用 LLM 生成苏格拉底式回复 """

from src.agents.base_worker import BaseWorker
from src.core.llm_client import chat
from src.core.prompt_loader import load_prompt
from src.storage.rag import hybrid_rag
from loguru import logger

class TutorAgent(BaseWorker):
    def __init__(self):
        super().__init__(name="TutorAgent")

    async def execute(self,context:dict)->dict:
        # 加载prompt
        tutor_prompt = load_prompt("tutor")
        system_prompt = tutor_prompt["instruction"]

        # RAG检索
        rag_context = await hybrid_rag(
            context.get("message",""),
            context.get("knowledge_id","")
        )

        # 组装uesr_message
        user_message = (
            f"学生的问题：{context.get('message', '')}\n"
            f"教学计划：{context.get('plan', '')}\n"
            f"知识点：{context.get('knowledge_id', '')}\n"
            f"学生水平：{context.get('mastery_level', 'beginner')}\n"
            f"掌握度：{context.get('mastery', 0):.0%}\n"
            f"\n参考资料：\n{rag_context}\n"
            f"\n请用苏格拉底式提问生成教学内容，引导学生思考而非直接给答案。"
        )

        # 调用LLM
        response = chat(system_prompt,user_message,model="gpt").strip()
        logger.info(f"[TutorAgent] 生成教学内容完成")
        return {
            "response":response,
            "metadata":{
                "agent":self.name,
                "style":"socratic",
                "rag_used":True
            }
        }
