"""数据源聚合器"""
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging

from app.core.base_source import BaseNewsSource, NewsArticle
from .text_matcher import TextMatcher

logger = logging.getLogger(__name__)


class NewsAggregator:
    """新闻聚合器 - 整合多个数据源"""
    
    def __init__(self):
        self.sources: List[BaseNewsSource] = []
        self.matcher = TextMatcher()
        self.similarity_threshold = 0.3  # 关联度阈值（可根据需求调整）

    def register_source(self, source: BaseNewsSource):
        """
        注册数据源
        
        Args:
            source: 数据源实例
        """
        self.sources.append(source)
        logger.info(f"已注册数据源: {source.name}")
    
    def search_all(
        self,
        query: str,
        max_workers: int = 3,
        **kwargs
    ) -> Dict[str, List[NewsArticle]]:
        """
        在所有数据源中搜索
        
        Args:
            query: 搜索关键词
            max_workers: 最大并发线程数
            **kwargs: 传递给各数据源的参数
            
        Returns:
            字典，键为数据源名称，值为文章列表
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有搜索任务
            future_to_source = {
                executor.submit(self._safe_search, source, query, **kwargs): source
                for source in self.sources
            }
            
            # 收集结果
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    articles = future.result()
                    results[source.name] = articles
                    logger.info(f"从 {source.name} 获取到 {len(articles)} 篇文章")
                except Exception as e:
                    logger.error(f"从 {source.name} 搜索时出错: {str(e)}")
                    results[source.name] = []
        
        return results
    
    def _safe_search(
        self,
        source: BaseNewsSource,
        query: str,
        **kwargs
    ) -> List[NewsArticle]:
        """
        安全的搜索封装
        
        Args:
            source: 数据源
            query: 搜索关键词
            **kwargs: 其他参数
            
        Returns:
            文章列表
        """
        try:
            articles = source.search(query, **kwargs)
            # 过滤无效文章
            return [a for a in articles if source.validate_article(a)]
        except Exception as e:
            logger.error(f"{source.name} 搜索失败: {str(e)}")
            return []
    
    def aggregate_results(
        self,
        query: str,
        results: Dict[str, List[NewsArticle]]
    ) -> List[Dict]:
        """
        聚合结果，按时间排序并去重
        
        Args:
            results: 各数据源的搜索结果
            
        Returns:
            聚合后的文章列表（字典格式）
        """
        all_articles = []
        seen_urls = set()
        
        # 合并所有文章
        for source_name, articles in results.items():
            for article in articles:
                # 简单去重（基于URL）
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    all_articles.append(article)
        
        # 按发布时间排序
        all_articles.sort(
            key=lambda x: x.published_at if x.published_at else datetime.min,
            reverse=True
        )

        # 计算标题相似度
        all_titles =  []
        for article in all_articles:
            all_titles.append(article.title)

        similarities = self.matcher.calculate_similarity(query, all_titles)

        # 过滤标题相似度低的文章
        filter_articles = []
        remain_articles = []
        for news, sim in zip(all_articles, similarities):
            if sim >= self.similarity_threshold:
                news.filter = False
                filter_articles.append(news)
            else:
                news.filter = True
                remain_articles.append(news)

        combined_articles = filter_articles + remain_articles
        return [article.to_dict() for article in combined_articles]
    
    def get_source_count(self) -> int:
        """获取已注册的数据源数量"""
        return len(self.sources)


# 全局聚合器实例
aggregator = NewsAggregator()

