import logging
from typing import List, Dict, Any, Tuple

from langchain_community.graphs.graph_document import GraphDocument

from core.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """知识图谱服务类，处理GraphDocument与Neo4j的同步"""

    def __init__(self):
        self.neo4j_client = neo4j_client

    def sync_graph_documents(self, graph_docs: List[GraphDocument], chunk_id: str) -> Tuple[int, int, int, int]:
        """
        同步GraphDocument到Neo4j，支持新增和更新

        Args:
            graph_docs: 图形文档列表
            chunk_id: 关联的分块ID

        Returns:
            元组(新增节点数, 更新节点数, 新增关系数, 更新关系数)
        """
        new_nodes = 0
        updated_nodes = 0
        new_rels = 0
        updated_rels = 0

        for graph_doc in graph_docs:
            # 处理节点
            node_stats = self._process_nodes(graph_doc.nodes, chunk_id)
            new_nodes += node_stats[0]
            updated_nodes += node_stats[1]

            # 处理关系
            rel_stats = self._process_relationships(graph_doc.relationships, chunk_id)
            new_rels += rel_stats[0]
            updated_rels += rel_stats[1]

        logger.info(
            f"同步完成 - 新增节点: {new_nodes}, 更新节点: {updated_nodes}, "
            f"新增关系: {new_rels}, 更新关系: {updated_rels}"
        )
        return new_nodes, updated_nodes, new_rels, updated_rels

    def _process_nodes(self, nodes: List[Any], chunk_id: str) -> Tuple[int, int]:
        """处理节点：新增或更新"""
        new = 0
        updated = 0

        for node in nodes:
            # 节点属性处理
            properties = {**node.properties, "chunk_id": chunk_id} if node.properties else {"chunk_id": chunk_id}

            # 检查节点是否已存在
            existing_nodes = self.neo4j_client.execute_query(
                f"MATCH (n:{node.type} {{id: $id}}) RETURN n",
                {"id": node.id}
            )

            if existing_nodes:
                # 更新现有节点
                self.neo4j_client.execute_query(
                    f"""
                    MATCH (n:{node.type} {{id: $id}})
                    SET n += $properties, n.updated_at = timestamp()
                    """,
                    {"id": node.id, "properties": properties}
                )
                updated += 1
            else:
                # 创建新节点
                self.neo4j_client.execute_query(
                    f"""
                    CREATE (n:{node.type} {{id: $id, name: $name, created_at: timestamp(), updated_at: timestamp()}})
                    SET n += $properties
                    """,
                    {
                        "id": node.id,
                        "name": node.id,  # 使用节点ID作为名称，可根据实际情况调整
                        "properties": properties
                    }
                )
                new += 1

        return new, updated

    def _process_relationships(self, relationships: List[Any], chunk_id: str) -> Tuple[int, int]:
        """处理关系：新增或更新"""
        new = 0
        updated = 0

        for rel in relationships:
            # 关系属性处理
            properties = {**rel.properties, "chunk_id": chunk_id} if rel.properties else {"chunk_id": chunk_id}

            # 检查关系是否已存在
            existing_rels = self.neo4j_client.execute_query(
                f"""
                MATCH (s:{rel.source.type} {{id: $source_id}})-[r:{rel.type}]->(t:{rel.target.type} {{id: $target_id}})
                RETURN r
                """,
                {
                    "source_id": rel.source.id,
                    "target_id": rel.target.id
                }
            )

            if existing_rels:
                # 更新现有关系
                self.neo4j_client.execute_query(
                    f"""
                    MATCH (s:{rel.source.type} {{id: $source_id}})-[r:{rel.type}]->(t:{rel.target.type} {{id: $target_id}})
                    SET r += $properties, r.updated_at = timestamp()
                    """,
                    {
                        "source_id": rel.source.id,
                        "target_id": rel.target.id,
                        "properties": properties
                    }
                )
                updated += 1
            else:
                # 创建新关系
                self.neo4j_client.execute_query(
                    f"""
                    MATCH (s:{rel.source.type} {{id: $source_id}})
                    MATCH (t:{rel.target.type} {{id: $target_id}})
                    CREATE (s)-[r:{rel.type} {{created_at: timestamp(), updated_at: timestamp()}}]->(t)
                    SET r += $properties
                    """,
                    {
                        "source_id": rel.source.id,
                        "target_id": rel.target.id,
                        "properties": properties
                    }
                )
                new += 1

        return new, updated

    def delete_by_chunk_id(self, chunk_id: str) -> Tuple[int, int]:
        """
        根据分块ID删除相关的节点和关系

        Args:
            chunk_id: 分块ID

        Returns:
            元组(删除节点数, 删除关系数)
        """
        # 删除关系
        rel_result = self.neo4j_client.execute_query(
            """
            MATCH ()-[r]->()
            WHERE r.chunk_id = $chunk_id
            DELETE r
            RETURN count(r) as deleted_rels
            """,
            {"chunk_id": chunk_id}
        )
        deleted_rels = rel_result[0]["deleted_rels"] if rel_result else 0

        # 删除仅与该分块相关的节点
        node_result = self.neo4j_client.execute_query(
            """
            MATCH (n)
            WHERE n.chunk_id = $chunk_id AND NOT (n)--()
            DELETE n
            RETURN count(n) as deleted_nodes
            """,
            {"chunk_id": chunk_id}
        )
        deleted_nodes = node_result[0]["deleted_nodes"] if node_result else 0

        logger.info(f"已删除分块 {chunk_id} 相关的节点: {deleted_nodes}, 关系: {deleted_rels}")
        return deleted_nodes, deleted_rels

    def query_related_knowledge(self, entity_id: str, entity_type: str, depth: int = 2) -> List[Dict[str, Any]]:
        """
        查询实体的相关知识

        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            depth: 查询深度

        Returns:
            相关知识列表
        """
        return self.neo4j_client.execute_query(
            f"""
            MATCH path = (n:{entity_type} {{id: $id}})-[*1..{depth}]-(m)
            RETURN 
                nodes(path) as nodes,
                relationships(path) as relationships,
                [node in nodes(path) | {{id: node.id, type: labels(node)[0], properties: properties(node)}}] as node_details,
                [rel in relationships(path) | {{type: type(rel), properties: properties(rel)}}] as rel_details
            """,
            {"id": entity_id}
        )
