import logging

from flask import Blueprint, request, jsonify

from services.chunk_service import ChunkService

logger = logging.getLogger(__name__)
chunk_bp = Blueprint('chunk', __name__)

chunk_service = ChunkService()

@chunk_bp.route('page', methods=['GET'])
def list_documents():
    """获取分块列表"""
    try:
        kb_id = request.args.get('kb_id')
        document_id = request.args.get('document_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        order_by = request.args.get('order_by', 'created_time')
        order_dir = request.args.get('order_dir', 'desc')

        result = chunk_service.list_chunks(
            kb_id=kb_id,
            document_id=document_id,
            page=page,
            per_page=per_page,
            order_by=order_by,
            order_dir=order_dir
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"获取分块列表异常: {e}")
        return jsonify({"error": str(e)}), 500


@chunk_bp.route('/<chunk_id>', methods=['DELETE'])
def delete_chunk(chunk_id):
    """删除分块"""
    try:
        success = chunk_service.delete_chunk(chunk_id)
        if success:
            return jsonify({
                "success": True,
                "message": "分块删除成功"
            }), 200
        else:
            return jsonify({"error": "分块不存在或删除失败"}), 500

    except Exception as e:
        logger.error(f"删除分块异常: {e}")
        return jsonify({"error": str(e)}), 500


@chunk_bp.route('/modify_status', methods=['POST'])
def modify_status():
    """修改分块状态【启用\禁用】"""

    data = request.get_json()  # 获取JSON数据
    print(data, type(data))
    # dto = DocumentStatusModify(**data)
    try:
        success = chunk_service.modify_status(data['chunk_id'], data['chunk_status'])
        if success:
            return jsonify({
                "success": True,
                "message": "修改分块状态成功"
            }), 200
        else:
            return jsonify({"error": "分块不存在或删除失败"}), 500

    except Exception as e:
        logger.error(f"修改分块状态异常: {e}")
        return jsonify({"error": str(e)}), 500