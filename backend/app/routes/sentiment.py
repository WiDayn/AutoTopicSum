from flask import Blueprint, request, jsonify
from app.services.sentiment_service import sentiment_analyzer
import logging

logger = logging.getLogger(__name__)

# 创建情感分析蓝图
sentiment_bp = Blueprint('sentiment', __name__)

@sentiment_bp.route('/analyze', methods=['POST'])
def analyze_sentiment():
    """分析单个文本的情感"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': '缺少文本参数'}), 400
        
        text = data['text']
        if not text.strip():
            return jsonify({'error': '文本不能为空'}), 400
        
        result = sentiment_analyzer.analyze_text(text)
        
        logger.info(f"情感分析请求完成: {result['sentiment']}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"情感分析API错误: {str(e)}")
        return jsonify({'error': '分析失败'}), 500

@sentiment_bp.route('/analyze-news', methods=['POST'])
def analyze_news():
    """批量分析新闻情感"""
    try:
        data = request.get_json()
        
        if not data or 'news_list' not in data:
            return jsonify({'error': '缺少新闻列表参数'}), 400
        
        news_list = data['news_list']
        if not isinstance(news_list, list):
            return jsonify({'error': 'news_list 必须是列表'}), 400
        
        results = sentiment_analyzer.analyze_news_list(news_list)
        
        logger.info(f"批量新闻情感分析完成: {len(results)} 条新闻")
        return jsonify({
            'analyzed_news': results,
            'total_count': len(results)
        })
        
    except Exception as e:
        logger.error(f"批量情感分析API错误: {str(e)}")
        return jsonify({'error': '批量分析失败'}), 500

@sentiment_bp.route('/trend', methods=['GET'])
def get_sentiment_trend():
    """获取情感趋势"""
    try:
        trend_data = sentiment_analyzer.get_trend_analysis()
        return jsonify(trend_data)
        
    except Exception as e:
        logger.error(f"获取情感趋势错误: {str(e)}")
        return jsonify({'error': '获取趋势失败'}), 500

@sentiment_bp.route('/history', methods=['GET'])
def get_analysis_history():
    """获取分析历史"""
    try:
        return jsonify({
            'history': sentiment_analyzer.analysis_history,
            'total_count': len(sentiment_analyzer.analysis_history)
        })
    except Exception as e:
        logger.error(f"获取分析历史错误: {str(e)}")
        return jsonify({'error': '获取历史失败'}), 500

@sentiment_bp.route('/stats', methods=['GET'])
def get_sentiment_stats():
    """获取情感统计"""
    try:
        trend_data = sentiment_analyzer.get_trend_analysis()
        return jsonify(trend_data.get('statistics', {}))
    except Exception as e:
        logger.error(f"获取情感统计错误: {str(e)}")
        return jsonify({'error': '获取统计失败'}), 500