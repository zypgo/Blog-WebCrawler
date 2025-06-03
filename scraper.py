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

class BlogScraper:
    def __init__(self, base_url="https://baoyu.io/blog"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_article_links(self):
        """获取博客首页所有文章链接"""
        try:
            logger.info(f"正在获取文章链接: {self.base_url}")
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # 查找所有文章链接 - 根据新的HTML结构调整选择器
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href', '')
                # 过滤出文章链接 - 新格式是 blog/xxx 而不是 /blog/xxx
                if href.startswith('blog/') and href != 'blog' and href != 'blog/':
                    full_url = urljoin(self.base_url, href)
                    
                    # 查找父级article元素来获取标题
                    article_element = link.find_parent('article')
                    if article_element:
                        title_element = article_element.find('h2')
                        if title_element:
                            title = title_element.get_text(strip=True)
                            if title:
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
    
    def extract_article_date(self, content):
        """从文章内容中提取日期"""
        try:
            # 尝试多种日期格式
            date_patterns = [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{4}-\d{1,2}-\d{1,2})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, content)
                if match:
                    date_str = match.group(1)
                    try:
                        # 尝试解析日期
                        if '年' in date_str:
                            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                        return datetime.strptime(date_str, '%Y-%m-%d').date()
                    except:
                        continue
            
            return None
        except Exception as e:
            logger.error(f"提取日期失败: {str(e)}")
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
            published_date = self.extract_article_date(text_content)
            
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
                    if start_date and article_data['published_date']:
                        if article_data['published_date'] < start_date:
                            continue
                    
                    if end_date and article_data['published_date']:
                        if article_data['published_date'] > end_date:
                            continue
                    
                    articles.append(article_data)
                
                # 添加延迟避免过于频繁的请求
                time.sleep(1)
            
            logger.info(f"成功抓取 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"抓取所有文章失败: {str(e)}")
            raise
