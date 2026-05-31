"""
知识图谱 -- 管理知识点之间的依赖关系。

知识图谱是一个 DAG（有向无环图），用于：
1. 确定学习顺序（拓扑排序）
2. 检查前置知识是否达标
3. 推荐下一个可学习的知识点
"""
import yaml
from loguru import logger
from collections import deque
from pathlib import Path

from pydantic import BaseModel, Field

class KnowledgeNode(BaseModel):
    """知识点节点。"""

    id: str
    name: str
    subject: str = "math"  # 学科
    difficulty: float = 0.5  # 难度 0-1
    description: str = ""
    prerequisites: list[str] = Field(default_factory=list)  # 前置知识点ID列表
    tags: list[str] = Field(default_factory=list)
    # 新增：GraphRAG使用
    related_to: list[str] = Field(default_factory=list)  # 关联概念
    common_errors: list[str] = Field(default_factory=list)  # 常见错误
    teaching_analogies:list[str] = Field(default_factory=list)  # 教学类比
    key_formulas:list[str] = Field(default_factory=list)  # 关键公式


class KnowledgeGraph:
    """
    知识图谱（DAG），管理知识点依赖关系。

    示例（初中数学）：
        加法 → 乘法 → 一元一次方程 → 二元一次方程组
                    → 因式分解 → 一元二次方程
    """

    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeNode] = {}
        self._adjacency: dict[str, list[str]] = {}  # node_id -> 后继节点列表
        self._reverse_adj: dict[str, list[str]] = {}  # node_id -> 前置节点列表

    def add_node(self, node: KnowledgeNode) -> None:
        """添加知识点。"""
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        if node.id not in self._reverse_adj:
            self._reverse_adj[node.id] = []

        for prereq_id in node.prerequisites:
            if prereq_id not in self._adjacency:
                self._adjacency[prereq_id] = []
            self._adjacency[prereq_id].append(node.id)
            self._reverse_adj[node.id].append(prereq_id)

    def get_prerequisites(self, node_id: str) -> list[str]:
        """获取直接前置知识点。"""
        return self._reverse_adj.get(node_id, [])

    def get_successors(self, node_id: str) -> list[str]:
        """获取直接后继知识点。"""
        return self._adjacency.get(node_id, [])

    def get_all_prerequisites(self, node_id: str) -> set[str]:
        """获取所有前置知识点（递归）。"""
        visited: set[str] = set()
        queue = deque(self.get_prerequisites(node_id))
        while queue:
            pid = queue.popleft()
            if pid not in visited:
                visited.add(pid)
                queue.extend(self.get_prerequisites(pid))
        return visited

    def topological_sort(self) -> list[str]:
        """
        拓扑排序 -- Kahn算法。

        返回知识点的学习顺序：确保前置知识排在前面。
        面试常考：BFS版拓扑排序 vs DFS版，时间复杂度O(V+E)。
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for nid in self.nodes:
            for succ in self._adjacency.get(nid, []):
                if succ in in_degree:
                    in_degree[succ] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result: list[str] = []
        # 确定先后学习顺序，确保前置知识排在前面
        while queue:
            nid = queue.popleft()
            result.append(nid)
            for succ in self._adjacency.get(nid, []):
                if succ in in_degree:
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        queue.append(succ)
        # 检查是否有环
        if len(result) != len(self.nodes):
            logger.warning("Knowledge graph contains a cycle! Partial sort returned.")

        return result

    def get_ready_nodes(self, mastered_ids: set[str]) -> list[str]:
        """
        获取当前可以学习的知识点：前置知识全部掌握，但自己还未掌握。

        这是 Curriculum Agent 推荐下一个知识点的核心逻辑。
        """
        ready = []
        for nid, node in self.nodes.items():
            if nid in mastered_ids:
                continue
            prereqs = set(node.prerequisites)
            if prereqs.issubset(mastered_ids):
                ready.append(nid)
        return sorted(ready, key=lambda nid: self.nodes[nid].difficulty)

    def get_learning_path(self, target_id: str, mastered_ids: set[str]) -> list[str]:
        """
        生成到达目标知识点的最短学习路径。

        从target_id反向遍历，找出所有未掌握的前置知识，按拓扑序排列。
        """
        needed = self.get_all_prerequisites(target_id) - mastered_ids
        if target_id not in mastered_ids:
            needed.add(target_id)

        full_order = self.topological_sort()
        return [nid for nid in full_order if nid in needed]

    @classmethod
    def from_yaml(cls, file_path: str) -> "KnowledgeGraph":
        """从 YAML 文件加载知识图谱。"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        graph = cls()
        for node_data in data["nodes"]:
            graph.add_node(KnowledgeNode(**node_data))
        logger.info(f"Knowledge graph loaded from {file_path}, {len(graph.nodes)} nodes")
        return graph


if __name__ == "__main__":
    data_path = Path(__file__).parent.parent / "data" / "math_graph.yaml"
    graph = KnowledgeGraph.from_yaml(str(data_path))
    print(f"节点数: {len(graph.nodes)}")
    print(f"拓扑排序: {graph.topological_sort()}")
    print(f"可学习节点(无前置): {graph.get_ready_nodes(set())}")
