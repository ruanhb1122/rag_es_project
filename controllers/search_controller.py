from flask import Blueprint, request, jsonify
from services.search_service import SearchService, SearchType
import logging

logger = logging.getLogger(__name__)
search_bp = Blueprint('search', __name__)
search_service = SearchService()


@search_bp.route('', methods=['POST'])
def search():
    """搜索接口"""
    try:

        request_json_data = request.get_json()

        kb_id = request_json_data.get('kb_id')
        query = request_json_data.get('query', '')
        search_type = request_json_data.get('search_type', 'hybrid')
        top_k = int(request_json_data.get('top_k', 3))
        min_score = float(request_json_data.get('min_score', 0.5))
        text_weight = float(request_json_data.get('text_weight', 0.3))
        vector_weight = float(request_json_data.get('vector_weight', 0.7))
        use_score_relevance = 'on' == request_json_data.get('use_score')

        if not kb_id:
            return jsonify({"error": "知识库ID不能为空"}), 400

        if not query:
            return jsonify({"error": "搜索内容不能为空"}), 400

        # 转换搜索类型
        try:
            search_type_enum = SearchType(search_type.lower())
        except ValueError:
            return jsonify({"error": f"不支持的搜索类型: {search_type}"}), 400

        # 执行搜索
        results = search_service.search(
            kb_id=kb_id,
            query=query,
            search_type=search_type_enum,
            top_k=top_k,
            min_score=min_score,
            use_score_relevance = use_score_relevance,
            text_weight=text_weight,
            vector_weight=vector_weight
        )

        return jsonify({
            "kb_id": kb_id,
            "query": query,
            "results": results,
            "total": len(results)
        }), 200

    except Exception as e:
        logger.error(f"搜索接口异常: {e}")
        return jsonify({"error": str(e)}), 500


@search_bp.route('/similar', methods=['GET'])
def get_similar_chunks():
    """获取相似分块"""
    try:
        kb_id = request.args.get('kb_id')
        chunk_id = request.args.get('chunk_id')
        top_k = int(request.args.get('top_k', 5))

        if not kb_id or not chunk_id:
            return jsonify({"error": "知识库ID和分块ID不能为空"}), 400

        results = search_service.get_similar_chunks(
            kb_id=kb_id,
            chunk_id=chunk_id,
            top_k=top_k
        )

        return jsonify({
            "kb_id": kb_id,
            "chunk_id": chunk_id,
            "results": results,
            "total": len(results)
        }), 200

    except Exception as e:
        logger.error(f"获取相似分块异常: {e}")
        return jsonify({"error": str(e)}), 500

