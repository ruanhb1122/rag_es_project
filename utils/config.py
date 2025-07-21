import yaml
import os
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

import pathlib

_project_root = str(pathlib.Path(__file__).resolve().parents[1])

class Config:
    """配置文件读取工具类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(_project_root,'config', 'backend.yaml')

        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误: {e}")
            raise ValueError(f"配置文件格式错误: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持嵌套key访问
        例如: config.get('database.mysql.host')
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self.get(section, {})

    def reload(self):
        """重新加载配置文件"""
        self._config = self._load_config()


# 全局配置实例
config = Config()