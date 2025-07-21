import os
from typing import List, Dict, Any, Tuple
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from langchain_openai import OpenAI, ChatOpenAI
from langchain_community.chat_models import ChatTongyi
# 原向量存储库导入方式注释（版本升级前写法）
# from langchain_community.vectorstores import ElasticsearchStore
# 新版Elasticsearch向量存储
from langchain_elasticsearch import ElasticsearchStore

from dotenv import load_dotenv  

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSerializable

import pathlib
import json

current_dir = pathlib.Path(__file__).parent.absolute()  # 获取当前文件绝对路径

# 加载环境变量（如API_KEY等配置）
load_dotenv()

# 配置日志（调试级别）
import logging
logging.basicConfig(level=logging.DEBUG)
# 配置Elasticsearch客户端日志为调试级别
logging.getLogger("elasticsearch").setLevel(logging.DEBUG)

# 该文件仅做参考

class ESRAGDemo:
    def __init__(self, es_url: str = "http://localhost:9200", index_name: str = "rag_demo_index"):
        """初始化ES连接和相关配置
        Args:
            es_url: Elasticsearch服务地址
            index_name: 存储向量的索引名称
        """
        self.es = Elasticsearch(
            hosts=[es_url],
            headers={"Content-Type": "application/json"}
        )  # 初始化Elasticsearch客户端
        self.index_name = index_name  # 索引名称
        self.embeddings = DashScopeEmbeddings(model = "text-embedding-v3")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # 原不同LLM配置注释（保留测试记录）
        # self.llm = OpenAI(temperature=0)
        # self.llm = ChatTongyi(model = 'qwen-plus' , temperature = 0)

        # 使用深度求索模型（需环境变量DEEPSEEK_API_KEY）
        self.llm = ChatOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            model='deepseek-chat',
            temperature=0
        )
        
        # 创建索引（如果不存在）
        if not self.es.indices.exists(index=self.index_name):
            self._create_index()

    def _create_index(self) -> None:
        """创建支持混合检索的ES索引（包含文本、向量、元数据字段）"""
        mapping = {
            "mappings": {
                "properties": {
                    "text": {"type": "text"},  # 存储文本内容
                    "embedding": {"type": "dense_vector", "dims": 1024},  # 存储1024维向量
                    "metadata": {"type": "object", "enabled": True}  # 存储元数据（如文档来源）
                }
            }
        }
        self.es.indices.create(index=self.index_name, body=mapping)

    def load_documents(self, directory: str) -> List[Dict[str, Any]]:
        """从目录加载文档并处理为ES可索引的格式
        Args:
            directory: 文档所在目录
        Returns:
            ES批量索引操作列表
        """
        loader = DirectoryLoader(directory, glob="**/*.txt", loader_cls=TextLoader)  # 加载所有txt文档
        documents = loader.load()  # 加载文档内容
        texts = self.text_splitter.split_documents(documents)  # 分割文档为小块
        
        # 准备ES批量导入数据
        actions = []
        for i, text in enumerate(texts):
            embedding = self.embeddings.embed_query(text.page_content)  # 生成文本嵌入向量
            actions.append({
                "_index": self.index_name,
                "_id": i,
                "_source": {
                    "text": text.page_content,
                    "embedding": embedding,
                    "metadata": text.metadata  # 包含文档路径、行数等元信息
                }
            })
        return actions

    def index_documents(self, documents: List[Dict[str, Any]]) -> Tuple[int, List[Any]]:
        """将文档批量索引到ES
        Args:
            documents: ES批量操作列表
        Returns:
            (成功数, 失败列表)
        """
        success, failed = bulk(self.es, documents)  # 使用Elasticsearch批量插入工具
        return success, failed

    def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        执行混合检索（BM25文本检索 + k-NN向量检索）
        适用于 Elasticsearch 8.x 及以上版本
        """
        query_vector = self.embeddings.embed_query(query)

        # 现代Elasticsearch中混合检索的正确查询结构
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": 100
            },
            "query": {
                "match": {
                    "text": {
                        "query": query,
                        "boost": 0.5  # 为文本匹配设置权重
                    }
                }
            },
            "size": k
        }

        print(f"正在执行混合检索查询: {json.dumps(search_body, indent=2)}")

        results = self.es.search(
            index=self.index_name,
            body=search_body,
        )

        print(f"混合检索结果: {results}")
        # 从检索结果中提取并返回文档内容
        return [hit["_source"] for hit in results["hits"]["hits"]]

    # def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
    #     """执行混合检索（BM25文本检索 + 向量检索）
    #     Args:
    #         query: 检索查询
    #         k: 返回结果数
    #     Returns:
    #         检索结果列表
    #     """
    #     query_vector = self.embeddings.embed_query(query)  # 生成查询的嵌入向量
    #     # TODO 混合检索逻辑待修复（当前可能未正确融合两种检索方式）
    #     hybrid_query = {
    #         "bool": {
    #             "must": [  # 必须满足的条件（BM25文本匹配）
    #                 {
    #                     "match": {"text": query}
    #                 }
    #             ],
    #             "should": [  # 可选满足的条件（向量相似性）
    #                 {
    #                     "dense_vector": {
    #                         "field": "embedding",
    #                         "query_vector": query_vector,
    #                         "cosine": True  # 使用余弦相似度
    #                     }
    #                 }
    #             ]
    #         }
    #     }
    #
    #     print(f"hybrid_query: {hybrid_query}")
    #
    #     results = self.es.search(
    #         index=self.index_name,
    #         body={
    #             "query": hybrid_query,
    #             # "size": k,  # 原分页参数注释（可能影响结果数）
    #             # "_source": ["text", "metadata", "embedding"]  # 原返回字段注释
    #         }
    #     )
    #     print(f"hybrid_query_results: {results}")
    #     return [hit["_source"] for hit in results["hits"]["hits"]]

    def setup_qa_chain(self) -> RunnableSerializable[Any, str]:
        """设置基于ES检索的问答链（结合检索和大语言模型）"""
        def hybrid_retriever(query: str):
            return self.hybrid_search(query)  # 自定义混合检索函数
        
        # 1）原向量存储初始化方式注释（因版本升级报错） langchain_community.vectorstores.ElasticsearchStore
        # store = ElasticsearchStore(
        #     es_connection=self.es,
        #     index_name=self.index_name,
        #     embedding=self.embeddings,
        #     query_builder=hybrid_retriever
        # )

        # 2）新版Elasticsearch向量存储初始化（适配当前库版本） langchain_elasticsearch.ElasticsearchStore
        store = ElasticsearchStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            es_connection=self.es,
            vector_query_field="embedding",  # 向量字段名
            query_field="text",  # 文本字段名
        )

        # es_retriever = store.as_retriever(search_kwargs = {"k": 3})  # 原检索器初始化注释

        # 定义问答提示模板（系统提示+用户问题）
        prompt = ChatPromptTemplate.from_messages([("system", "根据上下文回答：\n{context}"), ("human", "{question}")])
        # 构建问答链：{context: 检索结果, question: 输入问题} -> 提示模板 -> LLM -> 输出解析
        chain = {"context": store.as_retriever(search_kwargs = {"k": 3}),
                 "question": RunnablePassthrough()} | prompt | self.llm | StrOutputParser()

        return chain


    def run_demo(self, data_directory: str, sample_query: str) -> None:
        """运行完整演示流程（加载文档->索引->测试问答）
        Args:
            data_directory: 文档数据目录
            sample_query: 测试问题
        """
        print("加载并处理文档...")
        documents = self.load_documents(data_directory)  # 加载并处理文档

        list1 = self.embeddings.embed_documents(['abc','efg'])  # 生成文档嵌入向量
        str1 = self.embeddings.embed_query('abc')  # 保存文档嵌入向量


        print(f"索引 {len(documents)} 个文档片段到ES...")
        success, failed = self.index_documents(documents)  # 索引到Elasticsearch
        print(f"成功索引 {success} 个文档，失败 {len(failed)} 个")

        # 原混合检索测试注释（因逻辑待修复暂不执行）
        print("\n执行混合检索示例:")
        search_results = self.hybrid_search(sample_query)
        for i, result in enumerate(search_results, 1):
            print(f"\n结果 {i}:\n内容: {result['text'][:200]}...\n元数据: {result['metadata']}...")
        #
        print("\n设置基于检索的问答链...")
        qa_chain = self.setup_qa_chain()  # 初始化问答链
        
        print("\n测试问答链:")
        answer = qa_chain.invoke(sample_query)  # 执行问答
        print(f"问题: {sample_query}")
        print(f"回答: {answer}")


if __name__ == "__main__":
    print(f"当前目录: {current_dir}")
    demo = ESRAGDemo(index_name="es_rag_demo0703")
    demo.run_demo(
        data_directory= os.path.join(current_dir, "documents"),
        sample_query="deepseek发展历程"
    )