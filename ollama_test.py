import requests
import json


def call_ollama(model, prompt):
    url = "http://localhost:11434/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False  # 非流式
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()["message"]["content"]


# 使用示例  非流式
# result = call_ollama("deepseek-r1:7b", "帮忙计算一下3*（1+2）/4-100等于多少？")
# print(result)


def stream_ollama(model, prompt):
    url = "http://localhost:11434/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True  # 启用流式
    }

    with requests.post(url, headers=headers, data=json.dumps(data), stream=True) as r:
        for line in r.iter_lines():
            if line:
                # 解析每一行JSON
                chunk = json.loads(line.decode("utf-8"))
                print(chunk["message"]["content"], end="", flush=True)


# 使用示例 流式输出
# stream_ollama("deepseek-r1:7b", "用3个步骤解释光合作用的过程")


#
# from langchain_community.llms import Ollama
#
# # 加载本地 Ollama 模型（需先通过 ollama pull 下载）
# llm = Ollama(
#     model="deepseek-r1:7b",  # 模型名称
#     temperature=0.7,    # 随机性（0-1）
#     num_ctx=4096        # 上下文窗口大小
# )


from langchain_ollama import OllamaLLM
llm = OllamaLLM(
    model="deepseek-r1:7b",  # 模型名称
    temperature=0.7,    # 随机性（0-1）
    num_ctx=4096        # 上下文窗口大小
)


# 生成文本
response = llm.invoke("请简要介绍 LangChain 的核心功能")
print(response)