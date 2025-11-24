"""分词相关API接口"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.word_segmentation_service import word_segmentation_service


@api_bp.route('/word-segmentation', methods=['POST'])
def segment_text():
    """
    分词接口
    Body参数：
        - text: 待分词的文本（必需）
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'data': None,
            'message': '输入文本不能为空'
        }), 400
    
    # 执行分词
    result = word_segmentation_service.segment(text)
    
    if not result['success']:
        return jsonify(result), 500
    
    return jsonify(result)


@api_bp.route('/word-segmentation/batch', methods=['POST'])
def batch_segment_text():
    """
    批量分词接口
    Body参数：
        - texts: 待分词的文本列表（必需）
    """
    data = request.get_json() or {}
    texts = data.get('texts', [])
    
    if not texts or not isinstance(texts, list):
        return jsonify({
            'success': False,
            'data': None,
            'message': '输入文本列表不能为空'
        }), 400
    
    # 执行批量分词
    result = word_segmentation_service.batch_segment(texts)
    
    if not result['success']:
        return jsonify(result), 500
    
    return jsonify(result)

