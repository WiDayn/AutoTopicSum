"""事件相关API接口"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.event_service import event_service
from app.core.beat_encoder import beat_encoder


@api_bp.route('/events/search', methods=['POST'])
def search_events():
    """
    提交搜索任务接口（异步）
    Body参数：
        - query: 搜索关键词（必需）
        - language: 语言代码，默认'zh-CN'
        - region: 地区代码，默认'CN'
    """
    data = request.get_json() or {}
    query = data.get('query', '')
    
    if not query:
        return jsonify({
            'success': False,
            'data': None,
            'message': '搜索关键词不能为空'
        }), 400
    
    language = data.get('language', 'zh-CN')
    region = data.get('region', 'CN')
    
    # 提交搜索任务到队列
    result = event_service.submit_search_task(
        query=query,
        language=language,
        region=region
    )
    
    return jsonify(result)


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


@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取任务状态接口
    参数：
        - task_id: 任务ID
    """
    try:
        task_status = event_service.get_task_status(task_id)
        
        if not task_status:
            return jsonify({
                'success': False,
                'data': None,
                'message': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': task_status,
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


@api_bp.route('/beat/encoding-record', methods=['GET'])
def get_beat_encoding_record():
    """
    获取BEAT编码器记录接口
    返回编码映射和最后一次聚类的统计信息
    """
    try:
        record = beat_encoder.get_encoding_record()
        
        return jsonify({
            'success': True,
            'data': record,
            'message': '获取成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'data': None,
            'message': f'获取失败: {str(e)}'
        }), 500

