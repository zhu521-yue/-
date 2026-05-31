from pathlib import Path
from loguru import logger
from src.storage.vector_store import vector_store
from src.core.knowledge_graph import KnowledgeGraph
DATA_PATH = Path(__file__).parent.parent / "data" / "math_graph.yaml"
graph = KnowledgeGraph.from_yaml(str(DATA_PATH))

def graph_rag(knowledge_id:str)->list[str]:
    """GraphRAG：从知识图谱结构中获取相关内容"""
    node = graph.nodes.get(knowledge_id)
    if not node:
        return []
    results = []
    # 常见错误
    for error in node.common_errors:
        results.append(f"[常见错误] {error}")
    # 教学类比
    for analogy in node.teaching_analogies:
        results.append(f"[教学类比] {analogy}")
    # 关键公式
    for formula in node.key_formulas:
        results.append(f"[关键公式] {formula}")
    # 关联知识点
    for related_id in node.related_to:
        related_node = graph.nodes.get(related_id)
        if related_node:
            results.append(f"[关联知识点] {related_node.name}")
    
    
    return results


async def vector_rag(query:str,limit:int=3)->list[str]:
    """Vector RAG：按语义相似度检索（模型不可用时返回空）"""
    from src.storage.vector_store import model
    if model is None:
        return []
    results = await vector_store.search(query,limit=limit)
    return [f"[{row['content_type']}] {row['content']}" for row in results]

async def hybrid_rag(query:str,knowledge_id:str = "",limit:int=5)->str:
    """Hybrid RAG：结合GraphRAG和Vector RAG,返回拼接好的上下文"""
    context_parts = []
    # GraphRAG(如果有明确的知识点)
    if knowledge_id:
        graph_results = graph_rag(knowledge_id)
        context_parts.extend(graph_results)

    vector_results = await vector_rag(query,limit=limit)
    context_parts.extend(vector_results)
    # 去重
    context_parts = list(dict.fromkeys(context_parts))

    context = "\n".join(context_parts)
    logger.info(f"RAG retrieved {len(context_parts)} items for: {query[:20]}...")
    return context



