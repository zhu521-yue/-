import json
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
import asyncpg

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

# 尝试加载 embedding 模型（服务器内存不够时优雅降级）
model = None
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
    logger.info("[VectorStore] embedding 模型加载成功")
except Exception as e:
    logger.warning(f"[VectorStore] embedding 模型加载失败，Vector RAG 将不可用: {e}")

def get_embedding(text: str) -> list[float]:
    if model is None:
        return []
    return model.encode(text).tolist()

class VectorStore:
    def __init__(self):
        self._pool = None
    
    async def connect(self):
        self._pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("VectorStore connected")
    
    async def close(self):
        if self._pool:
            await self._pool.close()
            logger.info("VectorStore closed")
    

    async def insert(self, knowledge_id: str, content_type: str, content: str):
        embedding = get_embedding(content)
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO knowledge_embeddings (knowledge_id, content_type, content, embedding)
                VALUES ($1, $2, $3, $4)
            """, knowledge_id, content_type, content, str(embedding))
        logger.info(f"Inserted embedding: {knowledge_id} / {content_type}")

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """根据查询文本检索最相关的内容"""
        query_embedding = get_embedding(query)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT knowledge_id, content_type, content,
                       embedding <=> $1::vector AS distance
                FROM knowledge_embeddings
                ORDER BY distance ASC
                LIMIT $2
            """, str(query_embedding), limit)
        return [dict(row) for row in rows]

vector_store = VectorStore()