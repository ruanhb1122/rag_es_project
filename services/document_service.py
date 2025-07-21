from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import uuid
import os
import tempfile
import logging
from werkzeug.datastructures import FileStorage
from core.database import db_manager, PaginationQuery
from core.minio_client import minio_client
from core.elasticsearch_client import es_client
from models.document import Document
from models.chunk import Chunk
from utils.text_splitter import TextSplitter
from services.chunk_service import ChunkService
from utils.embedding_utils import embedding_utils

logger = logging.getLogger(__name__)


class DocumentService:
    """文档服务"""

    def __init__(self):
        self.text_splitter = TextSplitter()
        self.chunk_service = ChunkService()

    def create_document(self, document_name: str, kb_id: str,
                        file: FileStorage, created_by: str = None) -> Optional[str]:
        """创建文档"""
        document_id = str(uuid.uuid4())

        try:
            with db_manager.get_session() as session:
                # 创建文档记录
                document = Document(
                    document_id=document_id,
                    document_name=document_name,
                    kb_id=kb_id,
                    document_status=1,
                    created_by=created_by
                )
                session.add(document)
                session.flush()

                # 上传文件到MinIO
                object_name = f"{kb_id}/{document_id}/{document_name}"
                file.stream.seek(0)  # 重置文件指针
                success = minio_client.upload_file(
                    object_name=object_name,
                    file_data=file.stream,
                    file_size=file.content_length
                )

                if not success:
                    raise Exception("文件上传失败")

                # 处理文档内容
                file.stream.seek(0)  # 重置文件指针
                self._process_document_content(document_id, document_name, kb_id, file.stream.read())

                logger.info(f"文档创建成功: {document_id}")
                return document_id

        except Exception as e:
            logger.error(f"文档创建失败: {e}")
            # 回滚：删除已上传的文件
            try:
                object_name = f"{kb_id}/{document_id}/{document_name}"
                minio_client.delete_file(object_name)
            except:
                pass
            return None

    def _process_document_content(self, document_id: str, document_name: str,
                                  kb_id: str, file_data: bytes):
        """处理文档内容"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document_name)[1]) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                # 分割文档
                chunks = self.text_splitter.load_and_split_file(
                    temp_file_path, document_id, kb_id
                )

                logger.info(f"文档分割完成: {document_id}, 分块数量: {len(chunks)}")
                text_list = [f['chunk_content'] for f in chunks]
                chunk_vectors = embedding_utils.get_embeddings(text_list)
                logger.info(f"文档分割完成并完成embedding: {document_id}, embedding数量: {len(chunk_vectors)}")
                # 批量创建分块
                for i, chunk_data in enumerate(chunks):
                    chunk_data['chunk_vector'] = chunk_vectors[i]
                    self.chunk_service.create_chunk(chunk_data)

                logger.info(f"文档处理完成: {document_id}, 分块数量: {len(chunks)}")


                # logger.info(f"文档分割完成: {document_id}, 分块数量: {len(chunks)}")
                # # 批量创建分块
                # for chunk_data in chunks:
                #     # 改用单个embedding获取，上面批量获取embedding速度太慢了【改回单个embedding】
                #     chunk_data['chunk_vector'] = embedding_utils.get_embedding(chunk_data['chunk_content'])
                #     self.chunk_service.create_chunk(chunk_data)
                # logger.info(f"文档处理完成: {document_id}, 分块数量: {len(chunks)}")

            finally:
                # 删除临时文件
                os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            # 更新文档状态为失败
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if document:
                    document.document_status = 2
                    document.document_error = str(e)

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        try:
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if document:
                    return document.to_dict()
                return None
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    def update_document(self, document_id: str, **kwargs) -> bool:
        """更新文档"""
        try:
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if not document:
                    return False

                for key, value in kwargs.items():
                    if hasattr(document, key):
                        setattr(document, key, value)

                logger.info(f"文档更新成功: {document_id}")
                return True
        except Exception as e:
            logger.error(f"文档更新失败: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if not document:
                    return False

                # 删除关联的分块
                chunks = session.query(Chunk).filter_by(document_id=document_id).all()
                for chunk in chunks:
                    self.chunk_service.delete_chunk(chunk.chunk_id)

                # 删除MinIO中的文件
                object_name = f"{document.kb_id}/{document_id}/{document.document_name}"
                minio_client.delete_file(object_name)

                # 删除文档记录
                session.delete(document)

                logger.info(f"文档删除成功: {document_id}")
                return True
        except Exception as e:
            logger.error(f"文档删除失败: {e}")
            return False


    def modify_status(self, document_id: str, document_status: int) -> bool:
        """修改文档状态"""
        try:
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if not document:
                    return False
                if document_status not in [0,1]:
                    # 抛出ValueError
                    # raise ValueError("状态类型不对，只能是1或0")
                    return False
                if document_status == document.document_status:
                    return False

                document.document_status = document_status

                # 更新es数据
                chunks = session.query(Chunk).filter_by(document_id=document_id).all()
                for chunk in chunks:
                    self.chunk_service.modify_document_status(chunk, document_status)

                logger.info(f"文档状态修改成功: {document_id}")
                return True
        except Exception as e:
            logger.error(f"文档状态修改失败: {e}")
            return False


    def list_documents(self, kb_id: str = None, page: int = 1,
                       per_page: int = 10, order_by: str = 'created_time',
                       order_dir: str = 'desc') -> Dict[str, Any]:
        """列出文档"""
        try:
            with db_manager.get_session() as session:
                query = session.query(Document)

                if kb_id:
                    query = query.filter_by(kb_id=kb_id)

                # 排序
                if order_dir == 'desc':
                    query = query.order_by(desc(getattr(Document, order_by)))
                else:
                    query = query.order_by(asc(getattr(Document, order_by)))

                # 分页
                pagination = PaginationQuery(query, page, per_page)
                result = pagination.paginate()

                # 转换为字典
                result['rows'] = [doc.to_dict() for doc in result['rows']]

                return result
        except Exception as e:
            logger.error(f"列出文档失败: {e}")
            return {'rows': [], 'total': 0, 'page': page, 'per_page': per_page}

    def get_document_content(self, document_id: str) -> Tuple[Optional[bytes], Optional[str]]:
        """获取文档内容及类型"""
        try:
            with db_manager.get_session() as session:
                document = session.query(Document).filter_by(document_id=document_id).first()
                if not document:
                    return None, None

                object_name = f"{document.kb_id}/{document_id}/{document.document_name}"
                content = minio_client.download_file(object_name)

                # 获取文件扩展名作为内容类型的提示
                file_ext = os.path.splitext(document.document_name)[1].lower()
                content_type = {
                    '.txt': 'text/plain',
                    '.pdf': 'application/pdf',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.jpg': 'image/jpeg',
                    '.png': 'image/png',
                    '.csv': 'text/csv'
                }.get(file_ext, 'application/octet-stream')

                return content, content_type
        except Exception as e:
            logger.error(f"获取文档内容失败: {e}")
            return None, None

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """获取文档的分块"""
        try:
            with db_manager.get_session() as session:
                chunks = session.query(Chunk).filter_by(document_id=document_id).order_by(Chunk.chunk_order).all()
                return [chunk.to_dict() for chunk in chunks]
        except Exception as e:
            logger.error(f"获取文档分块失败: {e}")
            return []

