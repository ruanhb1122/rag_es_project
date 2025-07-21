from sqlalchemy import Column, String, Integer, DateTime, Text, SmallInteger, Index
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class Chunk(Base):
    """分块模型"""
    __tablename__ = 'tb_chunk'

    chunk_id = Column(String(36), primary_key=True, comment='分块id')
    document_id = Column(String(36), nullable=False, comment='文档id')
    chunk_content = Column(Text, nullable=False, comment='分块内容（长文本）')
    chunk_status = Column(SmallInteger, nullable=False, default=1, comment='分块状态 1-启用 0-禁用')
    index_status = Column(String(2), nullable=False, default='00', comment='同步到es状态')
    chunk_order = Column(Integer, comment='排序，从1开始')
    kb_id = Column(String(64), nullable=False, comment='所属知识库id')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    created_by = Column(String(64), comment='创建人')
    updated_time = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='更新时间')
    updated_by = Column(String(64), comment='更新人')

    # 索引定义
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_kb_id', 'kb_id'),
        Index('idx_index_status', 'index_status'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'chunk_content': self.chunk_content,
            'chunk_status': self.chunk_status,
            'index_status': self.index_status,
            'chunk_order': self.chunk_order,
            'kb_id': self.kb_id,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'created_by': self.created_by,
            'updated_time': self.updated_time.isoformat() if self.updated_time else None,
            'updated_by': self.updated_by
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        return cls(
            chunk_id=data.get('chunk_id'),
            document_id=data.get('document_id'),
            chunk_content=data.get('chunk_content'),
            chunk_status=data.get('chunk_status', 1),
            index_status=data.get('index_status', '00'),
            chunk_order=data.get('chunk_order'),
            kb_id=data.get('kb_id'),
            created_by=data.get('created_by'),
            updated_by=data.get('updated_by')
        )