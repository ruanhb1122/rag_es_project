import logging
from enum import Enum
from typing import List, Dict, Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable, RunnablePassthrough

from core.database import db_manager
from core.elasticsearch_client import es_client
from core.llm_client import llm_client
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

            min_relevance_score = min_score if use_score_relevance else 0.1

            # 根据搜索类型执行搜索
            if search_type == SearchType.TEXT:
                response = self._text_search(index_name, query, top_k, min_score=min_relevance_score)
            elif search_type == SearchType.VECTOR:
                response = self._vector_search(index_name, query, top_k, min_score=min_relevance_score)
            elif search_type == SearchType.HYBRID:
                response = self._hybrid_search(index_name, query, top_k, text_weight, vector_weight, min_score=min_relevance_score)
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

                results.append(result)
                # 启用阈值 and 分数低于Score阈值  其实在es查询时已经过滤了，这里不再重复过滤
                # if use_score_relevance and result['score'] < min_score:
                #     pass
                # else:
                #     results.append(result)

            logger.info(f"搜索完成: {len(results)}个结果")
            return results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def _text_search(self, index_name: str, query: str, size: int, min_score: float) -> Dict[str, Any]:
        """全文搜索"""
        return es_client.text_search(
            index_name=index_name,
            query_text=query,
            fields=["id", "document_id", "chunk_content", "document_name", "kb_id", "metadata"],
            size=size,
            min_score=min_score
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
            fields=["id", "document_id", "chunk_content", "document_name", "kb_id", "metadata"],
            size=size,
            min_score=min_score
        )

    def _hybrid_search(self, index_name: str, query: str, size: int,
                       text_weight: float, vector_weight: float, min_score: float) -> Dict[str, Any]:
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
            size=size,
            min_score=min_score
        )

    def _search_for_chat(self, kb_id: str, query: str) -> List[Dict[str, Any]]:
        size = 3
        min_score = 0.5
        text_weight = 0.3
        vector_weight = 0.7
        """混合搜索"""
        # 获取查询向量
        results = self.search(
            kb_id=kb_id,
            query=query,
            search_type=SearchType.HYBRID,
            top_k=size,
            min_score=min_score,
            use_score_relevance=True,
            text_weight=text_weight,
            vector_weight=vector_weight
        )
        return results

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

    def chat(self, kb_id: str, query: str) -> Optional[str]:
        qa_chain =  self.setup_qa_chain()
        answer = qa_chain.invoke({"kb_id": kb_id, "query_text": query})
        return answer

    def setup_qa_chain(self) -> RunnableSerializable[Any, str]:
        """设置基于ES检索的问答链"""

        # 定义问答提示模板
        prompt_template = """
                你是一个问答机器人。
                你的任务是根据下述已知信息回答用户问题。
                确保你的回复完全依据下述已知信息。不要编造答案。
                如果下述已知信息不足以回答用户的问题，请直接回复"我无法回答您的问题"。

                已知信息:
                {context}

                用户问：
                {question}

                请用中文回答用户问题。
                """

        # 定义问答提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("human", prompt_template),  # 更规范的写法，直接使用角色+内容的元组
        ])

        # 自定义一个函数，将检索到的文档字典列表格式化为字符串
        def format_context(docs: List[Dict[str, Any]]) -> str:
            return "\n\n".join(doc["content"] for doc in docs)

        # 构建问答链：通过RunnablePassthrough获取输入参数，动态传递给搜索方法
        chain = (
                {
                    # 从输入中获取kb_id和query_text，传递给_search_for_chat方法
                    "context": RunnablePassthrough.assign(
                        docs=lambda x: self._search_for_chat(x["kb_id"], x["query_text"])
                    ) | (lambda x: format_context(x["docs"])),  # 格式化搜索结果
                    "question": lambda x: x["query_text"]  # 从输入中获取问题
                }
                | prompt
                | llm_client.llm
                | StrOutputParser()
        )

        return chain

