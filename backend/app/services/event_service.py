"""事件服务 - 处理新闻聚合和事件生成"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import hashlib
import logging

from app.core.aggregator import aggregator
from app.sources.google_news import GoogleNewsSource

logger = logging.getLogger(__name__)


class EventService:
    """事件服务 - 负责新闻聚合和事件生成"""
    
    def __init__(self):
        # 初始化聚合器并注册数据源
        self._init_sources()
        # 简单的内存存储（实际项目中应使用数据库）
        self.events_cache = {}
        self.articles_cache = {}
    
    def _init_sources(self):
        """初始化数据源"""
        # 注册Google News数据源
        google_news = GoogleNewsSource()
        aggregator.register_source(google_news)
        logger.info("数据源初始化完成")
    
    def search_and_aggregate(
        self,
        query: str,
        language: str = 'zh-CN',
        region: str = 'CN',
        limit: int = 20
    ) -> Dict:
        """
        搜索并聚合新闻
        
        Args:
            query: 搜索关键词
            language: 语言代码
            region: 地区代码
            limit: 每个数据源的返回数量限制
            
        Returns:
            聚合后的事件数据
        """
        try:
            # 从所有数据源搜索
            results = aggregator.search_all(
                query,
                language=language,
                region=region,
                limit=limit
            )
            
            # 聚合结果
            aggregated_articles = aggregator.aggregate_results(results)
            
            # 生成事件（简单实现：将所有文章作为一个事件）
            event = self._create_event_from_articles(
                query,
                aggregated_articles
            )
            
            # 缓存事件
            self.events_cache[event['id']] = event
            
            return {
                'success': True,
                'data': {
                    'event': event,
                    'articles': aggregated_articles,
                    'source_count': len(results)
                },
                'message': f'成功从 {len(results)} 个数据源聚合了 {len(aggregated_articles)} 篇文章'
            }
            
        except Exception as e:
            logger.error(f"搜索聚合失败: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f'搜索失败: {str(e)}'
            }
    
    def _create_event_from_articles(
        self,
        query: str,
        articles: List[Dict]
    ) -> Dict:
        """
        从文章列表创建事件
        
        Args:
            query: 搜索关键词
            articles: 文章列表
            
        Returns:
            事件对象
        """
        # 生成事件ID
        event_id = self._generate_event_id(query)
        
        # 提取摘要（取第一篇文章的摘要）
        summary = ""
        if articles:
            summary = articles[0].get('summary', '')[:200]
        
        # 提取所有来源
        sources = []
        for article in articles:
            sources.append({
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'published_at': article.get('published_at', '')
            })
        
        # 提取标签（从所有文章中）
        tags = self._extract_tags(articles)
        
        # 计算日期范围
        dates = [
            article.get('published_at', '')
            for article in articles
            if article.get('published_at')
        ]
        latest_date = max(dates) if dates else datetime.now().isoformat()
        
        event = {
            'id': event_id,
            'title': f'关于"{query}"的新闻聚合',
            'summary': summary,
            'content': self._generate_content(articles),
            'date': latest_date,
            'category': '综合',
            'source_count': len(sources),
            'sources': sources,
            'tags': tags,
            'created_at': datetime.now().isoformat()
        }
        
        return event
    
    def _generate_event_id(self, query: str) -> str:
        """
        生成事件ID
        
        Args:
            query: 查询关键词
            
        Returns:
            事件ID
        """
        # 使用查询词和时间戳生成唯一ID
        unique_string = f"{query}_{datetime.now().date()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def _extract_tags(self, articles: List[Dict]) -> List[str]:
        """
        从文章中提取标签
        
        Args:
            articles: 文章列表
            
        Returns:
            标签列表
        """
        tags = set()
        for article in articles[:5]:  # 只从前5篇文章提取
            # 提取文章中的标签
            article_tags = article.get('tags', [])
            tags.update(article_tags)
        
        return list(tags)[:10]  # 返回最多10个标签
    
    def _generate_content(self, articles: List[Dict]) -> str:
        """
        生成事件内容摘要
        
        Args:
            articles: 文章列表
            
        Returns:
            内容文本
        """
        if not articles:
            return "暂无详细内容"
        
        # 合并前几篇文章的摘要
        content_parts = []
        for i, article in enumerate(articles[:3], 1):
            summary = article.get('summary', '')
            if summary:
                content_parts.append(f"{i}. {summary}")
        
        return "\n\n".join(content_parts) if content_parts else "暂无详细内容"
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """
        根据ID获取事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            事件对象或None
        """
        return self.events_cache.get(event_id)
    
    def get_all_events(self) -> List[Dict]:
        """
        获取所有缓存的事件
        
        Returns:
            事件列表
        """
        return list(self.events_cache.values())


# 全局服务实例
event_service = EventService()

