from sqlalchemy import create_engine, text
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, List, Dict, Any
import logging
from utils.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理类"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库连接"""
        db_config = config.get_section('database.mysql')

        # 构建数据库URL
        database_url = (
            f"mysql+pymysql://{db_config['username']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            f"?charset={db_config['charset']}"
        )

        # 创建引擎
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=db_config.get('pool_size', 10),
            max_overflow=db_config.get('max_overflow', 20),
            pool_timeout=db_config.get('pool_timeout', 30),
            pool_pre_ping=True,
            echo=config.get('app.debug', False)
        )

        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info("数据库连接初始化完成")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作异常: {e}")
            raise
        finally:
            session.close()

    def execute_raw_sql(self, sql: str, params: dict = None) -> List[Dict[str, Any]]:
        """执行原生SQL查询"""
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            return [dict(row) for row in result.fetchall()]

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("数据库表创建完成")


# 创建基础模型类
Base = declarative_base()

# 全局数据库管理器实例
db_manager = DatabaseManager()


# 分页查询基类
class PaginationQuery:
    """分页查询工具"""

    def __init__(self, query, page: int = 1, per_page: int = 10):
        self.query = query
        self.page = max(1, page)
        self.per_page = min(max(1, per_page), 100)  # 限制每页最大100条

    def paginate(self):
        """执行分页查询"""
        total = self.query.count()
        rows = self.query.offset((self.page - 1) * self.per_page).limit(self.per_page).all()

        return {
            'rows': rows,
            'total': total,
            'page': self.page,
            'per_page': self.per_page,
            'pages': (total + self.per_page - 1) // self.per_page,
            'has_prev': self.page > 1,
            'has_next': self.page * self.per_page < total
        }


if __name__ == '__main__':
    print(db_manager.test_connection())