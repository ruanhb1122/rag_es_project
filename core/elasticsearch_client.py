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
        self.text_max_value = 1.0
        self._initialize_client()
        self._initialize_other_param()

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

    def _initialize_other_param(self):
        es_other_config = config.get_section('retrieval')
        self.text_max_value = es_other_config.get('text_max_value')

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

    # -------------------------- 公共方法封装 --------------------------
    def _execute_search(self, index_name: str, search_body: Dict[str, Any],
                        min_relevance_score: float) -> Dict[str, Any]:
        """
        执行搜索的通用方法，封装了搜索执行、结果过滤和异常处理
        """
        try:
            # 执行搜索
            response = self.client.search(
                index=index_name,
                body=search_body
            )

            # 过滤低相关结果
            return self._filter_results(response, min_relevance_score)

        except Exception as e:
            # 统一异常处理
            return self._handle_exception(e, index_name)

    def _filter_results(self, response: Dict[str, Any], min_score: float) -> Dict[str, Any]:
        """过滤低于最小相关度分数的结果"""
        filtered_hits = [hit for hit in response["hits"]["hits"]
                         if hit["_score"] >= min_score]

        response["hits"]["hits"] = filtered_hits
        response["hits"]["total"]["value"] = len(filtered_hits)
        return response

    def _handle_exception(self, e: Exception, index_name: str) -> Dict[str, Any]:
        """统一异常处理逻辑"""
        error_msg = str(e).lower()
        if "index_not_found_exception" in error_msg:
            logger.error(f"索引不存在: {index_name}")
            return {"error": "索引不存在", "hits": {"hits": [], "total": {"value": 0}}}
        elif "vector_length_mismatch" in error_msg:
            logger.error("向量长度不匹配")
            return {"error": "向量长度不匹配", "hits": {"hits": [], "total": {"value": 0}}}
        elif "field_not_found" in error_msg or "unknown field" in error_msg:
            logger.error("字段不存在")
            return {"error": "字段不存在", "hits": {"hits": [], "total": {"value": 0}}}
        else:
            logger.error(f"搜索失败: {e}")
            return {"error": "搜索失败", "hits": {"hits": [], "total": {"value": 0}}}

    def _normalize_weights(self, text_weight: float, vector_weight: float) -> tuple[float, float]:
        """确保权重和为1.0，自动归一化处理"""
        if not abs(text_weight + vector_weight - 1.0) < 1e-6:
            logger.warning(f"权重之和不为1.0，自动归一化处理")
            total = text_weight + vector_weight
            text_weight /= total
            vector_weight /= total
        return text_weight, vector_weight

    def vector_search(self, index_name: str, vector: List[float],
                      size: int = 10, min_score: float = 0.1, fields: List[str] = None) -> Dict[str, Any]:
        """优化的纯向量检索方法"""
        search_body = {
            "query": {
                "function_score": {
                    "query": {"match_all": {}},
                    "functions": [
                        {
                            "script_score": {
                                "script": {
                                    "source": """
                                        double vectorScore = (cosineSimilarity(params.query_vector, 'chunk_embedding') + 1.0) / 2.0;
                                        return vectorScore;
                                    """,
                                    "params": {"query_vector": vector}
                                }
                            }
                        }
                    ],
                    "min_score": min_score,
                    "boost_mode": "replace"
                }
            },
            "size": size,
            "_source": fields if fields is not None else ["*"]
        }
        return self._execute_search(index_name, search_body, min_score)


    def text_search(self, index_name: str, query_text: str,
                    size: int = 10, min_score: float = 0.1, fields: List[str] = None) -> Dict[str, Any]:
        """优化的纯文本检索方法"""
        search_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"chunk_content": {"query": query_text}}},
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "functions": [
                        {
                            "script_score": {
                                "script": {
                                    "source": """
                                        double textScore = _score;
                                        textScore = Math.min(textScore, params.text_max_value);
                                        textScore = textScore / params.text_max_value;
                                        return textScore;
                                    """,
                                    "params": {"text_max_value": self.text_max_value}
                                }
                            }
                        }
                    ],
                    "min_score": min_score,
                    "boost_mode": "replace"
                }
            },
            "size": size,
            "_source": fields if fields is not None else ["*"]
        }

        return self._execute_search(index_name, search_body, min_score)

    def hybrid_search(self, index_name: str, query_text: str, vector: List[float],
                      text_weight: float = 0.5, vector_weight: float = 0.5,
                      size: int = 10, min_score: float = 0.1 ) -> Dict[str, Any]:

        """优化的混合检索方法"""
        # 归一化权重
        text_weight, vector_weight = self._normalize_weights(text_weight, vector_weight)

        search_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"chunk_content": {"query": query_text}}},
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "functions": [
                        {
                            "script_score": {
                                "script": {
                                    "source": """
                                                // 文本分数归一化
                                                double textScore = _score;
                                                textScore = Math.min(textScore, params.text_max_value);
                                                textScore = textScore / params.text_max_value;

                                                // 向量分数计算
                                                double vectorScore = (cosineSimilarity(params.query_vector, 'chunk_embedding') + 1.0) / 2.0;
                                                vectorScore = Math.max(vectorScore, 0.0);

                                                // 应用权重计算最终得分
                                                return (textScore * params.text_weight) + (vectorScore * params.vector_weight);
                                            """,
                                    "params": {
                                        "query_vector": vector,
                                        "text_weight": text_weight,
                                        "vector_weight": vector_weight,
                                        "text_max_value": self.text_max_value
                                    }
                                }
                            }
                        }
                    ],
                    "min_score": min_score,
                    "boost_mode": "replace"
                }
            },
            "size": size
        }

        return self._execute_search(index_name, search_body, min_score)

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