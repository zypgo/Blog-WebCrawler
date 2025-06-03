from datetime import datetime
from app import db

class ScrapeJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    output_format = db.Column(db.String(10), nullable=False)  # 'pdf' or 'txt'
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    articles_count = db.Column(db.Integer, default=0)
    file_path = db.Column(db.String(255))
    error_message = db.Column(db.Text)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    published_date = db.Column(db.Date)
    content = db.Column(db.Text)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey('scrape_job.id'))
