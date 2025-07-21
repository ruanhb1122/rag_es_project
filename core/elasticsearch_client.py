from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError
from typing import Dict, List, Any, Optional
import logging
from utils.config import config
import json

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Elasticsearch客户端封装"""

    def __init__(self):
        self.client: Elasticsearch  = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化ES客户端"""
        es_config = config.get_section('elasticsearch')

        self.client = Elasticsearch(
            hosts=es_config.get('hosts', ['http://localhost:9200']),
            # basic_auth=(es_config.get('username'), es_config.get('password')),
            # timeout=es_config.get('timeout', 30),
            # max_retries=es_config.get('max_retries', 3),
            # retry_on_timeout=es_config.get('retry_on_timeout', True),
            # verify_certs=False,
            # ssl_show_warn=False
        )

        logger.info("Elasticsearch客户端初始化完成")

    def create_index(self, index_name: str, mapping: Dict[str, Any] = None,
                     settings: Dict[str, Any] = None) -> bool:
        """创建索引"""
        try:
            body = {}
            if mapping:
                body['mappings'] = mapping
            if settings:
                body['settings'] = settings

            # 默认mapping
            if not mapping:
                body['mappings'] = {
                    "properties": {
                        "kb_name": {"type": "text", "analyzer": "ik_max_word"},
                        "kb_id": {"type": "keyword"},
                        "id": {"type": "keyword"},
                        "chunk_content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_max_word"
                        },
                        "chunk_embedding": {
                            "type": "dense_vector",
                            "dims": 1024,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "document_id": {"type": "keyword"},
                        "document_name": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 512}
                            }
                        },
                        "metadata": {
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "chunk_status": {"type": "keyword"},
                                "document_id": {"type": "keyword"}
                            }
                        }
                    }
                }

            self.client.indices.create(index=index_name, body=body)
            logger.info(f"索引创建成功: {index_name}")
            return True

        except RequestError as e:
            if 'resource_already_exists_exception' in str(e):
                logger.warning(f"索引已存在: {index_name}")
                return True
            logger.error(f"索引创建失败: {e}")
            return False
        except Exception as e:
            logger.error(f"索引创建异常: {e}")
            return False

    def delete_index(self, index_name: str) -> bool:
        """删除索引"""
        try:
            self.client.indices.delete(index=index_name)
            logger.info(f"索引删除成功: {index_name}")
            return True
        except NotFoundError:
            logger.warning(f"索引不存在: {index_name}")
            return True
        except Exception as e:
            logger.error(f"索引删除失败: {e}")
            return False

    def index_exists(self, index_name: str) -> bool:
        """检查索引是否存在"""
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"检查索引存在性失败: {e}")
            return False

    def add_document(self, index_name: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """添加文档"""
        try:
            response = self.client.index(index=index_name, id=doc_id, document=document)
            logger.debug(f"文档添加成功: {doc_id}")
            return response['result'] in ['created', 'updated']
        except Exception as e:
            logger.error(f"文档添加失败: {e}")
            return False

    def get_document(self, index_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        try:
            response = self.client.get(index=index_name, id=doc_id)
            return response['_source']
        except NotFoundError:
            logger.warning(f"文档不存在: {doc_id}")
            return None
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    def update_document(self, index_name: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """更新文档"""
        try:
            response = self.client.update(
                index=index_name,
                id=doc_id,
                doc=document
            )
            logger.debug(f"文档更新成功: {doc_id}")
            return response['result'] == 'updated'
        except Exception as e:
            logger.error(f"文档更新失败: {e}")
            return False

    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """删除文档"""
        try:
            response = self.client.delete(index=index_name, id=doc_id)
            logger.debug(f"文档删除成功: {doc_id}")
            return response['result'] == 'deleted'
        except NotFoundError:
            logger.warning(f"文档不存在: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"文档删除失败: {e}")
            return False

    # def _search(self, index_name: str, query: Dict[str, Any] = None, body: Dict[str, Any] = None,
    #             from_: int = 0, size: int = 10) -> Dict[str, Any]:
    #     """搜索文档"""
    #     try:
    #         response = self.client.search(
    #             index=index_name,
    #             query=query,
    #             body=body,
    #             from_=from_,
    #             size=size
    #         )
    #         return response
    #     except Exception as e:
    #         logger.error(f"搜索失败: {e}")
    #         return {'hits': {'hits': [], 'total': {'value': 0}}}

    def vector_search(self, index_name: str, vector: List[float],
                      size: int = 10, min_score: float = 0.0) -> Dict[str, Any]:
        """向量搜索"""
        query = {
            "knn": {
                "field": "chunk_embedding",
                "query_vector": vector,
                "k": size,
                "num_candidates": size * 2
            }
        }

        if min_score > 0:
            query["min_score"] = min_score

        try:
            response = self.client.search(
                index=index_name,
                body=query,
                from_=0,
                size=size
            )
            return response
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return {'hits': {'hits': [], 'total': {'value': 0}}}


    def text_search(self, index_name: str, query_text: str,
                    fields: List[str] = None, size: int = 10) -> Dict[str, Any]:
        """全文搜索"""
        if not fields:
            fields = ["chunk_content", "document_name", "kb_name"]

        query = {
            "multi_match": {
                "query": query_text,
                "fields": fields,
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }

        try:
            response = self.client.search(
                index=index_name,
                query=query,
                from_=0,
                size=size
            )
            return response
        except Exception as e:
            logger.error(f"全文搜索失败: {e}")
            return {'hits': {'hits': [], 'total': {'value': 0}}}

    def hybrid_search(self, index_name: str, query_text: str, vector: List[float],
                      text_weight: float = 0.5, vector_weight: float = 0.5,
                      size: int = 10) -> Dict[str, Any]:

        # knn搜索模型
        search_body = {
            "knn": {
                "field": "chunk_embedding",
                "query_vector": vector,
                "k": 3,
                "num_candidates": 100
            },
            "query": {
                "match": {
                    "text": {
                        "query": query_text,
                        "boost": 0.5
                    }
                }
            },
            "size": 3
        }

        # logger.info(f"hybrid_search正在执行混合检索查询knn: {json.dumps(search_body, indent=2)}")
        # results = self.client.search(
        #     index=index_name,
        #     body=search_body,
        # )
        # logger.info(f"hybrid_search查询knn结果: {results}")


        # script_score模式搜索
        script_query = {
            "script_score": {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"text": query_text}},
                            {"match_all": {}}  # 确保所有文档都能被考虑
                        ]
                    }
                },
                "script": {
                    "source": """
                           double textScore = _score;
                           double vectorScore = cosineSimilarity(params.query_vector, 'chunk_embedding') + 1.0;
                           return textScore * params.text_weight + vectorScore * params.vector_weight;
                       """,
                    "params": {"query_vector": vector , "text_weight": text_weight , "vector_weight": vector_weight}
                }
            }
        }

        # logger.info(f"hybrid_search正在执行混合检索查询script: {json.dumps(hybrid_query, indent=2)}")


        try:
            response = self.client.search(
                index=index_name,
                # body=search_body,
                query = script_query,
                from_=0,
                size=size
            )
            return response
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return {'hits': {'hits': [], 'total': {'value': 0}}}

    def bulk_index(self, index_name: str, documents: List[Dict[str, Any]]) -> bool:
        """批量索引文档"""
        try:
            actions = []
            for doc in documents:
                action = {
                    "_index": index_name,
                    "_id": doc.get('id'),
                    "_source": doc
                }
                actions.append(action)

            response = self.client.bulk(operations=actions)

            # 检查是否有错误
            if response.get('errors'):
                logger.error(f"批量索引部分失败: {response}")
                return False

            logger.info(f"批量索引成功: {len(documents)}个文档")
            return True

        except Exception as e:
            logger.error(f"批量索引失败: {e}")
            return False

    def health_check(self) -> bool:
        """健康检查"""
        try:
            health = self.client.cluster.health()
            return health['status'] in ['green', 'yellow']
        except Exception as e:
            logger.error(f"ES健康检查失败: {e}")
            return False


# 全局ES客户端实例
es_client = ElasticsearchClient()