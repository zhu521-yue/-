import asyncpg 
import json
import os
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
import redis.asyncio as aioredis
REDIS_URL = os.getenv("REDIS_URL")

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

class EventStore:
    def __init__(self):
        self._pool = None
    
    async def connect(self):
        self._pool = await asyncpg.create_pool(DATABASE_URL)
        self._redis = aioredis.from_url(REDIS_URL)
        logger.info("EventStore Connected to PostgreSQL and Redis")
    
    async def close(self):
        if self._pool:
            await self._pool.close()
        if self._redis:
            await self._redis.close()
        logger.info("EventStore Closed PostgreSQL and Redis Connection")


    async def append(self, stream_id: str, event_type: str, source: str, data:    
    dict):
            """写入一条事件"""
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO events (stream_id, event_type, source, data)
                    VALUES ($1, $2, $3, $4)
                    """,
                    stream_id, event_type, source, json.dumps(data)
                )
            await self._redis.xadd("event_stream",{
                "stream_id":stream_id,
                "event_type":event_type,
                "source":source,
                "data":json.dumps(data),
            })
            logger.info(f"Event appended: {event_type} for {stream_id}")
    async def get_events(self, stream_id: str, event_type: str = None, limit: int 
    = 50) -> list:
        """读取事件"""
        async with self._pool.acquire() as conn:
            if event_type:
                rows = await conn.fetch(
                    """
                    SELECT * FROM events
                    WHERE stream_id = $1 AND event_type = $2
                    ORDER BY created_at DESC LIMIT $3
                    """,
                    stream_id, event_type, limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM events
                    WHERE stream_id = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    stream_id, limit
                )
            return [dict(row) for row in rows]
# 全局单例
event_store = EventStore()