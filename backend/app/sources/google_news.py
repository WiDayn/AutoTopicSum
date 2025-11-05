"""Google News数据源实现"""
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime
import re
import logging
import time
from urllib.parse import urljoin, quote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from app.core.base_source import BaseNewsSource, NewsArticle
from config import Config

logger = logging.getLogger(__name__)


class GoogleNewsSource(BaseNewsSource):
    """Google News 网页搜索数据源"""
    
    # 固定返回数量
    DEFAULT_LIMIT = 100
    
    def __init__(self):
        super().__init__("Google News")
        self.base_url = "https://news.google.com"
        self.search_url = f"{self.base_url}/search"
        self.driver = None
    
    def _create_driver(self):
        """创建并配置 Chrome WebDriver"""
        try:
            print("  → 开始配置 Chrome 选项...")
            logger.info("开始配置 Chrome 选项...")
            chrome_options = Options()
            # chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 配置代理（如果启用）
            if Config.WEBDRIVER_PROXY_ENABLED and Config.WEBDRIVER_PROXY:
                proxy_url = Config.WEBDRIVER_PROXY
                chrome_options.add_argument(f'--proxy-server={proxy_url}')
                
                proxy_type = "HTTP/HTTPS"
                if proxy_url.startswith('socks5://'):
                    proxy_type = "SOCKS5"
                elif proxy_url.startswith('socks4://'):
                    proxy_type = "SOCKS4"
                
                print(f"  → 使用 {proxy_type} 代理: {proxy_url}")
                logger.info(f"WebDriver 使用 {proxy_type} 代理: {proxy_url}")
            else:
                print("  → 未配置代理")
                logger.info("WebDriver 未配置代理")
            
            # 禁用图片和CSS加载以提高速度
            prefs = {
                'profile.managed_default_content_settings.images': 2,
                'profile.managed_default_content_settings.stylesheets': 2
            }
            chrome_options.add_experimental_option('prefs', prefs)
            
            print("  → 正在下载/安装 ChromeDriver...")
            logger.info("正在下载/安装 ChromeDriver...")
            # 使用 webdriver-manager 自动管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            print("  → 正在启动 Chrome 浏览器...")
            logger.info("正在启动 Chrome 浏览器...")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            print("  ✅ Chrome WebDriver 创建成功")
            logger.info("Chrome WebDriver 创建成功")
            return driver
            
        except Exception as e:
            import traceback
            error_msg = f"创建 WebDriver 失败: {str(e)}"
            print(f"  ❌ {error_msg}")
            print(f"  错误详情:\n{traceback.format_exc()}")
            logger.error(error_msg)
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return None
    
    def _close_driver(self):
        """关闭 WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver 已关闭")
            except Exception as e:
                logger.error(f"关闭 WebDriver 失败: {str(e)}")
    
    def search(self, query: str, **kwargs) -> List[NewsArticle]:
        """
        搜索Google News（使用 Selenium）
        
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
        
        driver = None
        try:
            print(f"\n{'='*60}")
            print(f"开始使用 Selenium WebDriver 搜索 Google News: {query}")
            print(f"{'='*60}\n")
            logger.info("开始使用 Selenium WebDriver 搜索 Google News")
            
            # 创建 WebDriver
            print("正在创建 Chrome WebDriver...")
            logger.info("正在创建 Chrome WebDriver...")
            driver = self._create_driver()
            if not driver:
                print("❌ 无法创建 WebDriver，使用备用方法 (requests)")
                logger.warning("无法创建 WebDriver，使用备用方法 (requests)")
                return self._fallback_search(query, language, region)
            
            print("✅ WebDriver 创建成功，开始搜索")
            logger.info("WebDriver 创建成功，开始搜索")
            
            # 构建搜索URL
            url = f"{self.search_url}?q={quote(query)}&hl={language}&gl={region}"
            
            logger.info(f"正在从 Google News 搜索: {query}")
            logger.info(f"URL: {url}")
            
            # 访问页面
            driver.get(url)
            
            # 等待页面加载
            time.sleep(3)
            
            # 滚动加载更多内容
            articles = []
            last_article_count = 0
            scroll_attempts = 0
            max_scroll_attempts = 10  # 最多滚动10次
            
            while len(articles) < limit and scroll_attempts < max_scroll_attempts:
                # 获取当前页面HTML
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'lxml')
                
                # 查找所有文章元素
                article_elements = soup.find_all('article')
                
                logger.info(f"找到 {len(article_elements)} 个文章元素 (滚动第 {scroll_attempts + 1} 次)")
                
                # 解析新找到的文章
                current_articles = []
                for article_elem in article_elements:
                    article = self._parse_article_element(article_elem)
                    if article and article not in articles:
                        current_articles.append(article)
                
                articles.extend(current_articles)
                
                # 去重
                seen = set()
                unique_articles = []
                for article in articles:
                    key = (article.title, article.url)
                    if key not in seen:
                        seen.add(key)
                        unique_articles.append(article)
                articles = unique_articles
                
                # 检查是否有新文章
                if len(articles) == last_article_count:
                    logger.info("没有新文章，停止滚动")
                    break
                
                last_article_count = len(articles)
                
                # 如果已经达到目标数量，停止滚动
                if len(articles) >= limit:
                    logger.info(f"已获取足够的文章: {len(articles)}")
                    break
                
                # 滚动到页面底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待内容加载
                
                scroll_attempts += 1
            
            logger.info(f"从Google News获取到 {len(articles)} 篇文章")
            
            # 关闭 WebDriver
            driver.quit()
            
            return articles[:limit]
            
        except Exception as e:
            import traceback
            logger.error(f"Google News搜索失败: {str(e)}")
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            
            # 确保关闭 WebDriver
            if driver:
                try:
                    logger.info("正在关闭 WebDriver...")
                    driver.quit()
                    logger.info("WebDriver 已关闭")
                except Exception as close_error:
                    logger.error(f"关闭 WebDriver 时出错: {str(close_error)}")
            
            # 尝试使用备用方法
            logger.info("尝试使用备用搜索方法...")
            try:
                return self._fallback_search(query, language, region)
            except Exception as fallback_error:
                logger.error(f"备用搜索方法也失败: {str(fallback_error)}")
                return []
    
    def _fallback_search(self, query: str, language: str, region: str) -> List[NewsArticle]:
        """
        备用搜索方法（使用 requests，无需 Selenium）
        
        Args:
            query: 搜索关键词
            language: 语言代码
            region: 地区代码
            
        Returns:
            新闻文章列表
        """
        try:
            print(f"\n{'='*60}")
            print("⚠️  使用备用方法搜索（requests，不使用 Selenium）")
            print(f"{'='*60}\n")
            logger.warning("=" * 50)
            logger.warning("使用备用方法搜索（requests，不使用 Selenium）")
            logger.warning("=" * 50)
            
            url = f"{self.search_url}?q={quote(query)}&hl={language}&gl={region}"
            logger.info(f"请求 URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            logger.info("发送 HTTP 请求...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"HTTP 响应状态码: {response.status_code}")
            
            logger.info("解析 HTML...")
            soup = BeautifulSoup(response.content, 'lxml')
            article_elements = soup.find_all('article')
            logger.info(f"找到 {len(article_elements)} 个 article 元素")
            
            articles = []
            for article_elem in article_elements[:50]:  # 限制50篇
                article = self._parse_article_element(article_elem)
                if article:
                    articles.append(article)
            
            logger.warning(f"备用方法获取到 {len(articles)} 篇文章")
            logger.warning("=" * 50)
            return articles
            
        except Exception as e:
            import traceback
            logger.error(f"备用搜索也失败: {str(e)}")
            logger.error(f"错误详情:\n{traceback.format_exc()}")
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
            # 使用备用方法获取最新新闻
            url = f"{self.base_url}?hl=zh-CN&gl=CN"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
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

