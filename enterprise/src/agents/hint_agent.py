""" 职责：根据学生卡住的程度，给出分级提示（三级：元认知 → 脚手架 → 直接提示） """

from src.agents.base_worker import BaseWorker
from src.core.llm_client import chat
from src.core.prompt_loader import load_prompt
from src.storage.rag import hybrid_rag
from loguru import logger

class HintAgent(BaseWorker):
    def __init__(self):
        super().__init__(name="HintAgent")

    def _determine_hint_level(self,context:dict)->int:
        """根据学生状态决定提示级别"""
        mastery = context.get("mastery", 0)
        attempts = context.get("attempts", 0)
        engagement_state = context.get("engagement_state", "FOCUSED")
        if mastery < 0.15 and attempts >= 3:
            return 3  # 直接提示
        elif engagement_state == "FRUSTRATED":
            return 2  # 脚手架
        elif attempts <= 1:
            return 1  # 元认知
        elif attempts <= 3:
            return 2
        else:
            return 3
        
    async def execute(self,context:dict)->dict:
        hint_level = self._determine_hint_level(context)
        # 加载 prompt
        hint_prompt = load_prompt("hint")
        system_prompt = hint_prompt["instruction"]

        # RAG 检索常见错误
        rag_context = await hybrid_rag(
            context.get("message", ""),
            context.get("knowledge_id", "")
        )

        level_desc = {1: "元认知提示", 2: "脚手架提示", 3: "直接提示"}

        user_message = (
            f"知识点：{context.get('knowledge_id', '')}\n"
            f"学生水平：{context.get('mastery_level', 'beginner')}\n"
            f"提示级别：{hint_level} - {level_desc[hint_level]}\n"
            f"学生的问题：{context.get('message', '')}\n"
            f"\n参考资料：\n{rag_context}\n"
            f"\n请根据提示级别生成对应的提示内容。"
        )

        response = chat(system_prompt, user_message,model="gpt").strip()
        logger.info(f"[HintAgent] 生成 Level {hint_level} 提示")

        return {
            "response": response,
            "metadata": {
                "agent": self.name,
                "hint_level": hint_level,
                "hint_type": level_desc[hint_level],
            }
        }