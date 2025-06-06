import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import trafilatura
import os
import logging
from datetime import datetime
import time
import re

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_article_links(self):
        """获取网站的所有文章链接"""
        try:
            logger.info(f"正在获取文章链接: {self.base_url}")
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # 通用的文章链接查找策略
            # 1. 首先尝试常见的文章容器选择器
            article_containers = soup.select('article, .article, .post, .entry, .content-item, .blog-post')
            
            if article_containers:
                # 如果找到文章容器，从中提取链接
                for container in article_containers:
                    link = container.find('a', href=True)
                    if link:
                        href = str(link.get('href', ''))
                        if href and self._is_valid_article_link(href):
                            full_url = urljoin(self.base_url, href)
                            title = self._extract_title_from_container(container)
                            if title:
                                articles.append({
                                    'url': full_url,
                                    'title': title
                                })
            else:
                # 如果没有找到文章容器，尝试查找所有链接并过滤
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = str(link.get('href', ''))
                    if href and self._is_valid_article_link(href):
                        full_url = urljoin(self.base_url, href)
                        title = link.get_text(strip=True) or self._extract_title_from_url(href)
                        if title and len(title) > 5:  # 过滤掉太短的标题
                            articles.append({
                                'url': full_url,
                                'title': title
                            })
            
            # 去重
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            logger.info(f"找到 {len(unique_articles)} 篇文章")
            return unique_articles
            
        except Exception as e:
            logger.error(f"获取文章链接失败: {str(e)}")
            return []
    
    def _is_valid_article_link(self, href):
        """判断链接是否可能是文章链接"""
        if not href or href.startswith('#') or href.startswith('javascript:'):
            return False
        
        # 排除常见的非文章链接
        excluded_patterns = [
            '/tag/', '/category/', '/archive/', '/about', '/contact',
            '/login', '/register', '/search', '/feed', '/rss',
            '.pdf', '.doc', '.jpg', '.png', '.gif', '.zip'
        ]
        
        for pattern in excluded_patterns:
            if pattern in href.lower():
                return False
        
        return True
    
    def _extract_title_from_container(self, container):
        """从容器中提取标题"""
        # 尝试多种标题选择器
        title_selectors = ['h1', 'h2', 'h3', '.title', '.post-title', '.entry-title', '.article-title']
        
        for selector in title_selectors:
            title_element = container.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title and len(title) > 5:
                    return title
        
        return None
    
    def _extract_title_from_url(self, href):
        """从URL中提取可能的标题"""
        # 从URL路径中提取标题
        path = urlparse(href).path
        segments = [seg for seg in path.split('/') if seg]
        
        if segments:
            last_segment = segments[-1]
            # 移除文件扩展名
            if '.' in last_segment:
                last_segment = last_segment.rsplit('.', 1)[0]
            # 替换连字符和下划线为空格
            title = last_segment.replace('-', ' ').replace('_', ' ')
            return title.title()
        
        return None
    
    def extract_article_date(self, content, soup=None):
        """从文章内容中提取日期"""
        try:
            # 首先尝试从HTML结构中提取日期
            if soup:
                # 常见的日期元素选择器
                date_selectors = [
                    'time[datetime]', '.date', '.published', '.post-date', 
                    '.entry-date', '.article-date', '.publish-date',
                    'meta[property="article:published_time"]',
                    'meta[name="publishdate"]'
                ]
                
                for selector in date_selectors:
                    date_element = soup.select_one(selector)
                    if date_element:
                        # 尝试从datetime属性获取
                        datetime_attr = date_element.get('datetime') or date_element.get('content')
                        if datetime_attr:
                            try:
                                # 解析ISO格式日期
                                if 'T' in datetime_attr:
                                    return datetime.fromisoformat(datetime_attr.split('T')[0]).date()
                                else:
                                    return datetime.strptime(datetime_attr[:10], '%Y-%m-%d').date()
                            except:
                                pass
                        
                        # 尝试从文本内容获取
                        date_text = date_element.get_text(strip=True)
                        if date_text:
                            parsed_date = self._parse_date_text(date_text)
                            if parsed_date:
                                return parsed_date
            
            # 从文本内容中提取日期
            return self._parse_date_text(content)
            
        except Exception as e:
            logger.error(f"提取日期失败: {str(e)}")
            return None
    
    def _parse_date_text(self, text):
        """解析文本中的日期"""
        # 扩展的日期格式模式
        date_patterns = [
            # ISO格式
            (r'(\d{4}-\d{1,2}-\d{1,2})', '%Y-%m-%d'),
            # 中文格式
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日', None),
            # 英文格式
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})', '%b %d %Y'),
            # 美式格式
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
            # 欧式格式
            (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', '%d.%m.%Y'),
        ]
        
        for pattern, format_str in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if format_str is None:  # 中文格式特殊处理
                        if '年' in match.group(0):
                            year, month, day = match.groups()
                            return datetime(int(year), int(month), int(day)).date()
                    else:
                        if len(match.groups()) == 1:
                            return datetime.strptime(match.group(1), format_str).date()
                        else:
                            return datetime.strptime(match.group(0), format_str).date()
                except:
                    continue
        
        return None
    
    def scrape_article(self, article_url):
        """抓取单篇文章内容"""
        try:
            logger.info(f"正在抓取文章: {article_url}")
            
            # 使用trafilatura提取主要内容
            downloaded = trafilatura.fetch_url(article_url)
            if not downloaded:
                raise Exception("无法下载文章内容")
            
            # 提取文本内容
            text_content = trafilatura.extract(downloaded)
            if not text_content:
                raise Exception("无法提取文章文本")
            
            # 同时用BeautifulSoup获取更多信息
            soup = BeautifulSoup(downloaded, 'html.parser')
            
            # 提取标题
            title = None
            title_selectors = ['h1', 'title', '.article-title', '.post-title']
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title = title_element.get_text(strip=True)
                    break
            
            if not title:
                title = "无标题"
            
            # 提取发布日期
            published_date = self.extract_article_date(text_content, soup)
            
            # 查找并下载图片
            images = self.extract_images(soup, article_url)
            
            article_data = {
                'title': title,
                'url': article_url,
                'content': text_content,
                'published_date': published_date,
                'images': images
            }
            
            logger.info(f"成功抓取文章: {title}")
            return article_data
            
        except Exception as e:
            logger.error(f"抓取文章失败 {article_url}: {str(e)}")
            return None
    
    def extract_images(self, soup, base_url):
        """提取文章中的图片"""
        images = []
        try:
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src:
                    # 处理相对URL
                    img_url = urljoin(base_url, src)
                    alt_text = img.get('alt', '图片')
                    images.append({
                        'url': img_url,
                        'alt': alt_text
                    })
            
            logger.info(f"找到 {len(images)} 张图片")
            return images
            
        except Exception as e:
            logger.error(f"提取图片失败: {str(e)}")
            return []
    
    def download_image(self, img_url, save_path):
        """下载图片到本地"""
        try:
            response = self.session.get(img_url, timeout=10)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            logger.error(f"下载图片失败 {img_url}: {str(e)}")
            return False
    
    def scrape_all_articles(self, start_date=None, end_date=None, progress_callback=None):
        """抓取所有文章"""
        try:
            # 获取所有文章链接
            article_links = self.get_article_links()
            
            if not article_links:
                raise Exception("未找到任何文章链接")
            
            articles = []
            total_articles = len(article_links)
            
            for i, article_info in enumerate(article_links):
                if progress_callback:
                    progress_callback(i + 1, total_articles, f"正在抓取: {article_info['title']}")
                
                article_data = self.scrape_article(article_info['url'])
                
                if article_data:
                    # 检查日期过滤
                    published_date = article_data.get('published_date')
                    
                    # 如果设置了日期过滤但文章没有日期信息，记录日志但仍然包含该文章
                    if start_date or end_date:
                        if published_date:
                            if start_date and published_date < start_date:
                                logger.info(f"跳过文章（早于开始日期）: {article_data['title']} - {published_date}")
                                continue
                            
                            if end_date and published_date > end_date:
                                logger.info(f"跳过文章（晚于结束日期）: {article_data['title']} - {published_date}")
                                continue
                        else:
                            logger.warning(f"文章无法提取日期，将包含在结果中: {article_data['title']}")
                    
                    articles.append(article_data)
                
                # 添加延迟避免过于频繁的请求
                time.sleep(1)
            
            logger.info(f"成功抓取 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"抓取所有文章失败: {str(e)}")
            raise
