"""Google News数据源实现"""
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime
import re
import logging
from urllib.parse import urljoin, quote

from app.core.base_source import BaseNewsSource, NewsArticle

logger = logging.getLogger(__name__)


class GoogleNewsSource(BaseNewsSource):
    """Google News 网页搜索数据源"""
    
    # 固定返回数量
    DEFAULT_LIMIT = 100
    
    def __init__(self):
        super().__init__("Google News")
        self.base_url = "https://news.google.com"
        self.search_url = f"{self.base_url}/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def search(self, query: str, **kwargs) -> List[NewsArticle]:
        """
        搜索Google News（直接解析网页）
        
        Args:
            query: 搜索关键词
            **kwargs: 
                - language: 语言代码，如'zh-CN'
                - region: 地区代码，如'CN'
                
        Returns:
            新闻文章列表
        """
        language = kwargs.get('language', 'zh-CN')
        region = kwargs.get('region', 'CN')
        limit = self.DEFAULT_LIMIT
        
        try:
            # 构建搜索URL
            params = {
                'q': query,
                'hl': language,
                'gl': region
            }
            
            logger.info(f"正在从 Google News 搜索: {query}")
            
            # 发起请求
            response = requests.get(
                self.search_url,
                params=params,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'lxml')
            articles = []
            
            # 查找所有新闻文章元素
            # Google News 使用特定的 HTML 结构
            article_elements = soup.find_all('article')
            
            logger.info(f"找到 {len(article_elements)} 个文章元素")
            
            for article_elem in article_elements[:limit]:
                article = self._parse_article_element(article_elem)
                if article:
                    articles.append(article)
            
            logger.info(f"从Google News获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"Google News搜索失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
            url = f"{self.base_url}?hl=zh-CN&gl=CN"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            articles = []
            
            article_elements = soup.find_all('article')[:limit]
            
            for article_elem in article_elements:
                article = self._parse_article_element(article_elem)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"获取Google News最新新闻失败: {str(e)}")
            return []
    
    def _parse_article_element(self, article_elem) -> Optional[NewsArticle]:
        """
        解析 Google News 文章元素
        
        Args:
            article_elem: BeautifulSoup article 元素
            
        Returns:
            NewsArticle对象或None
        """
        try:
            # 查找标题链接
            title_link = article_elem.find('a', class_=re.compile('gPFEn|JtKRv'))
            if not title_link:
                # 尝试其他可能的选择器
                title_link = article_elem.find('a')
            
            if not title_link:
                return None
            
            # 提取标题
            title = title_link.get_text(strip=True)
            if not title:
                return None
            
            # 提取URL
            url = title_link.get('href', '')
            if url.startswith('./'):
                url = urljoin(self.base_url, url)
            elif not url.startswith('http'):
                url = urljoin(self.base_url, url)
            
            # 提取来源 - 多种方式尝试
            source = self._extract_source(article_elem)
            
            if not source:
                source = 'Google News'
            
            # 提取时间信息
            time_elem = article_elem.find('time')
            published_at = None
            if time_elem:
                datetime_str = time_elem.get('datetime')
                if datetime_str:
                    try:
                        published_at = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except:
                        pass
                
                # 如果没有datetime属性，尝试解析文本
                if not published_at:
                    time_text = time_elem.get_text(strip=True)
                    published_at = self._parse_relative_time(time_text)
            
            # 提取摘要（如果有）
            summary = ''
            # Google News 的摘要通常在特定的 div 中
            summary_elem = article_elem.find('div', class_=re.compile('.*snippet.*|St8fe'))
            if summary_elem:
                summary = summary_elem.get_text(strip=True)
            
            article = NewsArticle(
                title=title,
                url=url,
                source=source or 'Google News',
                published_at=published_at,
                summary=summary
            )
            
            return article
            
        except Exception as e:
            logger.error(f"解析文章元素失败: {str(e)}")
            return None
    
    def _parse_relative_time(self, time_text: str) -> Optional[datetime]:
        """
        解析相对时间（如"2小时前"）
        
        Args:
            time_text: 时间文本
            
        Returns:
            datetime对象或None
        """
        try:
            from datetime import timedelta
            now = datetime.now()
            
            # 匹配不同的时间格式
            if '分钟' in time_text or 'minute' in time_text.lower():
                minutes = re.search(r'(\d+)', time_text)
                if minutes:
                    return now - timedelta(minutes=int(minutes.group(1)))
            
            elif '小时' in time_text or 'hour' in time_text.lower():
                hours = re.search(r'(\d+)', time_text)
                if hours:
                    return now - timedelta(hours=int(hours.group(1)))
            
            elif '天' in time_text or 'day' in time_text.lower():
                days = re.search(r'(\d+)', time_text)
                if days:
                    return now - timedelta(days=int(days.group(1)))
            
            elif '周' in time_text or 'week' in time_text.lower():
                weeks = re.search(r'(\d+)', time_text)
                if weeks:
                    return now - timedelta(weeks=int(weeks.group(1)))
            
            return now
            
        except Exception as e:
            logger.error(f"解析相对时间失败: {str(e)}")
            return None
    
    def _extract_source(self, article_elem) -> Optional[str]:
        """
        提取文章来源（媒体名称）
        
        Args:
            article_elem: BeautifulSoup article 元素
            
        Returns:
            来源名称或None
        """
        try:
            # 查找 class="vr1PYe" 的元素（Google News 中表示媒体来源的类名）
            source_elem = article_elem.find('div',class_='vr1PYe')
            
            if source_elem:
                source = source_elem.get_text(strip=True)
                
                # 清理来源名称
                if source:
                    # 移除多余的空白字符
                    source = ' '.join(source.split())
                    # 移除常见的无用后缀
                    source = re.sub(r'\s*-\s*.*$', '', source)  # 移除 "来源 - xxx"
                    source = re.sub(r'\s*\|.*$', '', source)    # 移除 "来源 | xxx"
                    # 限制长度
                    if len(source) > 100:
                        source = source[:100]
                    
                    logger.debug(f"提取到来源: {source}")
                    return source
            return None
            
        except Exception as e:
            logger.error(f"提取来源失败: {str(e)}")
            return None

