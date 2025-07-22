import logging
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy import desc, asc

from core.database import db_manager, PaginationQuery
from core.elasticsearch_client import es_client
from models.chunk import Chunk

logger = logging.getLogger(__name__)


class ChunkService:
    """分块服务"""

    def create_chunk(self, chunk_data: Dict[str, Any]) -> Optional[str]:
        """创建分块"""
        try:
            with db_manager.get_session() as session:
                # 创建分块记录
                chunk = Chunk.from_dict(chunk_data)
                if not chunk.chunk_id:
                    chunk.chunk_id = str(uuid.uuid4())

                session.add(chunk)
                session.flush()

                # 异步索引到ES
                self._index_chunk_to_es(chunk, chunk_data['chunk_vector'])

                logger.info(f"分块创建成功: {chunk.chunk_id}")
                return chunk.chunk_id

        except Exception as e:
            logger.error(f"分块创建失败: {e}")
            return None

    def _index_chunk_to_es(self, chunk: Chunk, chunk_vector: List[float] = None):
        """索引分块到ES"""
        try:
            # 获取向量
            # embedding = embedding_utils.get_embedding(chunk.chunk_content)
            embedding = chunk_vector
            if not embedding:
                logger.warning(f"获取向量失败: {chunk.chunk_id}")
                return

            # 构建ES文档
            es_doc = {
                'kb_id': chunk.kb_id,
                'id': chunk.chunk_id,
                'chunk_content': chunk.chunk_content,
                'chunk_embedding': embedding,
                'document_id': chunk.document_id,
                'metadata': {
                    'enabled': chunk.chunk_status == 1,
                    'chunk_status': str(chunk.chunk_status),
                    'document_id': chunk.document_id
                }
            }

            # 索引到ES
            index_name = f"kb_{chunk.kb_id}"

            # 确保索引存在
            if not es_client.index_exists(index_name):
                es_client.create_index(index_name)

            success = es_client.add_document(index_name, chunk.chunk_id, es_doc)

            if success:
                # 更新索引状态
                with db_manager.get_session() as session:
                    db_chunk = session.query(Chunk).filter_by(chunk_id=chunk.chunk_id).first()
                    if db_chunk:
                        db_chunk.index_status = '01'
                        logger.info(f"分块索引成功: {chunk.chunk_id}")
            else:
                logger.error(f"分块索引失败: {chunk.chunk_id}")

        except Exception as e:
            logger.error(f"分块索引异常: {e}")

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """获取分块"""
        try:
            with db_manager.get_session() as session:
                chunk = session.query(Chunk).filter_by(chunk_id=chunk_id).first()
                if chunk:
                    return chunk.to_dict()
                return None
        except Exception as e:
            logger.error(f"获取分块失败: {e}")
            return None

    def update_chunk(self, chunk_id: str, **kwargs) -> bool:
        """更新分块"""
        try:
            with db_manager.get_session() as session:
                chunk = session.query(Chunk).filter_by(chunk_id=chunk_id).first()
                if not chunk:
                    return False

                for key, value in kwargs.items():
                    if hasattr(chunk, key):
                        setattr(chunk, key, value)

                # 重新索引到ES
                if 'chunk_content' in kwargs or 'chunk_status' in kwargs:
                    chunk.index_status = '10'  # 标记为需要更新
                    self._index_chunk_to_es(chunk)

                logger.info(f"分块更新成功: {chunk_id}")
                return True
        except Exception as e:
            logger.error(f"分块更新失败: {e}")
            return False

    def delete_chunk(self, chunk_id: str) -> bool:
        """删除分块"""
        try:
            with db_manager.get_session() as session:
                chunk = session.query(Chunk).filter_by(chunk_id=chunk_id).first()
                if not chunk:
                    return False

                # 从ES中删除
                index_name = f"kb_{chunk.kb_id}"
                es_client.delete_document(index_name, chunk_id)

                # 删除数据库记录
                session.delete(chunk)

                logger.info(f"分块删除成功: {chunk_id}")
                return True
        except Exception as e:
            logger.error(f"分块删除失败: {e}")
            return False

    def modify_document_status(self, chunk: Chunk, document_status: int) -> bool:
        """修改文档状态"""
        try:
            index_name = f"kb_{chunk.kb_id}"
            # 更新es文档状态
            es_client.update_document(index_name, chunk.chunk_id, {'metadata': {'enabled': document_status == 1}})

            logger.info(f"分块es更新成功: {chunk.chunk_id}")
            return True
        except Exception as e:
            logger.error(f"分块es更新失败: {e}")
            return False

    def modify_status(self, chunk_id: str, chunk_status: int) -> bool:
        """修改块状态"""
        try:
            with db_manager.get_session() as session:
                chunk = session.query(Chunk).filter_by(chunk_id=chunk_id).first()
                if not chunk:
                    return False

                # 实体类字段更新后，在session执行session.commit() 会更新数据库
                chunk.chunk_status = chunk_status
                # 更新es数据
                index_name = f"kb_{chunk.kb_id}"
                es_client.update_document(index_name, chunk.chunk_id,
                                          {'metadata': {'chunk_status': chunk_status}})


                logger.info(f"分块状态更新成功: {chunk_id}")
                return True
        except Exception as e:
            logger.error(f"分块状态更新失败: {e}")
            return False




    def list_chunks(self, kb_id: str = None, document_id: str = None,
                    page: int = 1, per_page: int = 10,
                    order_by: str = 'chunk_order', order_dir: str = 'asc') -> Dict[str, Any]:
        """列出分块"""
        try:
            with db_manager.get_session() as session:
                query = session.query(Chunk)

                if kb_id:
                    query = query.filter_by(kb_id=kb_id)
                if document_id:
                    query = query.filter_by(document_id=document_id)

                # 排序
                if order_dir == 'desc':
                    query = query.order_by(desc(getattr(Chunk, order_by)))
                else:
                    query = query.order_by(asc(getattr(Chunk, order_by)))

                # 分页
                pagination = PaginationQuery(query, page, per_page)
                result = pagination.paginate()

                # 转换为字典
                result['rows'] = [chunk.to_dict() for chunk in result['rows']]

                return result
        except Exception as e:
            logger.error(f"列出分块失败: {e}")
            return {'rows': [], 'total': 0, 'page': page, 'per_page': per_page}

    def batch_update_index_status(self, chunk_ids: List[str], status: str) -> bool:
        """批量更新索引状态"""
        try:
            with db_manager.get_session() as session:
                chunks = session.query(Chunk).filter(Chunk.chunk_id.in_(chunk_ids)).all()
                for chunk in chunks:
                    chunk.index_status = status

                logger.info(f"批量更新索引状态成功: {len(chunks)}个分块")
                return True
        except Exception as e:
            logger.error(f"批量更新索引状态失败: {e}")
            return False