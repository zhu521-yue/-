import asyncio
from pathlib import Path
from loguru import logger
from src.core.knowledge_graph import KnowledgeGraph
from src.storage.vector_store import vector_store
DATA_PATH = Path(__file__).parent.parent / "data" / "math_graph.yaml"
async def init_embeddings_with_pool():
    """使用已有连接池导入 embeddings（被 main.py startup 调用）。"""
    graph = KnowledgeGraph.from_yaml(str(DATA_PATH))
    count = 0
    for node_id, node in graph.nodes.items():
        for error in node.common_errors:
            await vector_store.insert(node_id, "common_error", error)
            count += 1
        for analogy in node.teaching_analogies:
            await vector_store.insert(node_id, "analogy", analogy)
            count += 1
        for formula in node.key_formulas:
            await vector_store.insert(node_id, "formula", formula)
            count += 1
        if node.description:
            await vector_store.insert(node_id, "description", node.description)
            count += 1
    logger.info(f"[init_embeddings] 导入 {count} 条 embeddings")
async def init_embeddings():
    """独立运行版本（手动执行时用）。"""
    await vector_store.connect()
    await init_embeddings_with_pool()
    await vector_store.close()
if __name__ == "__main__":
    asyncio.run(init_embeddings())