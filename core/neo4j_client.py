from neo4j import GraphDatabase, exceptions
from typing import List, Dict, Any, Optional, Tuple
import logging
from utils.config import config

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 客户端封装，用于知识图谱操作"""

    def __init__(self):
        self.driver = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化 Neo4j 连接驱动"""
        neo4j_config = config.get_section('neo4j')

        try:
            self.driver = GraphDatabase.driver(
                neo4j_config.get('uri', 'bolt://localhost:7687'),
                auth=(
                    neo4j_config.get('username', 'neo4j'),
                    neo4j_config.get('password', 'password')
                ),
                # database=neo4j_config.get('database', 'rag_demo'),
                max_connection_lifetime=neo4j_config.get('max_connection_lifetime', 3600)
            )
            # 测试连接
            self.test_connection()
            logger.info("Neo4j 客户端初始化完成")
        except Exception as e:
            logger.error(f"Neo4j 客户端初始化失败: {e}")
            raise

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.driver.session() as session:
                res = session.run("MATCH (n) RETURN count(n) AS count LIMIT 1")
                print(res)
            return True
        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j 连接测试失败: {e}")
            return False

    def close(self) -> None:
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 连接已关闭")

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询
        :param query: Cypher 语句
        :param parameters: 查询参数
        :return: 结果列表
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result.data()]
        except exceptions.Neo4jError as e:
            logger.error(f"Cypher 查询执行失败: {query}, 错误: {e}")
            return []

    def create_triple(self, subject: str, predicate: str, object_: str,
                      properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        创建三元组（实体-关系-实体）
        :param subject: 主体实体
        :param predicate: 关系
        :param object_: 客体实体
        :param properties: 关系属性
        :return: 是否成功
        """
        cypher = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        MERGE (s)-[r:RELATIONSHIP {type: $predicate, 
                                 createdAt: timestamp(),
                                 updatedAt: timestamp(),
                                 properties: $properties}]->(o)
        RETURN id(s) AS subject_id, id(o) AS object_id, id(r) AS relation_id
        """
        try:
            with self.driver.session() as session:
                session.run(cypher, {
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_,
                    "properties": properties or {}
                })
            logger.debug(f"创建三元组成功: ({subject})- [{predicate}] -> ({object_})")
            return True
        except exceptions.Neo4jError as e:
            logger.error(f"创建三元组失败: {e}")
            return False

    def batch_create_triples(self, triples: List[Tuple[str, str, str, Optional[Dict]]]) -> Tuple[int, int]:
        """
        批量创建三元组
        :param triples: 三元组列表，格式: [(主体, 关系, 客体, 属性), ...]
        :return: (成功数, 失败数)
        """
        success = 0
        failed = 0

        for triple in triples:
            subject, predicate, object_, props = triple
            if self.create_triple(subject, predicate, object_, props):
                success += 1
            else:
                failed += 1

        return success, failed

    def delete_relationship(self, subject: str, predicate: str, object_: str) -> bool:
        """
        删除实体间的关系
        :param subject: 主体实体
        :param predicate: 关系类型
        :param object_: 客体实体
        :return: 是否成功
        """
        cypher = """
        MATCH (s:Entity {name: $subject})-[r:RELATIONSHIP {type: $predicate}]->(o:Entity {name: $object})
        DELETE r
        """
        try:
            with self.driver.session() as session:
                result = session.run(cypher, {
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_
                })
                return result.consume().counters.relationships_deleted > 0
        except exceptions.Neo4jError as e:
            logger.error(f"删除关系失败: {e}")
            return False

    def delete_entity(self, entity_name: str) -> bool:
        """
        删除实体及相关关系
        :param entity_name: 实体名称
        :return: 是否成功
        """
        cypher = """
        MATCH (n:Entity {name: $name})
        DETACH DELETE n
        """
        try:
            with self.driver.session() as session:
                result = session.run(cypher, {"name": entity_name})
                return result.consume().counters.nodes_deleted > 0
        except exceptions.Neo4jError as e:
            logger.error(f"删除实体失败: {e}")
            return False

    def search_entities(self, entity_name: str, fuzzy: bool = False) -> List[Dict[str, Any]]:
        """
        搜索实体
        :param entity_name: 实体名称
        :param fuzzy: 是否模糊搜索
        :return: 实体列表
        """
        if fuzzy:
            cypher = """
            MATCH (n:Entity)
            WHERE n.name CONTAINS $name
            RETURN n.name AS name, id(n) AS id
            """
        else:
            cypher = """
            MATCH (n:Entity {name: $name})
            RETURN n.name AS name, id(n) AS id
            """

        return self.execute_query(cypher, {"name": entity_name})

    def get_related_entities(self, entity_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        获取实体的关联实体（知识图谱检索）
        :param entity_name: 实体名称
        :param depth: 检索深度
        :return: 关联实体及关系列表
        """
        cypher = f"""
        MATCH (s:Entity {{name: $name}})-[r*1..{depth}]-(o:Entity)
        RETURN 
            s.name AS source,
            [rel in r | rel.type] AS relationships,
            o.name AS target,
            [rel in r | rel.properties] AS properties
        """
        return self.execute_query(cypher, {"name": entity_name})

    def extract_and_save_triples(self, text: str, chunk_id: str, llm) -> Tuple[int, int]:
        """
        从文本中提取三元组并保存（结合LLM）
        :param text: 待提取的文本
        :param chunk_id: 关联的分块ID
        :param llm: LLM客户端实例
        :return: (成功数, 失败数)
        """
        # 构建提示词让LLM提取三元组
        prompt = f"""
        请从以下文本中提取实体关系三元组，格式为：(主体, 关系, 客体, 属性)
        其中属性为可选字段，包含来源分块ID等信息。
        文本内容：{text}
        分块ID：{chunk_id}
        请严格按照JSON格式返回列表，例如：
        [
            ["实体1", "关系", "实体2", {{"chunk_id": "xxx", "confidence": 0.9}}],
            ["实体3", "关系", "实体4", {{"chunk_id": "xxx", "confidence": 0.8}}]
        ]
        """

        try:
            # 调用LLM提取三元组
            response = llm.llm.predict(prompt)
            triples = eval(response)  # 注意：生产环境需使用更安全的JSON解析

            # 添加分块ID属性
            formatted_triples = []
            for triple in triples:
                if len(triple) == 3:
                    subj, pred, obj = triple
                    props = {"chunk_id": chunk_id}
                    formatted_triples.append((subj, pred, obj, props))
                elif len(triple) == 4:
                    subj, pred, obj, props = triple
                    props["chunk_id"] = chunk_id
                    formatted_triples.append((subj, pred, obj, props))

            # 批量保存
            return self.batch_create_triples(formatted_triples)

        except Exception as e:
            logger.error(f"三元组提取失败: {e}")
            return 0, 1


# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()