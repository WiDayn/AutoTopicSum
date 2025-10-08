"""事件相关API接口"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.event_service import event_service


@api_bp.route('/events/search', methods=['GET'])
def search_events():
    """
    搜索事件接口
    参数：
        - query: 搜索关键词（必需）
        - language: 语言代码，默认'zh-CN'
        - region: 地区代码，默认'CN'
        - limit: 每个数据源的返回数量限制，默认20
    """
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({
            'success': False,
            'data': None,
            'message': '搜索关键词不能为空'
        }), 400
    
    language = request.args.get('language', 'zh-CN')
    region = request.args.get('region', 'CN')
    limit = request.args.get('limit', 20, type=int)
    
    # 调用事件服务进行搜索和聚合
    result = event_service.search_and_aggregate(
        query=query,
        language=language,
        region=region,
        limit=limit
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@api_bp.route('/events', methods=['GET'])
def get_events():
    """
    获取事件列表接口
    返回所有已缓存的事件
    """
    try:
        events = event_service.get_all_events()
        
        # 按创建时间排序
        events.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        
        return jsonify({
            'success': True,
            'data': {
                'events': events,
                'total': len(events)
            },
            'message': '获取成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'data': None,
            'message': f'获取失败: {str(e)}'
        }), 500


@api_bp.route('/events/<event_id>', methods=['GET'])
def get_event_detail(event_id):
    """
    获取事件详情接口
    参数：
        - event_id: 事件ID（字符串）
    """
    try:
        event = event_service.get_event_by_id(event_id)
        
        if not event:
            return jsonify({
                'success': False,
                'data': None,
                'message': '事件不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': event,
            'message': '获取成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'data': None,
            'message': f'获取失败: {str(e)}'
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'API服务运行正常'
    })

