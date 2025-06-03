import os
import logging
from datetime import datetime, date
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from app import app, db
from models import ScrapeJob, Article
from scraper import WebScraper
from pdf_generator import PDFGenerator, TXTGenerator
import threading
import time

logger = logging.getLogger(__name__)

# 全局变量存储当前进度
current_progress = {
    'status': 'idle',
    'progress': 0,
    'total': 0,
    'message': '',
    'job_id': None
}

@app.route('/')
def index():
    """主页"""
    recent_jobs = ScrapeJob.query.order_by(ScrapeJob.created_at.desc()).limit(5).all()
    return render_template('index.html', recent_jobs=recent_jobs)

@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    """开始抓取任务"""
    try:
        data = request.get_json()
        
        # 解析输入数据
        target_url = data.get('target_url', '').strip()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        output_format = data.get('output_format', 'pdf')
        
        if not target_url:
            return jsonify({
                'success': False,
                'message': '请输入目标网站URL'
            }), 400
        
        # 确保URL格式正确
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # 创建抓取任务
        job = ScrapeJob(
            target_url=target_url,
            start_date=start_date,
            end_date=end_date,
            output_format=output_format,
            status='pending'
        )
        
        db.session.add(job)
        db.session.commit()
        
        # 在后台线程中执行抓取
        thread = threading.Thread(target=run_scrape_job, args=(job.id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'message': '抓取任务已开始'
        })
        
    except Exception as e:
        logger.error(f"启动抓取任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'启动任务失败: {str(e)}'
        }), 500

@app.route('/progress')
def get_progress():
    """获取当前进度"""
    return jsonify(current_progress)

@app.route('/download/<int:job_id>')
def download_file(job_id):
    """下载生成的文件"""
    try:
        job = ScrapeJob.query.get_or_404(job_id)
        
        if job.status != 'completed' or not job.file_path:
            return jsonify({'error': '文件未准备好'}), 404
        
        if not os.path.exists(job.file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        filename = f"blog_articles_{job.created_at.strftime('%Y%m%d')}.{job.output_format}"
        
        return send_file(
            job.file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return jsonify({'error': '下载失败'}), 500

@app.route('/jobs')
def list_jobs():
    """获取任务列表"""
    jobs = ScrapeJob.query.order_by(ScrapeJob.created_at.desc()).limit(20).all()
    jobs_data = []
    
    for job in jobs:
        jobs_data.append({
            'id': job.id,
            'target_url': job.target_url,
            'start_date': job.start_date.strftime('%Y-%m-%d') if job.start_date else None,
            'end_date': job.end_date.strftime('%Y-%m-%d') if job.end_date else None,
            'output_format': job.output_format,
            'status': job.status,
            'articles_count': job.articles_count,
            'created_at': job.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else None,
            'error_message': job.error_message
        })
    
    return jsonify(jobs_data)

def update_progress(current, total, message, job_id=None):
    """更新进度"""
    global current_progress
    current_progress.update({
        'status': 'running',
        'progress': current,
        'total': total,
        'message': message,
        'job_id': job_id
    })

def run_scrape_job(job_id):
    """执行抓取任务"""
    global current_progress
    
    with app.app_context():
        try:
            job = ScrapeJob.query.get(job_id)
            if not job:
                return
            
            job.status = 'running'
            db.session.commit()
            
            # 初始化进度
            current_progress.update({
                'status': 'running',
                'progress': 0,
                'total': 100,
                'message': '开始抓取...',
                'job_id': job_id
            })
            
            # 创建爬虫实例
            scraper = WebScraper(job.target_url)
            
            # 定义进度回调函数
            def progress_callback(current, total, message):
                update_progress(current, total, message, job_id)
            
            # 开始抓取
            articles = scraper.scrape_all_articles(
                start_date=job.start_date,
                end_date=job.end_date,
                progress_callback=progress_callback
            )
            
            if not articles:
                raise Exception("未找到符合条件的文章")
            
            # 保存文章到数据库
            for article_data in articles:
                article = Article()
                article.title = article_data['title']
                article.url = article_data['url']
                article.published_date = article_data.get('published_date')
                article.content = article_data.get('content', '')
                article.job_id = job_id
                db.session.add(article)
            
            job.articles_count = len(articles)
            db.session.commit()
            
            # 生成文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"blog_articles_{timestamp}.{job.output_format}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            current_progress['message'] = f'正在生成{job.output_format.upper()}文件...'
            
            if job.output_format == 'pdf':
                generator = PDFGenerator()
                generator.generate_pdf(articles, output_path, progress_callback)
            else:  # txt
                generator = TXTGenerator()
                generator.generate_txt(articles, output_path, progress_callback)
            
            # 更新任务状态
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.file_path = output_path
            db.session.commit()
            
            # 完成进度
            current_progress.update({
                'status': 'completed',
                'progress': 100,
                'total': 100,
                'message': f'抓取完成! 共处理 {len(articles)} 篇文章',
                'job_id': job_id
            })
            
            logger.info(f"抓取任务完成: job_id={job_id}, articles={len(articles)}")
            
        except Exception as e:
            logger.error(f"抓取任务失败: {str(e)}")
            
            with app.app_context():
                job = ScrapeJob.query.get(job_id)
                if job:
                    job.status = 'failed'
                    job.error_message = str(e)
                    db.session.commit()
            
            current_progress.update({
                'status': 'failed',
                'message': f'抓取失败: {str(e)}',
                'job_id': job_id
            })

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('index.html'), 500
