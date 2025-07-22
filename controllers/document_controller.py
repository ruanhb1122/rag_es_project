import logging

from flask import Blueprint, request, jsonify

from services.document_service import DocumentService

logger = logging.getLogger(__name__)
document_bp = Blueprint('document', __name__)

document_service = DocumentService()

@document_bp.route('/upload', methods=['POST'])
def upload_document():
    """上传文档"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "未找到文件"}), 400

        file = request.files['file']
        kb_id = request.form.get('kb_id')
        created_by = request.form.get('created_by', 'system')

        if not kb_id:
            return jsonify({"error": "知识库ID不能为空"}), 400

        if file.filename == '':
            return jsonify({"error": "文件名不能为空"}), 400

        # 读取文件数据
        # file_data = file.stream.read()

        # 调用服务创建文档
        document_id = document_service.create_document(
            document_name=file.filename,
            kb_id=kb_id,
            file=file,
            # content_type=file.content_type,
            created_by=created_by
        )

        if document_id:
            return jsonify({
                "success": True,
                "document_id": document_id,
                "message": "文档上传成功"
            }), 201
        else:
            return jsonify({"error": "文档上传失败"}), 500

    except Exception as e:
        logger.error(f"文档上传接口异常: {e}")
        return jsonify({"error": str(e)}), 500


@document_bp.route('page', methods=['GET'])
def list_documents():
    """获取文档列表"""
    try:
        kb_id = request.args.get('kb_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        order_by = request.args.get('order_by', 'created_time')
        order_dir = request.args.get('order_dir', 'desc')

        result = document_service.list_documents(
            kb_id=kb_id,
            page=page,
            per_page=per_page,
            order_by=order_by,
            order_dir=order_dir
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"获取文档列表异常: {e}")
        return jsonify({"error": str(e)}), 500


@document_bp.route('/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """删除文档"""
    try:
        success = document_service.delete_document(document_id)
        if success:
            return jsonify({
                "success": True,
                "message": "文档删除成功"
            }), 200
        else:
            return jsonify({"error": "文档不存在或删除失败"}), 500

    except Exception as e:
        logger.error(f"删除文档异常: {e}")
        return jsonify({"error": str(e)}), 500


@document_bp.route('/modify_status', methods=['POST'])
def modify_status():
    """修改文档状态【启用\禁用】"""

    data = request.get_json()  # 获取JSON数据
    print(data, type(data))
    # dto = DocumentStatusModify(**data)
    try:
        success = document_service.modify_status(data['document_id'], data['document_status'])
        if success:
            return jsonify({
                "success": True,
                "message": "修改文档状态成功"
            }), 200
        else:
            return jsonify({"error": "文档不存在或删除失败"}), 500

    except Exception as e:
        logger.error(f"修改文档状态异常: {e}")
        return jsonify({"error": str(e)}), 500



#
# @document_bp.route('/<document_id>', methods=['GET'])
# def get_document(document_id):
#     """获取单个文档详情"""
#     try:
#         document = document_service.get_document(document_id)
#         if document:
#             return jsonify(document), 200
#         else:
#             return jsonify({"error": "文档不存在"}), 404
#
#     except Exception as e:
#         logger.error(f"获取文档详情异常: {e}")
#         return jsonify({"error": str(e)}), 500
#
#
# @document_bp.route('/<document_id>/chunks', methods=['GET'])
# def get_document_chunks(document_id):
#     """获取文档分块"""
#     try:
#         chunks = document_service.get_document_chunks(document_id)
#         return jsonify({
#             "document_id": document_id,
#             "chunks": chunks,
#             "total": len(chunks)
#         }), 200
#
#     except Exception as e:
#         logger.error(f"获取文档分块异常: {e}")
#         return jsonify({"error": str(e)}), 500