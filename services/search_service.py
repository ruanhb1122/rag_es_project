from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from core.database import db_manager
from core.elasticsearch_client import es_client
from models.chunk import Chunk
from utils.embedding_utils import embedding_utils

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """搜索类型"""
    TEXT = "text"  # 全文搜索
    VECTOR = "vector"  # 向量搜索
    HYBRID = "hybrid"  # 混合搜索


class SearchService:
    """搜索服务"""

    def search(self, kb_id: str, query: str, search_type: SearchType = SearchType.HYBRID,
               top_k: int = 10, min_score: float = 0.0, use_score_relevance: bool = False,
               text_weight: float = 0.5, vector_weight: float = 0.5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            index_name = f"kb_{kb_id}"

            # 检查索引是否存在
            if not es_client.index_exists(index_name):
                logger.warning(f"索引不存在: {index_name}")
                return []

            # 根据搜索类型执行搜索
            if search_type == SearchType.TEXT:
                response = self._text_search(index_name, query, top_k)
            elif search_type == SearchType.VECTOR:
                response = self._vector_search(index_name, query, top_k, min_score if use_score_relevance else 0.0)
            elif search_type == SearchType.HYBRID:
                response = self._hybrid_search(index_name, query, top_k, text_weight, vector_weight)
            else:
                raise ValueError(f"不支持的搜索类型: {search_type}")

            # 处理搜索结果
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'chunk_id': hit['_id'],
                    'score': hit['_score'],
                    'content': hit['_source'].get('chunk_content', ''),
                    'document_id': hit['_source'].get('document_id', ''),
                    'document_name': hit['_source'].get('document_name', ''),
                    'kb_id': hit['_source'].get('kb_id', ''),
                    'metadata': hit['_source'].get('metadata', {})
                }

                # 启用阈值 and 分数低于Score阈值
                if use_score_relevance and result['score'] < min_score:
                    pass
                else:
                    results.append(result)

            logger.info(f"搜索完成: {len(results)}个结果")
            return results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def _text_search(self, index_name: str, query: str, size: int) -> Dict[str, Any]:
        """全文搜索"""
        return es_client.text_search(
            index_name=index_name,
            query_text=query,
            fields=["chunk_content", "document_name", "kb_name"],
            size=size
        )

    def _vector_search(self, index_name: str, query: str, size: int, min_score: float) -> Dict[str, Any]:
        """向量搜索"""
        # 获取查询向量
        query_vector = embedding_utils.get_embedding(query)
        if not query_vector:
            logger.error("获取查询向量失败")
            return {'hits': {'hits': [], 'total': {'value': 0}}}

        return es_client.vector_search(
            index_name=index_name,
            vector=query_vector,
            size=size,
            min_score=min_score
        )

    def _hybrid_search(self, index_name: str, query: str, size: int,
                       text_weight: float, vector_weight: float) -> Dict[str, Any]:
        """混合搜索"""
        # 获取查询向量
        query_vector = embedding_utils.get_embedding(query)
        if not query_vector:
            logger.warning("获取查询向量失败，回退到纯文本搜索")
            return self._text_search(index_name, query, size)

        return es_client.hybrid_search(
            index_name=index_name,
            query_text=query,
            vector=query_vector,
            text_weight=text_weight,
            vector_weight=vector_weight,
            size=size
        )

    def get_similar_chunks(self, chunk_id: str, kb_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取相似分块"""
        try:
            # 获取分块内容
            with db_manager.get_session() as session:
                chunk = session.query(Chunk).filter_by(chunk_id=chunk_id, kb_id=kb_id).first()
                if not chunk:
                    logger.warning(f"分块不存在: {chunk_id}")
                    return []

                # 向量搜索相似内容
                return self._vector_search(f"kb_{kb_id}", chunk.chunk_content, top_k, 0.0)['hits']['hits']

        except Exception as e:
            logger.error(f"获取相似分块失败: {e}")
            return []