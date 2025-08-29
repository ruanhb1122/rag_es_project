from string import Template
from typing import List

import spacy
from langchain_community.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_experimental.graph_transformers import LLMGraphTransformer

# 加载模型（相当于实例化一个实体提取器）
nlp = spacy.load("zh_core_web_sm")  # 类似 KeywordExtractor()
text = "Apple is looking to buy U.K. startup for $1 billion"
doc = nlp(text)  # 处理文本
entities = [(ent.text, ent.label_) for ent in doc.ents]  # 提取实体
# 输出：[("Apple", "ORG"), ("U.K.", "GPE"), ("$1 billion", "MONEY")]

print(entities)


print('\n----------\n')

from core.keyword_extractor import KeywordExtractor


keyword_extractor = KeywordExtractor(model_name='zh_core_web_sm')
text = """
DeepSeek有哪些模型？模型的特点是什么
"""
keywords = keyword_extractor.input_text_entities_extractor(text, filter_types=['公司', '人物', '产品'])
print(keywords)  # 输出：['Apple', 'U.K.', '$1 billion']


print('\n============================\n')


from utils.config import config
from core.llm_client import llm_client
import logging

logger = logging.getLogger(__name__)


doc = Document(page_content=text, metadata={"source": "test.txt"})

nodes = ['公司', '产品', '人']
system_template = config.get("graph_query_prompt")
template = Template(system_template)
humn_str = f"你是一个知识图谱工程专家，请帮我提取出上下文中的文本中的 {','.join(nodes)} 等实体"
humn = HumanMessagePromptTemplate.from_template(humn_str)
sysprompt = template.safe_substitute(entity_types=','.join(nodes),
                                     input_text=doc.page_content)
system_message_prompt = SystemMessagePromptTemplate.from_template(sysprompt)
prompt = ChatPromptTemplate.from_messages([system_message_prompt, humn])
graph = LLMGraphTransformer(llm=llm_client.llm, prompt=prompt, allowed_nodes=nodes, node_properties=True)

res_data: List[GraphDocument] = graph.convert_to_graph_documents([doc])

logger.info(res_data)

for data in res_data:
    print(data.nodes)
    print(data.relationships)

print('\n----------\n')
print('res_data:' , res_data)