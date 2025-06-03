import os
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
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
            # 注册Unicode CID字体，支持中文
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            logger.info("成功注册中文字体: STSong-Light")
            return
        except Exception as e:
            logger.warning(f"注册STSong-Light失败: {str(e)}")
        
        try:
            # 备选方案：使用HeiseiMin-W3
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            logger.info("成功注册中文字体: HeiseiMin-W3")
            return
        except Exception as e:
            logger.warning(f"注册HeiseiMin-W3失败: {str(e)}")
        
        try:
            # 最后备选：注册DejaVu字体作为Chinese
            pdfmetrics.registerFont(TTFont('Chinese', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            logger.info("使用DejaVu字体作为备选")
        except Exception as e:
            logger.error(f"设置字体失败: {str(e)}")
    
    def setup_styles(self):
        """设置文档样式"""
        styles = getSampleStyleSheet()
        
        # 检查可用的中文字体
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        chinese_font = None
        
        # 优先使用CID字体
        if 'STSong-Light' in registered_fonts:
            chinese_font = 'STSong-Light'
        elif 'HeiseiMin-W3' in registered_fonts:
            chinese_font = 'HeiseiMin-W3'
        elif 'Chinese' in registered_fonts:
            chinese_font = 'Chinese'
        else:
            chinese_font = 'Helvetica'
        
        # 为英文内容使用Helvetica字体
        english_font = 'Helvetica'
        
        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=12,
            alignment=TA_CENTER,
            fontName=chinese_font,
            leading=20,  # 行间距
            leftIndent=0,
            rightIndent=0
        )
        
        # 正文样式 - 统一使用中文字体，确保字符兼容性
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            spaceBefore=6,
            alignment=TA_LEFT,
            fontName=chinese_font,  # 统一使用中文字体以避免字符显示问题
            leading=16,  # 行间距
            leftIndent=12,
            rightIndent=12,
            firstLineIndent=24,  # 首行缩进
            wordWrap='LTR'
        )
        
        # 中文内容样式（与content_style保持一致）
        chinese_content_style = ParagraphStyle(
            'ChineseContent',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            spaceBefore=6,
            alignment=TA_LEFT,
            fontName=chinese_font,
            leading=16,
            leftIndent=12,
            rightIndent=12,
            firstLineIndent=24,
            wordWrap='LTR'
        )
        
        # 日期样式
        date_style = ParagraphStyle(
            'CustomDate',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=8,
            spaceBefore=4,
            alignment=TA_LEFT,
            fontName=chinese_font,  # 统一使用中文字体
            leading=12,
            leftIndent=12,
            textColor='gray'
        )
        
        return {
            'title': title_style,
            'content': content_style,
            'chinese_content': chinese_content_style,
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
        content = content.replace('\u2028', '\n')  # 行分隔符
        content = content.replace('\u2029', '\n\n')  # 段落分隔符
        
        # 更严格的字符过滤 - 只保留基本字符
        # 保留基本拉丁字母、数字、中文字符、基本标点符号
        allowed_chars = []
        for char in content:
            code = ord(char)
            # 基本拉丁字母和数字 (0-127)
            # 中文字符 (19968-40959)
            # 基本标点符号
            if (code <= 127 or  # ASCII字符
                (19968 <= code <= 40959) or  # 中文字符
                char in '，。！？；：""''（）【】《》、—…\n\r\t '):
                allowed_chars.append(char)
            else:
                # 将不支持的字符替换为空格或删除
                if char.isspace():
                    allowed_chars.append(' ')
                # 其他字符直接删除
        
        content = ''.join(allowed_chars)
        
        # 修复英文单词连接问题
        # 在小写字母和大写字母之间添加空格
        content = re.sub(r'([a-z])([A-Z])', r'\1 \2', content)
        # 在字母和数字之间添加空格
        content = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', content)
        content = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', content)
        # 在标点符号后添加空格（如果后面直接跟字母）
        content = re.sub(r'([.!?])([A-Z])', r'\1 \2', content)
        content = re.sub(r'([,;:])([a-zA-Z])', r'\1 \2', content)
        
        # 规范化空白字符
        content = re.sub(r'\s+', ' ', content)  # 多个空格合并为一个
        content = re.sub(r'\n\s*\n', '\n\n', content)  # 多个换行合并
        
        # 转义XML特殊字符
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        
        return content.strip()
    
    def generate_pdf(self, articles, output_path, progress_callback=None):
        """生成PDF文件"""
        temp_image_paths = []  # 在函数级别管理临时文件
        
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
                    # 将内容按段落分割，每段不超过一定长度
                    paragraphs = content.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            # 限制段落长度，避免单行过长
                            para_text = para.strip()
                            if len(para_text) > 500:
                                # 按句号分割长段落
                                sentences = para_text.split('。')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para + sentence) > 300:
                                        if current_para:
                                            # 检测当前段落的语言类型
                                            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', current_para))
                                            total_chars = len(current_para)
                                            
                                            # 统一使用content样式
                                            style = self.styles['content']
                                            
                                            para_obj = Paragraph(current_para + "。", style)
                                            story.append(para_obj)
                                            story.append(Spacer(1, 4))
                                        current_para = sentence
                                    else:
                                        current_para += sentence + "。" if sentence else ""
                                if current_para:
                                    # 统一使用content样式
                                    style = self.styles['content']
                                    
                                    para_obj = Paragraph(current_para, style)
                                    story.append(para_obj)
                                    story.append(Spacer(1, 4))
                            else:
                                # 检测文本是否主要是中文或英文
                                chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', para_text))
                                total_chars = len(para_text)
                                
                                # 统一使用content样式，避免字体不一致问题
                                style = self.styles['content']
                                
                                para_obj = Paragraph(para_text, style)
                                story.append(para_obj)
                                story.append(Spacer(1, 4))
                
                # 处理图片
                images = article.get('images', [])
                
                for img_info in images[:3]:  # 限制每篇文章最多3张图片
                    img_path = self.download_and_process_image(img_info['url'])
                    if img_path and os.path.exists(img_path):
                        try:
                            # 检查文件大小，避免添加太大的图片
                            img_size = os.path.getsize(img_path)
                            if img_size > 5 * 1024 * 1024:  # 5MB限制
                                logger.warning(f"图片过大，跳过: {img_info['url']}")
                                os.unlink(img_path)
                                continue
                            
                            img = Image(img_path, width=4*inch, height=3*inch)
                            story.append(img)
                            story.append(Spacer(1, 0.1*inch))
                            
                            # 图片说明
                            caption = Paragraph(f"<i>{img_info.get('alt', '图片')}</i>", self.styles['date'])
                            story.append(caption)
                            story.append(Spacer(1, 0.2*inch))
                            
                            # 添加到临时文件列表，稍后清理
                            temp_image_paths.append(img_path)
                            
                        except Exception as e:
                            logger.error(f"添加图片失败: {str(e)}")
                            if os.path.exists(img_path):
                                os.unlink(img_path)
                
                # 文章分隔
                story.append(Spacer(1, 0.5*inch))
                if i < total_articles - 1:  # 不是最后一篇文章
                    story.append(Paragraph("<br/>", self.styles['content']))
                    story.append(Spacer(1, 0.3*inch))
            
            # 生成PDF
            doc.build(story)
            logger.info(f"PDF生成完成: {output_path}")
            
            # 清理所有临时图片文件
            for temp_path in temp_image_paths:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {temp_path}, {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"生成PDF失败: {str(e)}")
            # 确保清理临时文件
            for temp_path in temp_image_paths:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception:
                    pass
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
