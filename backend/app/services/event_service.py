"""事件服务 - 处理新闻聚合和事件生成"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import hashlib
import logging
import uuid

from app.core.aggregator import aggregator
from app.core.task_queue import task_queue, TaskStatus
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
        
        # 注册任务处理器
        task_queue.register_handler('search_news', self._handle_search_task)
        
        # 启动任务队列
        task_queue.start()
        logger.info("任务队列已启动")
    
    def submit_search_task(
        self,
        query: str,
        language: str = 'zh-CN',
        region: str = 'CN'
    ) -> Dict:
        """
        提交搜索任务（异步）
        
        Args:
            query: 搜索关键词
            language: 语言代码
            region: 地区代码
            
        Returns:
            任务提交结果
        """
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 提交任务到队列
            task = task_queue.submit_task(
                task_id=task_id,
                task_type='search_news',
                params={
                    'query': query,
                    'language': language,
                    'region': region
                }
            )
            
            # 创建初始事件（状态为处理中）
            event_id = self._generate_event_id(query)
            initial_event = {
                'id': event_id,
                'task_id': task_id,
                'title': f'关于"{query}"的新闻聚合',
                'summary': '',
                'content': '',
                'date': datetime.now().isoformat(),
                'category': '综合',
                'source_count': 0,
                'sources': [],
                'tags': [],
                'created_at': datetime.now().isoformat(),
                'status': 'processing',
                'progress': task.progress
            }
            self.events_cache[event_id] = initial_event
            
            return {
                'success': True,
                'data': {
                    'task_id': task_id,
                    'event_id': event_id,
                    'status': 'submitted'
                },
                'message': '搜索任务已提交，正在处理中...'
            }
            
        except Exception as e:
            logger.error(f"提交搜索任务失败: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f'提交失败: {str(e)}'
            }
    
    def _handle_search_task(self, task, update_progress):
        """
        处理搜索任务
        
        Args:
            task: 任务对象
            update_progress: 进度更新函数
        """
        params = task.params
        query = params['query']
        language = params.get('language', 'zh-CN')
        region = params.get('region', 'CN')
        
        # 获取数据源数量
        source_count = aggregator.get_source_count()
        
        # 从所有数据源搜索
        update_progress(0, source_count, f'开始从 {source_count} 个数据源搜索...')
        
        results = aggregator.search_all(
            query,
            language=language,
            region=region
        )
        
        # 聚合结果
        update_progress(source_count, source_count, '正在聚合结果...')
        aggregated_articles = aggregator.aggregate_results(results)
        
        # 生成事件
        event = self._create_event_from_articles(query, aggregated_articles)
        event['status'] = 'completed'
        event['progress'] = {
            'current': source_count,
            'total': source_count,
            'message': '完成'
        }
        
        # 更新缓存
        self.events_cache[event['id']] = event
        
        return {
            'event_id': event['id'],
            'article_count': len(aggregated_articles),
            'source_count': len(results)
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
        获取所有缓存的事件（包括处理中的）
        
        Returns:
            事件列表
        """
        events = list(self.events_cache.values())
        
        # 更新处理中事件的进度
        for event in events:
            if event.get('status') == 'processing' and event.get('task_id'):
                task = task_queue.get_task(event['task_id'])
                if task:
                    event['progress'] = task.progress
                    # 如果任务已完成，更新事件状态
                    if task.status == TaskStatus.COMPLETED:
                        if task.result:
                            # 重新获取完整事件数据
                            event_id = task.result.get('event_id')
                            if event_id and event_id in self.events_cache:
                                events[events.index(event)] = self.events_cache[event_id]
                    elif task.status == TaskStatus.FAILED:
                        event['status'] = 'failed'
                        event['error'] = task.error
        
        return events
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        task = task_queue.get_task(task_id)
        if not task:
            return None
        
        return task.to_dict()


# 全局服务实例
event_service = EventService()

