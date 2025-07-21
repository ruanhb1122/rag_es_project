from sqlalchemy import Column, String, Integer, DateTime, Text, SmallInteger
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class Document(Base):
    """文档模型"""
    __tablename__ = 'tb_document'

    document_id = Column(String(36), primary_key=True, comment='文档id')
    document_name = Column(String(255), nullable=False, comment='文档名称')
    document_status = Column(SmallInteger, nullable=False, default=1, comment='状态 1-启用 0-禁用 2-失败')
    document_error = Column(Text, comment='失败原因（长文本）')
    document_order = Column(Integer, comment='排序，从1开始')
    kb_id = Column(String(64), nullable=False, comment='所属知识库id')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    created_by = Column(String(64), comment='创建人')
    updated_time = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='更新时间')
    updated_by = Column(String(64), comment='更新人')

    def to_dict(self):
        """转换为字典"""
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'document_status': self.document_status,
            'document_error': self.document_error,
            'document_order': self.document_order,
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
            document_id=data.get('document_id'),
            document_name=data.get('document_name'),
            document_status=data.get('document_status', 1),
            document_error=data.get('document_error'),
            document_order=data.get('document_order'),
            kb_id=data.get('kb_id'),
            created_by=data.get('created_by'),
            updated_by=data.get('updated_by')
        )