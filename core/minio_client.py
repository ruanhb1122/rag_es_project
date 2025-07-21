from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import logging
from utils.config import config

logger = logging.getLogger(__name__)


class MinioClient:
    """MinIO客户端封装"""

    def __init__(self):
        self.client = None
        self.bucket_name = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化MinIO客户端"""
        minio_config = config.get_section('minio')

        self.client = Minio(
            endpoint=minio_config.get('endpoint'),
            access_key=minio_config.get('access_key'),
            secret_key=minio_config.get('secret_key'),
            secure=minio_config.get('secure', False),
            cert_check=False
        )

        self.bucket_name = minio_config.get('bucket_name')

        # 创建bucket（如果不存在）
        self._ensure_bucket_exists()

        logger.info("MinIO客户端初始化完成")

    def _ensure_bucket_exists(self):
        """确保bucket存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket创建成功: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Bucket创建失败: {e}")
            raise

    def upload_file(self, object_name: str, file_data: BinaryIO,
                    file_size: int) -> bool:
        """上传文件"""
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
            )
            logger.info(f"文件上传成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件上传失败: {e}")
            return False

    def upload_file_from_path(self, object_name: str, file_path) -> bool:
        """从文件路径上传文件"""
        try:
            result = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
            logging.info(f"文件上传成功: {result.object_name}")

            # 返回MinIO对象URL
            return f"minio://{self.bucket_name}/{object_name}"
        except S3Error as e:
            logger.error(f"文件上传失败: {e}")
            # return False
            raise e

    def download_file(self, object_name: str) -> Optional[bytes]:
        """下载文件"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"文件下载失败: {e}")
            return None

    def download_file_to_path(self, object_name: str, file_path: str) -> bool:
        """下载文件到指定路径"""
        try:
            self.client.fget_object(self.bucket_name, object_name, file_path)
            logger.info(f"文件下载成功: {object_name} -> {file_path}")
            return True
        except S3Error as e:
            logger.error(f"文件下载失败: {e}")
            return False

    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"文件删除成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件删除失败: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def list_files(self, prefix: str = None) -> list:
        """列出文件"""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"列出文件失败: {e}")
            return []

    def get_file_url(self, object_name: str, expires_in_seconds: int = 3600) -> Optional[str]:
        """获取文件的预签名URL"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires_in_seconds
            )
            return url
        except S3Error as e:
            logger.error(f"获取文件URL失败: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.bucket_exists(self.bucket_name)
            return True
        except Exception as e:
            logger.error(f"MinIO健康检查失败: {e}")
            return False


# 全局MinIO客户端实例
minio_client = MinioClient()