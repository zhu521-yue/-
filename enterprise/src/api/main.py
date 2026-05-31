from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from src.api.routes import router
from loguru import logger
import sys
from pathlib import Path
from src.storage.event_store import event_store
from src.storage.vector_store import vector_store
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import asyncio
from src.storage.projection_worker import run_projection_loop



logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/app_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days")


app = FastAPI(title="Multi-Agent Education API",version="1.0.0")
app.include_router(router)

# 静态文件服务（背景图片）
IMG_DIR = Path(__file__).parent.parent / "data" / "img"
app.mount("/static/img", StaticFiles(directory=str(IMG_DIR)), name="images")

# 配置 OTel：输出到控制台（后续可改为输出到 Langfuse）
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
# 自动追踪所有 FastAPI 请求
FastAPIInstrumentor.instrument_app(app)

@app.get("/health")
def health_check():
    logger.info("Health check received")
    return {"status":"ok"}

@app.on_event("startup")
async def startup():
    await event_store.connect()
    await vector_store.connect()
    await auto_init_embeddings()
    # 启动 Projection Worker 后台任务
    global _projection_task
    _projection_task = asyncio.create_task(
        run_projection_loop(event_store._pool, event_store._redis)
    )
@app.on_event("shutdown")
async def shutdown():
    # 停止 Projection Worker
    global _projection_task
    if _projection_task:
        _projection_task.cancel()
        try:
            await _projection_task
        except asyncio.CancelledError:
            pass
    await event_store.close()
    await vector_store.close()
    try:
        from langfuse import Langfuse
        Langfuse().flush()
    except Exception:
        pass

async def auto_init_embeddings():
    """启动时检查 embeddings 是否已导入，未导入则自动执行。"""
    try:
        async with vector_store._pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_embeddings")
        if count == 0:
            logger.info("[Startup] knowledge_embeddings 为空，开始导入...")
            from src.storage.init_embeddings import init_embeddings_with_pool
            await init_embeddings_with_pool()
            logger.info("[Startup] embeddings 导入完成")
        else:
            logger.info(f"[Startup] knowledge_embeddings 已有 {count} 条数据，跳过导入")
    except Exception as e:
        logger.warning(f"[Startup] embeddings 初始化失败（不影响启动）: {e}")

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000,reload=True)