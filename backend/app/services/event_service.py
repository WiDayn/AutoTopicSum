"""事件服务 - 处理新闻聚合和事件生成"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import defaultdict
import hashlib
import logging
import uuid
import requests
import re
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from app.core.aggregator import aggregator
from app.core.task_queue import task_queue, TaskStatus
from app.sources.google_news import GoogleNewsSource
from app.core.bert_encoder import bert_encoder
from app.core.timeline_generator import get_timeline_generator
from config import Config

# 新增情感分析导入
from app.services.sentiment_service import sentiment_analyzer
# 新增分词服务导入
from app.services.word_segmentation_service import word_segmentation_service

logger = logging.getLogger(__name__)


class EventService:
    """事件服务 - 负责新闻聚合和事件生成"""
    
    def __init__(self):
        # 初始化聚合器并注册数据源
        self._init_sources()
        # 简单的内存存储
        self.events_cache = {}
        self.articles_cache = {}
        # 媒体信息缓存，避免重复分析同一媒体
        self.media_info_cache = {}
        # 缓存锁，保证线程安全
        self.cache_lock = threading.Lock()
        # 加载持久化的媒体缓存
        self._load_media_cache()

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

        curr_prog, curr_step = 0, 1
        total_step = 7
        prog_of_single_step = int(100. / total_step)

        # 阶段1: 从数据源搜索
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 开始搜索新闻...')
        results = aggregator.search_all(
            query,
            language=language,
            region=region
        )
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段2: 聚合结果
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在聚合结果...')
        aggregated_articles = aggregator.aggregate_results(query, results)
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段3: 情感分析
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在进行情感分析...')
        articles_with_sentiment = self._analyze_articles_sentiment(aggregated_articles, update_progress)
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段4: 分析媒体来源
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在分析媒体来源...')
        media_info_dict = self._analyze_sources(aggregated_articles, update_progress, curr_step, total_step)
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段5：生成时间线
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在生成时间线...')
        timeline_nodes = self._generate_timeline(task.task_id, aggregated_articles)
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段6：分词处理
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在进行分词处理...')
        segmentation_result = None
        try:
            seg_result = word_segmentation_service.segment(query)
            if seg_result.get('success') and seg_result.get('data'):
                segmentation_result = seg_result['data']
                logger.info(f"查询词 '{query}' 分词成功，共 {segmentation_result.get('total_words', 0)} 个词")
            else:
                logger.warning(f"查询词 '{query}' 分词失败: {seg_result.get('message', '未知错误')}")
        except Exception as e:
            logger.error(f"分词处理异常: {str(e)}")
        curr_prog += prog_of_single_step
        curr_step += 1

        # 阶段7：使用LLM生成事件摘要
        update_progress(curr_prog, 100, f'步骤{curr_step}/{total_step}: 正在生成事件摘要...')
        ai_summary = None
        try:
            ai_summary = self._generate_event_summary_with_ai(
                query,
                articles_with_sentiment,
                timeline_nodes,
                update_progress,
                curr_step,
                total_step
            )
            if ai_summary:
                logger.info(f"事件摘要生成成功，长度: {len(ai_summary)} 字符")
            else:
                logger.warning("事件摘要生成失败，将使用默认摘要")
        except Exception as e:
            logger.error(f"生成事件摘要异常: {str(e)}")
        curr_prog += prog_of_single_step
        curr_step += 1

        if curr_step == total_step:
            curr_prog = 100
        
        # 生成事件
        event = self._create_event_from_articles(
            query,
            articles_with_sentiment,
            media_info_dict,
            timeline_nodes,
            segmentation_result,
            ai_summary,
        )
        event['status'] = 'completed'
        event['progress'] = {
            'current': curr_prog,
            'total': 100,
            'message': '完成'
        }
        
        # 更新缓存
        self.events_cache[event['id']] = event
        
        return {
            'event_id': event['id'],
            'article_count': len(articles_with_sentiment),
            'source_count': len(results),
            'media_analyzed': len(media_info_dict),
            'timeline': len(timeline_nodes),
        }
    
    def _analyze_articles_sentiment(self, articles: List[Dict], update_progress=None) -> List[Dict]:
        """
        批量分析文章情感（使用线程池并发处理）
        
        Args:
            articles: 文章列表
            update_progress: 进度更新函数
            
        Returns:
            包含情感分析结果的文章列表
        """
        if not articles:
            return articles
        
        logger.info(f"开始对 {len(articles)} 篇文章进行情感分析")
        
        # 使用线程池并发处理情感分析
        articles_with_sentiment = []
        total_articles = len(articles)
        completed_count = 0
        
        # 创建锁用于线程安全的计数和进度更新
        lock = threading.Lock()
        
        def analyze_single_article(article):
            """分析单篇文章情感的辅助函数"""
            nonlocal completed_count
            
            try:
                # 组合标题和内容进行情感分析
                text = f"{article.get('title', '')} {article.get('content', '')}"
                sentiment_result = sentiment_analyzer.analyze_text(text)
                
                # 将情感分析结果添加到文章对象中
                article_with_sentiment = article.copy()
                article_with_sentiment['sentiment_analysis'] = sentiment_result
                
                # 线程安全的更新进度
                with lock:
                    completed_count += 1
                    articles_with_sentiment.append(article_with_sentiment)
                    
                    # 更新进度
                    if update_progress:
                        # 计算情感分析阶段的进度 (50-75之间)
                        sentiment_progress = 50 + int((completed_count / total_articles) * 25)
                        update_progress(
                            sentiment_progress,
                            100,
                            f'步骤3/4: 正在进行情感分析 ({completed_count}/{total_articles})'
                        )
                
                return article_with_sentiment
                
            except Exception as e:
                logger.error(f"分析文章情感失败: {str(e)}")
                # 如果分析失败，返回原始文章
                return article
        
        # 使用线程池并发处理，最大5个线程（避免过多请求）
        max_workers = min(5, total_articles)
        logger.info(f"使用 {max_workers} 个线程并发分析文章情感")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_article = {
                executor.submit(analyze_single_article, article): article 
                for article in articles
            }
            
            # 等待所有任务完成
            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    future.result()  # 获取结果，会抛出任何异常
                except Exception as e:
                    logger.error(f"分析文章情感时出错: {str(e)}")
        
        # 计算情感统计
        sentiment_stats = self._calculate_sentiment_stats(articles_with_sentiment)
        logger.info(f"情感分析完成: {sentiment_stats}")
        
        return articles_with_sentiment
    
    def _calculate_sentiment_stats(self, articles: List[Dict]) -> Dict[str, Any]:
        """
        计算情感分析统计
        
        Args:
            articles: 包含情感分析结果的文章列表
            
        Returns:
            情感统计字典
        """
        sentiment_count = {
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        
        total_confidence = 0
        valid_articles = 0
        
        for article in articles:
            sentiment_analysis = article.get('sentiment_analysis')
            if sentiment_analysis:
                sentiment = sentiment_analysis.get('sentiment')
                confidence = sentiment_analysis.get('confidence', 0)
                
                if sentiment in sentiment_count:
                    sentiment_count[sentiment] += 1
                    total_confidence += confidence
                    valid_articles += 1
        
        # 计算百分比
        total_with_sentiment = sum(sentiment_count.values())
        if total_with_sentiment > 0:
            sentiment_percentages = {
                sentiment: (count / total_with_sentiment) * 100
                for sentiment, count in sentiment_count.items()
            }
        else:
            sentiment_percentages = {sentiment: 0 for sentiment in sentiment_count.keys()}
        
        # 计算平均置信度
        avg_confidence = total_confidence / valid_articles if valid_articles > 0 else 0
        
        return {
            'counts': sentiment_count,
            'percentages': sentiment_percentages,
            'average_confidence': round(avg_confidence, 3),
            'total_analyzed': valid_articles
        }
    
    def _create_event_from_articles(
        self,
        query: str,
        articles: List[Dict],
        media_info_dict: Optional[Dict[str, Dict]] = None,
        timeline_nodes=None,
        segmentation_result: Optional[Dict] = None,
        ai_summary: Optional[str] = None
    ) -> Dict:
        """
        从文章列表创建事件
        
        Args:
            query: 搜索关键词
            articles: 文章列表
            media_info_dict: 媒体信息字典（可选）
            timeline_nodes: 时间线dict

        Returns:
            事件对象
        """
        # 生成事件ID
        event_id = self._generate_event_id(query)
        
        # 使用AI生成的摘要，如果没有则使用第一篇文章的摘要
        summary = ""
        if ai_summary:
            summary = ai_summary
        elif articles:
            summary = articles[0].get('summary', '')[:200]
        
        # 提取所有来源，并关联媒体信息
        sources = []
        dates = []
        for article in articles:
            source_name = article.get('source', '')
            published_date = article.get('published_at', '')
            source_item = {
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': source_name,
                'published_at': article.get('published_at', ''),
                # 添加情感分析结果
                'sentiment_analysis': article.get('sentiment_analysis', {}),
                # 添加过滤状态
                'filter': article.get('filter', False)
            }

            if published_date:
                dates.append(published_date)

            # 添加媒体信息（如果有）
            if media_info_dict and source_name in media_info_dict:
                source_item['media_info'] = media_info_dict[source_name]
            
            sources.append(source_item)
        
        # 提取标签（从所有文章中）
        tags = self._extract_tags(articles)
        
        # 计算日期范围
        latest_date = max(dates) if dates else datetime.now().isoformat()
        
        # 计算情感统计
        sentiment_stats = self._calculate_sentiment_stats(articles)
        
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
            'created_at': datetime.now().isoformat(),
            'sentiment_analysis': sentiment_stats,  # 新增情感分析统计
            'media_analysis': {
                'total_media': len(media_info_dict) if media_info_dict else 0,
                'media_info': media_info_dict if media_info_dict else {}
            },
            'timeline': timeline_nodes,
            'word_segmentation': segmentation_result,  # 新增分词结果
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
    
    def _analyze_media_with_ai(self, media_name: str) -> Optional[Dict]:
        """
        使用硅基流动 AI 分析媒体信息（线程安全）
        
        Args:
            media_name: 媒体名称
            
        Returns:
            媒体信息字典或None（如果分析失败）
        """
        # 检查缓存（线程安全）
        with self.cache_lock:
            if media_name in self.media_info_cache:
                logger.info(f"从缓存中获取媒体信息: {media_name}")
                return self.media_info_cache[media_name]
        
        # 检查是否配置了 API Key
        if not Config.SILICONFLOW_API_KEY:
            logger.warning("未配置 SILICONFLOW_API_KEY，跳过媒体分析")
            return None
        
        # 构建 prompt
        prompt = f"""请用官方媒体，个人账号，知名报纸，科技博客etc，或按政治光谱/立场，所有制与资金来源，内容垂直领域，地理位置与目标受众评价这个媒体的立场，不需要给出分析，直接得出结果，如果有多个关键词请用/隔开，不需要额外的任何解释，严格遵守输出格式，使用中文回答：
目标媒体：{media_name}
输出格式：
所有制：
资金来源：
政治立场：
内容领域：
地理位置：
目标受众：
媒体类别："""
        
        try:
            # 调用硅基流动 API
            headers = {
                'Authorization': f'Bearer {Config.SILICONFLOW_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': Config.SILICONFLOW_MODEL,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 500
            }
            
            logger.info(f"正在分析媒体: {media_name}")
            response = requests.post(
                Config.SILICONFLOW_API_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code != 200:
                logger.error(f"API 请求失败: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                logger.error(f"API 返回内容为空")
                return None
            
            # 解析返回的内容
            media_info = self._parse_media_info(content, media_name)
            
            # 使用BERT编码器聚合相似关键词
            if media_info:
                media_info = bert_encoder.encode_media_info(media_info)
                logger.debug(f"媒体 {media_name} 的关键词已编码")
            
            # 缓存结果（线程安全）
            if media_info:
                with self.cache_lock:
                    self.media_info_cache[media_name] = media_info
                logger.info(f"成功分析媒体: {media_name}")
            
            return media_info
            
        except requests.exceptions.Timeout:
            logger.error(f"分析媒体 {media_name} 超时")
            return None
        except Exception as e:
            logger.error(f"分析媒体 {media_name} 失败: {str(e)}")
            return None
    
    def _parse_media_info(self, content: str, media_name: str) -> Dict:
        """
        解析 AI 返回的媒体信息
        
        Args:
            content: AI 返回的内容
            media_name: 媒体名称
            
        Returns:
            解析后的媒体信息字典
        """
        media_info = {
            'name': media_name,
            'ownership': '',
            'funding': '',
            'political_stance': '',
            'content_domain': '',
            'location': '',
            'target_audience': '',
            'category': ''
        }
        
        try:
            # 使用正则表达式提取各个字段
            patterns = {
                'ownership': r'所有制[:：]\s*(.+)',
                'funding': r'资金来源[:：]\s*(.+)',
                'political_stance': r'政治立场[:：]\s*(.+)',
                'content_domain': r'内容领域[:：]\s*(.+)',
                'location': r'地理位置[:：]\s*(.+)',
                'target_audience': r'目标受众[:：]\s*(.+)',
                'category': r'媒体类别[:：]\s*(.+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    media_info[key] = match.group(1).strip()
            
            return media_info
            
        except Exception as e:
            logger.error(f"解析媒体信息失败: {str(e)}")
            return media_info
    
    def _analyze_sources(self, articles: List[Dict], update_progress=None, curr_step=None, total_step=None) -> Dict[str, Dict]:
        """
        分析所有文章的媒体来源（使用线程池并发处理）
        
        Args:
            articles: 文章列表
            update_progress: 进度更新函数
            
        Returns:
            媒体信息字典 {media_name: media_info}
        """
        # 提取所有唯一的媒体来源
        sources = set()
        for article in articles:
            source = article.get('source', '').strip()
            if source:
                sources.add(source)
        
        logger.info(f"发现 {len(sources)} 个唯一媒体来源")
        
        if not sources:
            return {}
        
        # 分析每个媒体来源（使用线程池并发）
        media_info_dict = {}
        total_sources = len(sources)
        completed_count = 0
        new_media_analyzed = 0
        
        # 创建锁用于线程安全的计数和进度更新
        lock = threading.Lock()
        
        def analyze_single_media(source):
            """分析单个媒体的辅助函数"""
            nonlocal completed_count, new_media_analyzed
            
            # 记录分析前缓存中是否有这个媒体
            with self.cache_lock:
                had_in_cache = source in self.media_info_cache
            
            media_info = self._analyze_media_with_ai(source)
            
            # 线程安全的更新进度
            with lock:
                completed_count += 1
                is_new_media = False
                
                if media_info:
                    media_info_dict[source] = media_info
                    # 如果是新分析的媒体（之前不在缓存中），计数
                    if not had_in_cache:
                        new_media_analyzed += 1
                        is_new_media = True
                
                # 更新进度
                if update_progress and curr_step is not None and total_step is not None:
                    # 计算媒体分析阶段的进度
                    prog_of_single_step = 100. / total_step
                    curr_prog = int(prog_of_single_step * (curr_step - 1))

                    media_progress = curr_prog + int((completed_count / total_sources) * prog_of_single_step)
                    update_progress(
                        media_progress,
                        100,
                        f'步骤{curr_step}/{total_step}: 正在分析媒体来源 ({completed_count}/{total_sources})'
                    )
            
            # 如果是新分析的媒体，立即保存到文件（防止中断导致数据丢失）
            if is_new_media:
                try:
                    self._save_media_cache()
                    logger.info(f"已保存新分析的媒体: {source}")
                except Exception as e:
                    logger.error(f"保存媒体缓存时出错: {str(e)}")
            
            return media_info
        
        # 使用线程池并发处理，最大10个线程
        max_workers = min(10, total_sources)  # 不超过媒体数量
        logger.info(f"使用 {max_workers} 个线程并发分析媒体")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_source = {
                executor.submit(analyze_single_media, source): source 
                for source in sources
            }
            
            # 等待所有任务完成
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    future.result()  # 获取结果，会抛出任何异常
                except Exception as e:
                    logger.error(f"分析媒体 {source} 时出错: {str(e)}")
        
        # 所有媒体分析完成
        if new_media_analyzed > 0:
            logger.info(f"本次共新分析了 {new_media_analyzed} 个媒体（已实时保存）")
        
        logger.info(f"成功分析 {len(media_info_dict)} 个媒体来源")
        return media_info_dict
    
    def _load_media_cache(self):
        """从JSON文件加载媒体缓存"""
        cache_file = Config.MEDIA_CACHE_FILE
        
        try:
            # 确保目录存在
            cache_dir = os.path.dirname(cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                logger.info(f"创建缓存目录: {cache_dir}")
            
            # 如果文件存在，加载缓存
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    raw_cache = json.load(f)
                
                # 使用BERT编码器对加载的缓存进行编码（确保一致性）
                self.media_info_cache = bert_encoder.batch_encode_media(raw_cache)
                
                # 如果编码后有变化，保存更新后的缓存
                if raw_cache != self.media_info_cache:
                    logger.info("检测到缓存数据需要编码更新，正在保存...")
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(self.media_info_cache, f, ensure_ascii=False, indent=2)
                
                logger.info(f"从文件加载了 {len(self.media_info_cache)} 个媒体缓存（已编码）")
            else:
                logger.info("缓存文件不存在，将创建新的缓存")
                self.media_info_cache = {}
                
        except json.JSONDecodeError as e:
            logger.error(f"缓存文件格式错误: {str(e)}，将使用空缓存")
            self.media_info_cache = {}
        except Exception as e:
            logger.error(f"加载媒体缓存失败: {str(e)}，将使用空缓存")
            self.media_info_cache = {}
    
    def _save_media_cache(self):
        """保存媒体缓存到JSON文件（线程安全，自动编码）"""
        cache_file = Config.MEDIA_CACHE_FILE
        
        try:
            # 确保目录存在
            cache_dir = os.path.dirname(cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            # 保存缓存（线程安全）
            with self.cache_lock:
                cache_data = dict(self.media_info_cache)  # 复制一份避免长时间持有锁
            
            # 使用BERT编码器对所有媒体信息进行编码
            encoded_cache_data = bert_encoder.batch_encode_media(cache_data)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(encoded_cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(encoded_cache_data)} 个媒体缓存到文件（已编码）")
            
        except Exception as e:
            logger.error(f"保存媒体缓存失败: {str(e)}")

    def _generate_timeline(self, task_id, articles: List[Dict]):
        timeline_generator = get_timeline_generator()
        timeline_nodes = timeline_generator.generate_timeline(task_id, articles)
        return timeline_nodes
    
    def _generate_event_summary_with_ai(
        self,
        query: str,
        articles: List[Dict],
        timeline_nodes: Optional[List[Dict]],
        update_progress=None,
        curr_step=None,
        total_step=None
    ) -> Optional[str]:
        """
        使用硅基流动 AI 生成事件摘要
        
        Args:
            query: 搜索关键词
            articles: 文章列表
            timeline_nodes: 时间线节点列表
            update_progress: 进度更新函数
            curr_step: 当前步骤
            total_step: 总步骤数
            
        Returns:
            生成的摘要文本或None（如果生成失败）
        """
        # 检查是否配置了 API Key
        if not Config.SILICONFLOW_API_KEY:
            logger.warning("未配置 SILICONFLOW_API_KEY，跳过AI摘要生成")
            return None
        
        if not articles:
            logger.warning("文章列表为空，无法生成摘要")
            return None
        
        try:
            # 收集所有新闻标题和时间
            titles_with_time = []
            for article in articles[:20]:  # 限制最多20篇文章，避免prompt过长
                title = article.get('title', '')
                published_at = article.get('published_at', '')
                if title:
                    time_str = published_at if published_at else '时间未知'
                    titles_with_time.append(f"- {title} ({time_str})")
            
            # 格式化时间线信息
            timeline_text = ""
            if timeline_nodes and len(timeline_nodes) > 0:
                timeline_items = []
                for node in timeline_nodes[:10]:  # 限制最多10个时间线节点
                    timestamp = node.get('timestamp', '')
                    key_event = node.get('key_event', '')
                    summary = node.get('summary', '')
                    # 优先使用key_event，如果没有则使用summary
                    description = key_event if key_event else summary
                    if timestamp and description:
                        timeline_items.append(f"- {timestamp}: {description}")
                if timeline_items:
                    timeline_text = "\n时间线：\n" + "\n".join(timeline_items)
            
            # 构建 prompt
            titles_text = "\n".join(titles_with_time)
            prompt = f"""请根据以下新闻标题和时间线信息，生成一个关于"{query}"的事件摘要。

要求：
1. 摘要应该简洁明了，概括事件的核心内容
2. 长度控制在200-300字之间
3. 突出事件的关键信息和发展脉络
4. 使用中文回答
5. 直接输出摘要内容，不要包含"摘要："等前缀

新闻标题列表：
{titles_text}
{timeline_text}

请生成事件摘要："""
            
            # 调用硅基流动 API
            headers = {
                'Authorization': f'Bearer {Config.SILICONFLOW_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': Config.SILICONFLOW_MODEL,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            logger.info(f"正在生成事件摘要，查询词: {query}")
            
            # 更新进度
            if update_progress and curr_step is not None and total_step is not None:
                prog_of_single_step = 100. / total_step
                curr_prog = int(prog_of_single_step * (curr_step - 1))
                update_progress(
                    curr_prog + int(prog_of_single_step * 0.5),
                    100,
                    f'步骤{curr_step}/{total_step}: 正在调用AI生成事件摘要...'
                )
            
            response = requests.post(
                Config.SILICONFLOW_API_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code != 200:
                logger.error(f"API 请求失败: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                logger.error(f"API 返回内容为空")
                return None
            
            # 清理摘要内容（去除可能的格式标记）
            summary = content.strip()
            # 移除可能的"摘要："等前缀
            prefixes = ['摘要：', '摘要:', '摘要', '事件摘要：', '事件摘要:', '事件摘要']
            for prefix in prefixes:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            
            logger.info(f"事件摘要生成成功，长度: {len(summary)} 字符")
            return summary
            
        except requests.exceptions.Timeout:
            logger.error(f"生成事件摘要超时")
            return None
        except Exception as e:
            logger.error(f"生成事件摘要失败: {str(e)}")
            return None


# 全局服务实例
event_service = EventService()