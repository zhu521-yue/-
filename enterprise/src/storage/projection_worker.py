import asyncio
import json
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
import asyncpg
import redis.asyncio as aioredis
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

async def update_student_state(conn,stream_id:str,event_type:str,data:dict):
    if event_type == "STUDENT_ANSWER":
        mastery_json = json.dumps({data.get("knowledge_id"):data.get("mastery",0)})
        await conn.execute(
            """ 
            INSERT INTO student_state (learner_id, mastery, session_state, engagement_state, last_activity, total_submissions)
            VALUES ($1, $2::jsonb, $3, $4, NOW(), 1)
            ON CONFLICT (learner_id) DO UPDATE SET
                mastery = student_state.mastery || $2::jsonb,
                session_state = $3,
                engagement_state = $4,
                last_activity = NOW(),
                total_submissions = student_state.total_submissions + 1 
        """,stream_id, mastery_json, data.get("session_state", "ONBOARDING"), data.get("engagement_state", "FOCUSED")
        )
    elif event_type == "TEACHING_INTERACTION":
        await conn.execute("""
            INSERT INTO student_state (learner_id, session_state, engagement_state, last_activity)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (learner_id) DO UPDATE SET
                session_state = $2,
                engagement_state = $3,
                last_activity = NOW()
        """, stream_id, data.get("session_state", "ONBOARDING"), data.get("engagement_state", "FOCUSED"))

async def run_projection_loop(pool, redis_client):
    """后台投影循环（被 app startup 启动为 asyncio task）。"""
    last_id = "0"
    logger.info("[ProjectionWorker] 后台投影任务启动")
    try:
        while True:
            messages = await redis_client.xread({"event_stream": last_id}, block=5000, count=10)
            if messages:
                for stream_name, entries in messages:
                    for entry_id, fields in entries:
                        stream_id = fields.get(b'stream_id', b'').decode('utf-8')
                        event_type = fields.get(b'event_type', b'').decode('utf-8')
                        data = json.loads(fields.get(b'data', b'{}').decode('utf-8'))
                        async with pool.acquire() as conn:
                            await update_student_state(conn, stream_id, event_type, data)
                        last_id = entry_id
                        logger.info(f"[ProjectionWorker] Projected: {event_type} for {stream_id}")
    except asyncio.CancelledError:
        logger.info("[ProjectionWorker] 后台投影任务已停止")
# 独立运行版本
async def run_worker():
    pool = await asyncpg.create_pool(DATABASE_URL)
    redis_client = aioredis.from_url(REDIS_URL)
    await run_projection_loop(pool, redis_client)

if __name__ == "__main__":
    asyncio.run(run_worker())
