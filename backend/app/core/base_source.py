"""数据源基类定义"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class NewsArticle:
    """新闻文章数据模型"""
    
    def __init__(
        self,
        title: str,
        url: str,
        source: str,
        published_at: Optional[datetime] = None,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        author: Optional[str] = None,
        image_url: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        self.title = title
        self.url = url
        self.source = source
        self.published_at = published_at or datetime.now()
        self.summary = summary or ""
        self.content = content or ""
        self.author = author or ""
        self.image_url = image_url or ""
        self.tags = tags or []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'summary': self.summary,
            'content': self.content,
            'author': self.author,
            'image_url': self.image_url,
            'tags': self.tags
        }


class BaseNewsSource(ABC):
    """新闻数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[NewsArticle]:
        """
        搜索新闻
        
        Args:
            query: 搜索关键词
            **kwargs: 其他参数（如日期范围、语言等）
            
        Returns:
            新闻文章列表
        """
        pass
    
    @abstractmethod
    def get_latest(self, limit: int = 10) -> List[NewsArticle]:
        """
        获取最新新闻
        
        Args:
            limit: 返回数量限制
            
        Returns:
            新闻文章列表
        """
        pass
    
    def validate_article(self, article: NewsArticle) -> bool:
        """
        验证文章数据是否有效
        
        Args:
            article: 新闻文章对象
            
        Returns:
            是否有效
        """
        return bool(article.title and article.url and article.source)

