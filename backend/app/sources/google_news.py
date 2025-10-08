"""Google News数据源实现"""
import requests
import feedparser
from typing import List, Optional
from datetime import datetime
from dateutil import parser as date_parser
import logging

from app.core.base_source import BaseNewsSource, NewsArticle

logger = logging.getLogger(__name__)


class GoogleNewsSource(BaseNewsSource):
    """Google News RSS数据源"""
    
    def __init__(self):
        super().__init__("Google News")
        self.base_url = "https://news.google.com/rss"
        self.search_url = f"{self.base_url}/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search(self, query: str, **kwargs) -> List[NewsArticle]:
        """
        搜索Google News
        
        Args:
            query: 搜索关键词
            **kwargs: 
                - language: 语言代码，如'zh-CN'
                - region: 地区代码，如'CN'
                - limit: 返回数量限制
                
        Returns:
            新闻文章列表
        """
        language = kwargs.get('language', 'zh-CN')
        region = kwargs.get('region', 'CN')
        limit = kwargs.get('limit', 20)
        
        try:
            # 构建RSS URL
            params = {
                'q': query,
                'hl': language,
                'gl': region,
                'ceid': f'{region}:{language}'
            }
            
            # 发起请求
            response = requests.get(
                self.search_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            # 解析RSS Feed
            feed = feedparser.parse(response.content)
            articles = []
            
            for entry in feed.entries[:limit]:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)
            
            logger.info(f"从Google News获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"Google News搜索失败: {str(e)}")
            return []
    
    def get_latest(self, limit: int = 10) -> List[NewsArticle]:
        """
        获取Google News最新新闻
        
        Args:
            limit: 返回数量限制
            
        Returns:
            新闻文章列表
        """
        try:
            # 获取热门新闻
            url = f"{self.base_url}?hl=zh-CN&gl=CN&ceid=CN:zh-CN"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            articles = []
            
            for entry in feed.entries[:limit]:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"获取Google News最新新闻失败: {str(e)}")
            return []
    
    def _parse_entry(self, entry) -> Optional[NewsArticle]:
        """
        解析RSS条目
        
        Args:
            entry: feedparser的条目对象
            
        Returns:
            NewsArticle对象或None
        """
        try:
            # 提取标题
            title = entry.get('title', '')
            
            # 提取URL
            url = entry.get('link', '')
            
            # 提取摘要
            summary = entry.get('summary', '')
            # 移除HTML标签
            if summary:
                summary = self._clean_html(summary)
            
            # 提取发布时间
            published_at = None
            if 'published' in entry:
                try:
                    published_at = date_parser.parse(entry.published)
                except:
                    pass
            
            # 提取来源
            source = entry.get('source', {}).get('title', 'Google News')
            
            # 创建文章对象
            article = NewsArticle(
                title=title,
                url=url,
                source=source,
                published_at=published_at,
                summary=summary
            )
            
            return article
            
        except Exception as e:
            logger.error(f"解析RSS条目失败: {str(e)}")
            return None
    
    def _clean_html(self, text: str) -> str:
        """
        清理HTML标签
        
        Args:
            text: 包含HTML的文本
            
        Returns:
            纯文本
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, 'lxml')
        return soup.get_text(strip=True)

