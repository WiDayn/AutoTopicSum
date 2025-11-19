import jieba
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        # 初始化情感词典
        self.positive_words = set([
            '好', '优秀', '伟大', '成功', '胜利', '高兴', '喜欢', '爱', 
            '美丽', '完美', '进步', '发展', '增长', '提升', '利好', '乐观',
            '上涨', '盈利', '丰收', '突破', '创新', '领先', '冠军', '金牌',
            '成就', '荣誉', '庆祝', '欢乐', '幸福', '满意', '称赞', '表扬'
        ])
        self.negative_words = set([
            '坏', '糟糕', '失败', '痛苦', '讨厌', '恨', '丑', '差', 
            '恶心', '可怕', '下跌', '下降', '亏损', '危机', '利空', '悲观',
            '崩溃', '破产', '衰退', '下跌', '损失', '灾难', '事故', '死亡',
            '冲突', '战争', '抗议', '愤怒', '失望', '批评', '谴责', '处罚'
        ])
        
        # 情感分析历史记录
        self.analysis_history = []
        
        logger.info("情感分析器初始化完成")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """分析单个文本的情感"""
        if not text or not text.strip():
            return self._get_neutral_result()
        
        try:
            # 中文分词
            words = jieba.lcut(text)
            
            # 计算情感分数
            positive_score = sum(1 for word in words if word in self.positive_words)
            negative_score = sum(1 for word in words if word in self.negative_words)
            total_meaningful_words = len([w for w in words if len(w) > 1])
            
            if total_meaningful_words == 0:
                return self._get_neutral_result()
            
            # 归一化分数
            pos_norm = positive_score / total_meaningful_words
            neg_norm = negative_score / total_meaningful_words
            neutral_norm = max(0, 1 - pos_norm - neg_norm)
            
            # 调整分数使总和为1
            total = pos_norm + neutral_norm + neg_norm
            if total > 0:
                pos_norm /= total
                neutral_norm /= total
                neg_norm /= total
            
            scores = {
                'positive': float(pos_norm),
                'neutral': float(neutral_norm),
                'negative': float(neg_norm)
            }
            
            # 确定主要情感
            max_sentiment = max(scores.items(), key=lambda x: x[1])
            sentiment = max_sentiment[0]
            confidence = max_sentiment[1]
            
            result = {
                'sentiment': sentiment,
                'confidence': round(confidence, 3),
                'scores': scores,
                'text_length': len(text),
                'word_count': len(words),
                'timestamp': datetime.now().isoformat()
            }
            
            # 记录分析历史
            self.analysis_history.append(result)
            if len(self.analysis_history) > 100:  # 限制历史记录数量
                self.analysis_history = self.analysis_history[-50:]
            
            logger.info(f"情感分析完成: {sentiment} (置信度: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            return self._get_neutral_result()
    
    def analyze_news_list(self, news_list: List[Dict]) -> List[Dict]:
        """批量分析新闻情感"""
        results = []
        for news in news_list:
            text = f"{news.get('title', '')} {news.get('content', '')}"
            sentiment_result = self.analyze_text(text)
            results.append({
                **news,
                'sentiment_analysis': sentiment_result
            })
        return results
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """获取情感趋势分析"""
        if not self.analysis_history:
            return {'trend': 'neutral', 'data': []}
        
        recent_analyses = self.analysis_history[-20:]  # 最近20次分析
        
        trend_data = []
        for analysis in recent_analyses:
            trend_data.append({
                'timestamp': analysis['timestamp'],
                'sentiment': analysis['sentiment'],
                'scores': analysis['scores']
            })
        
        # 计算趋势
        positive_count = sum(1 for a in recent_analyses if a['sentiment'] == 'positive')
        negative_count = sum(1 for a in recent_analyses if a['sentiment'] == 'negative')
        
        if positive_count > negative_count:
            trend = 'positive'
        elif negative_count > positive_count:
            trend = 'negative'
        else:
            trend = 'neutral'
        
        return {
            'trend': trend,
            'total_analyses': len(self.analysis_history),
            'recent_data': trend_data,
            'statistics': {
                'positive': positive_count,
                'neutral': len(recent_analyses) - positive_count - negative_count,
                'negative': negative_count
            }
        }
    
    def _get_neutral_result(self) -> Dict[str, Any]:
        """获取中性结果"""
        return {
            'sentiment': 'neutral',
            'confidence': 0.33,
            'scores': {'positive': 0.33, 'neutral': 0.34, 'negative': 0.33},
            'text_length': 0,
            'word_count': 0,
            'timestamp': datetime.now().isoformat()
        }

# 创建全局情感分析器实例
sentiment_analyzer = SentimentAnalyzer()