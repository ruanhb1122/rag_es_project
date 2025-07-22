# RAG 知识库系统

基于检索增强生成（RAG）技术的知识库系统，支持文档上传、智能分块、向量检索等功能。


## 项目结构

```
rag_es_project/
├── app.py                 # Flask应用入口
├── config/
│   └── backend.yaml       # 配置文件
├── core/
│   ├── __init__.py
│   ├── database.py        # 数据库连接和ORM
│   ├── elasticsearch_client.py  # ES客户端封装
│   └── minio_client.py    # MinIO客户端封装
├── models/
│   ├── __init__.py
│   ├── chunk.py            # 分块模型
│   ├── document.py         # 文档模型
│   └── dto.py
├── services/
│   ├── __init__.py
│   ├── chunk_service.py        # 分块服务
│   ├── document_service.py     # 文档服务
│   └── search_service.py       # 搜索服务
├── controllers/
│   ├── __init__.py
│   ├── document_controller.py  # 分块控制器
│   ├── document_controller.py  # 文档控制器
│   └── search_controller.py    # 搜索控制器
├── utils/
│   ├── __init__.py
│   ├── config.py               # 配置文件读取工具
│   ├── text_splitter.py        # 文本分割工具
│   └── embedding_utils.py      # 向量化工具
├── static/                     #前端静态资源
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
├── templates/                  #前端页面
│   ├── index.html
│   ├── upload.html
│   ├── chunk_list.html
│   ├── document_list.html
│   └── search.html
├── requirements.txt            #项目包依赖管理
└── README.md
```



## 功能特点

1. **文档管理**：支持TXT、PDF、DOCX等格式文档上传、存储、删除
2. **智能分块**：自动将文档分割为语义连贯的文本块
3. **向量嵌入**：使用OpenAI embedding模型将文本转换为向量
4. **多模式检索**：支持全文检索、向量检索、混合检索
5. **知识库隔离**：不同知识库数据独立存储和检索


## 环境要求

- Python 3.8+
- MySQL 5.7+
- Elasticsearch 8.x
- MinIO (或兼容S3的对象存储)
- Node.js (可选，用于前端开发)


## 快速开始

### 后端部署

#### 1. 进入后端目录
```bash
cd backend
```

#### 2. 安装依赖
```bash
pip install -r requirements.txt
```

#### 3.配置修改
编辑 *backend/config/backend.yaml*，修改数据库、ES、MinIO 等配置

#### 4.启动服务
```bash
python app.py
```

### 前端部署

直接通过浏览器访问后端服务的静态文件（Flask 默认托管 frontend 目录），或使用 Nginx 部署 frontend 目录。

### 接口说明
#### 文档管理
- POST /api/documents/upload：上传文档
- GET /api/documents：获取文档列表
- GET /api/documents/<document_id>：获取文档详情
- DELETE /api/documents/<document_id>：删除文档
- GET /api/documents/<document_id>/chunks：获取文档分块
#### 搜索服务
- GET /api/search：搜索知识库
- GET /api/search/similar：获取相似分块
- GET /api/search/suggestions：获取搜索建议

#### 技术栈
- **后端**：Flask、SQLAlchemy、Elasticsearch、MinIO SDK
- **前端**：HTML、CSS、JavaScript（可扩展为 Vue/React）
- **AI 相关**：LangChain、OpenAI Embedding
- **数据库**：MySQL（元数据）、Elasticsearch（检索）、MinIO（文档存储）




文档上传
/api/documents/upload: 上传文档
    1、上传文档至MinIO
    2、解析文档，生成分块
    3、将文档、分块保存至数据库
    4、生成向量并保存至Elasticsearch
    5、返回接口响应

文档管理
/api/documents/page: 获取文档列表
/api/documents/<document_id>：删除文档   DB、es同步删除
/api/documents/modify_status：修改文档状态 DB、es同步修改
    文档块：
    /api/chunks/page: 获取文档块列表（文档id必传）
    /api/chunks/modify_data：修改文档块数据
    /api/chunks/modify_status：修改文档块状态

搜索服务
    /api/search: 搜索知识库(召回测试)
    /api/search_answer: 搜索知识库并llm回复
    




