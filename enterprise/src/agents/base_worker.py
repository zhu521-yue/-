from abc import ABC, abstractmethod
from loguru import logger

class BaseWorker(ABC):
    """Worker Agent 基类，所有 worker 必须实现 execute 方法"""
    def __init__(self,name:str):
        self.name = name
    
    @abstractmethod
    async def execute(self,context:dict)->dict:
        """
        执行任务

        参数：
            context: 包含任务所需的所有信息
                - learner_id: 学生ID
                - knowledge_id: 知识点ID
                - mastery: 掌握度
                - mastery_level: 掌握等级
                - message: 学生消息
                - plan: 教学计划（可选）
                - ...

        返回：
            dict: 执行结果
                - response: 生成的内容
                - metadata: 额外信息
        """
        pass

    def __repr__(self):
        return f"<{self.name}>" 