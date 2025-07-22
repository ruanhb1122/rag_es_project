import logging
import os

from langchain_openai import ChatOpenAI

from utils.config import config

logger = logging.getLogger(__name__)


class LlmClient:
    """大语言模型客户端封装"""

    def __init__(self):
        self.llm: ChatOpenAI  = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化llm客户端"""
        llm_config = config.get_section('llm')

        self.llm = ChatOpenAI(
            # api_key=llm_config.get('api_key'),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=llm_config.get('base_url'),
            model=llm_config.get('model_name'),
            temperature=llm_config.get('temperature', 0.7)
        )

        logger.info("llm客户端初始化完成")


# 全局llm客户端实例
llm_client = LlmClient()