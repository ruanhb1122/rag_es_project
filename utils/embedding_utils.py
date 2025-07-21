from typing import List, Optional
import openai
import numpy as np
# 使用千问的Embedding模型
# from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
import logging
from utils.config import config
import os

logger = logging.getLogger(__name__)


class EmbeddingUtils:
    """向量化工具"""

    def __init__(self):
        self.api_key = config.get('embedding.api_key')
        self.model_name = config.get('embedding.model_name', 'text-embedding-v3')
        self.dimensions = config.get('embedding.dimensions', 1024)

        # 初始化OpenAI客户端
        openai.api_key = self.api_key

        # 初始化LangChain嵌入模型
        # self.embeddings = OpenAIEmbeddings(
        #     model=self.model_name,
        #     openai_api_key=self.api_key,
        #     dimensions=self.dimensions
        # )

        self.embeddings = DashScopeEmbeddings(
            # dashscope_api_key=self.api_key,
            dashscope_api_key = os.getenv('DASHSCOPE_API_KEY'),
            model=self.model_name
        )

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取单个文本的向量"""
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            return None

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取多个文本的向量"""
        try:
            ems = self.embeddings.embed_documents(texts)
            return ems
        except Exception as e:
            logger.error(f"批量获取向量失败: {e}")
            return []

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            return dot_product / (norm_a * norm_b)
        except Exception as e:
            logger.error(f"计算余弦相似度失败: {e}")
            return 0.0


# 全局向量化工具实例
embedding_utils = EmbeddingUtils()