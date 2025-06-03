import os
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from io import BytesIO
import requests
from PIL import Image as PILImage
import tempfile
import re

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self):
        self.setup_fonts()
        self.styles = self.setup_styles()
    
    def setup_fonts(self):
        """设置中文字体"""
        try:
            # 尝试注册系统中文字体，如果失败则使用默认字体
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                'C:/Windows/Fonts/simsun.ttc',  # Windows
                'C:/Windows/Fonts/msyh.ttc',  # Windows Microsoft YaHei
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Chinese', font_path))
                        logger.info(f"成功注册中文字体: {font_path}")
                        return
                    except:
                        continue
            
            logger.warning("未找到中文字体，将使用默认字体")
            
        except Exception as e:
            logger.error(f"设置字体失败: {str(e)}")
    
    def setup_styles(self):
        """设置文档样式"""
        styles = getSampleStyleSheet()
        
        # 检查是否已注册中文字体
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        has_chinese_font = 'Chinese' in registered_fonts
        
        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Chinese' if has_chinese_font else 'Helvetica-Bold'
        )
        
        # 正文样式
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Chinese' if has_chinese_font else 'Helvetica'
        )
        
        # 日期样式
        date_style = ParagraphStyle(
            'CustomDate',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Chinese' if has_chinese_font else 'Helvetica'
        )
        
        return {
            'title': title_style,
            'content': content_style,
            'date': date_style
        }
    
    def download_and_process_image(self, img_url, max_width=400):
        """下载并处理图片"""
        try:
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()
            
            # 使用Pillow处理图片
            img = PILImage.open(BytesIO(response.content))
            
            # 转换为RGB格式（如果是RGBA或其他格式）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整图片大小
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                img = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
            
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_file.name, 'JPEG', quality=85)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"处理图片失败 {img_url}: {str(e)}")
            return None
    
    def clean_html_content(self, content):
        """清理HTML内容，移除不支持的标签"""
        if not content:
            return content
        
        # 移除HTML标签但保留内容
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理特殊字符
        content = content.replace('\u00a0', ' ')  # 替换不间断空格
        content = content.replace('\u200b', '')   # 移除零宽空格
        
        # 转义XML特殊字符
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        
        return content
    
    def generate_pdf(self, articles, output_path, progress_callback=None):
        """生成PDF文件"""
        try:
            logger.info(f"开始生成PDF: {output_path}")
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            story = []
            total_articles = len(articles)
            
            # 添加封面
            cover_title = Paragraph("博客文章合集", self.styles['title'])
            story.append(cover_title)
            story.append(Spacer(1, 0.5*inch))
            
            for i, article in enumerate(articles):
                if progress_callback:
                    progress_callback(i + 1, total_articles, f"正在处理文章: {article['title']}")
                
                # 文章标题
                title = Paragraph(f"<b>{article['title']}</b>", self.styles['title'])
                story.append(title)
                
                # 发布日期
                if article.get('published_date'):
                    date_str = article['published_date'].strftime('%Y年%m月%d日')
                    date_para = Paragraph(f"发布日期: {date_str}", self.styles['date'])
                    story.append(date_para)
                
                # URL
                url_para = Paragraph(f"原文链接: {article['url']}", self.styles['date'])
                story.append(url_para)
                story.append(Spacer(1, 0.2*inch))
                
                # 文章内容
                content = article.get('content', '')
                if content:
                    # 清理HTML内容
                    content = self.clean_html_content(content)
                    # 将内容按段落分割
                    paragraphs = content.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            para_obj = Paragraph(para.strip(), self.styles['content'])
                            story.append(para_obj)
                            story.append(Spacer(1, 6))
                
                # 处理图片
                images = article.get('images', [])
                for img_info in images[:3]:  # 限制每篇文章最多3张图片
                    img_path = self.download_and_process_image(img_info['url'])
                    if img_path:
                        try:
                            img = Image(img_path, width=4*inch, height=3*inch)
                            story.append(img)
                            story.append(Spacer(1, 0.1*inch))
                            
                            # 图片说明
                            caption = Paragraph(f"<i>{img_info.get('alt', '图片')}</i>", self.styles['date'])
                            story.append(caption)
                            story.append(Spacer(1, 0.2*inch))
                            
                            # 清理临时文件
                            os.unlink(img_path)
                        except Exception as e:
                            logger.error(f"添加图片失败: {str(e)}")
                
                # 文章分隔
                story.append(Spacer(1, 0.5*inch))
                if i < total_articles - 1:  # 不是最后一篇文章
                    story.append(Paragraph("<br/>", self.styles['content']))
                    story.append(Spacer(1, 0.3*inch))
            
            # 生成PDF
            doc.build(story)
            logger.info(f"PDF生成完成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成PDF失败: {str(e)}")
            raise

class TXTGenerator:
    def __init__(self):
        pass
    
    def generate_txt(self, articles, output_path, progress_callback=None):
        """生成TXT文件"""
        try:
            logger.info(f"开始生成TXT: {output_path}")
            
            total_articles = len(articles)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("博客文章合集\n")
                f.write("=" * 50 + "\n\n")
                
                for i, article in enumerate(articles):
                    if progress_callback:
                        progress_callback(i + 1, total_articles, f"正在处理文章: {article['title']}")
                    
                    # 文章标题
                    f.write(f"标题: {article['title']}\n")
                    
                    # 发布日期
                    if article.get('published_date'):
                        date_str = article['published_date'].strftime('%Y年%m月%d日')
                        f.write(f"发布日期: {date_str}\n")
                    
                    # URL
                    f.write(f"原文链接: {article['url']}\n")
                    f.write("-" * 30 + "\n\n")
                    
                    # 文章内容
                    content = article.get('content', '')
                    if content:
                        f.write(content)
                        f.write("\n\n")
                    
                    # 图片信息
                    images = article.get('images', [])
                    if images:
                        f.write("文章图片:\n")
                        for img_info in images:
                            f.write(f"- {img_info.get('alt', '图片')}: {img_info['url']}\n")
                        f.write("\n")
                    
                    # 文章分隔
                    f.write("=" * 50 + "\n\n")
            
            logger.info(f"TXT生成完成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成TXT失败: {str(e)}")
            raise
