# Flask应用入口
from flask import Flask, jsonify,render_template
from flask_cors import CORS

from controllers.chunk_controller import chunk_bp
from controllers.document_controller import document_bp
from controllers.search_controller import search_bp
from utils.config import config
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    CORS(app)  # 启用CORS

    @app.route('/')
    def index():
        """渲染首页页面"""
        return render_template('index.html')

    @app.route('/upload')
    def upload():
        """渲染上传页面"""
        return render_template('upload.html')

    @app.route('/search')
    def search():
        """渲染搜索页面"""
        return render_template('search.html')

    @app.route('/chat')
    def chat():
        """渲染搜索页面"""
        return render_template('chat.html')

    @app.route('/document_list')
    def document_list():
        """渲染文档列表页面"""
        return render_template('document_list.html')

    @app.route('/chunk_list')
    def chunk_list():
        """渲染分块列表页面"""
        return render_template('chunk_list.html')

    # 加载配置
    app.config['SECRET_KEY'] = config.get('app.secret_key')

    # 注册蓝图
    app.register_blueprint(document_bp, url_prefix='/api/documents')
    app.register_blueprint(chunk_bp, url_prefix='/api/chunks')
    app.register_blueprint(search_bp, url_prefix='/api/search')

    # 健康检查路由
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "message": "服务正常运行"}), 200

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "未找到该资源"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"服务器内部错误: {error}")
        return jsonify({"error": "服务器内部错误，请稍后再试"}), 500

    logger.info(f"应用启动: {config.get('app.host')}:{config.get('app.port')}")


    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=config.get('app.host'),
        port=config.get('app.port'),
        debug=config.get('app.debug')
    )