from typing import List, Dict, Any
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
import uuid
from utils.config import config


class TextSplitter:
    """文本分割工具"""

    def __init__(self):
        self.chunk_size = config.get('text_splitter.chunk_size', 1000)
        self.chunk_overlap = config.get('text_splitter.chunk_overlap', 200)
        self.separator = config.get('text_splitter.separator', '\n\n')

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[self.separator, '\n', ' ', '']
        )

    def split_text(self, text: str, document_id: str, kb_id: str) -> List[Dict[str, Any]]:
        """分割文本"""
        chunks = self.splitter.split_text(text)

        chunk_list = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_content': chunk.strip(),
                'chunk_order': i + 1,
                'kb_id': kb_id,
                'chunk_status': 1,
                'index_status': '00'
            }
            chunk_list.append(chunk_data)

        return chunk_list

    def load_and_split_file(self, file_path: str, document_id: str, kb_id: str) -> List[Dict[str, Any]]:
        """加载并分割文件"""
        try:
            # 根据文件扩展名选择加载器
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith('.docx'):
                loader = Docx2txtLoader(file_path)
            elif file_path.endswith('.txt'):
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")

            # 加载文档
            documents = loader.load()

            # 提取文本内容
            text_content = '\n'.join([doc.page_content for doc in documents])

            # 分割文本
            return self.split_text(text_content, document_id, kb_id)

        except Exception as e:
            raise Exception(f"文件处理失败: {str(e)}")

    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()""''—]', '', text)
        return text.strip()