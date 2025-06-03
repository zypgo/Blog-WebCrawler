# 通用网页爬虫工具 🕷️

一个强大的基于Flask的通用网页内容爬取和转换工具，支持自动抓取任意静态博客网站的文章内容并导出为PDF或TXT格式。仅供用于个人学习，与技术学习，切勿用做任何其他用途。

## ✨ 主要功能

- **通用网站支持**: 支持抓取任意博客内容
- **智能内容提取**: 使用trafilatura和BeautifulSoup进行高质量文章内容提取
- **多种输出格式**: 支持PDF和TXT两种导出格式
- **日期筛选**: 可按发布日期范围过滤文章内容
- **图片处理**: 自动提取和处理文章中的图片
- **进度监控**: 实时显示爬取进度和状态
- **任务管理**: 查看历史任务和下载生成的文件

## 🛠️ 技术栈

- **后端**: Flask, SQLAlchemy, Gunicorn
- **爬虫**: trafilatura, BeautifulSoup, requests
- **PDF生成**: ReportLab
- **数据库**: SQLite
- **前端**: Bootstrap 5, JavaScript

## 🚀 快速开始

### 环境要求

- Python 3.11+
- 所需依赖包已在 `pyproject.toml` 中定义

### 安装运行

1. 克隆项目
```bash
git clone <repository-url>
cd web-scraper
```

2. 安装依赖
```bash
pip install -r requirements.txt
# 或使用 uv
uv sync
```

3. 启动应用
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

4. 打开浏览器访问 `http://localhost:5000`

## 📖 使用说明

### 基本使用流程

1. **输入目标网站URL**: 在输入框中填入要抓取的网站地址
2. **设置日期范围（可选）**: 选择开始和结束日期来过滤文章
3. **选择输出格式**: PDF格式包含图片适合阅读，TXT格式体积小便于处理
4. **开始爬取**: 点击"开始爬取"按钮启动任务
5. **监控进度**: 实时查看爬取进度和状态
6. **下载文件**: 完成后点击下载按钮获取生成的文件

### 支持的网站类型

- 个人博客（WordPress, Ghost, Jekyll等）
- 新闻网站
- 技术文档站点
- 在线杂志和期刊
- 其他基于HTML的内容网站

### 日期筛选功能

工具支持多种日期格式的自动识别：
- ISO格式: `2024-01-01`
- 中文格式: `2024年1月1日`
- 英文格式: `January 1, 2024`
- 简写格式: `Jan 1, 2024`

## 🏗️ 项目结构

```
├── app.py              # Flask应用配置
├── main.py             # 应用入口点
├── models.py           # 数据库模型
├── routes.py           # 路由处理
├── scraper.py          # 爬虫核心逻辑
├── pdf_generator.py    # PDF和TXT生成
├── templates/          # HTML模板
│   ├── base.html
│   └── index.html
├── static/             # 静态资源
│   ├── css/
│   └── js/
│       └── app.js
└── downloads/          # 生成的文件存储目录
```

## 🔧 核心组件

### WebScraper类
- 通用网站链接发现
- 智能内容提取
- 多格式日期解析
- 图片资源处理

### PDFGenerator类
- 中文字体支持
- 图片嵌入处理
- 自动版式布局
- 目录生成

### TXTGenerator类
- 纯文本导出
- 结构化内容组织
- 字符编码处理

## 📊 功能特性

### 智能内容识别
- 自动识别文章容器和标题
- 过滤导航、广告等非内容元素
- 保持文章原始结构和格式

### 多格式日期支持
- HTML meta标签日期提取
- 文本内容日期识别
- 多语言日期格式支持

### 错误处理和日志
- 详细的错误信息记录
- 爬取进度实时反馈
- 网络异常自动重试

## 🔍 使用示例

### 基本爬取
```
目标URL: https://example-blog.com
输出格式: PDF
结果: 获取该博客的所有文章并生成PDF文件
```

### 日期过滤
```
目标URL: https://news-site.com
开始日期: 2024-01-01
结束日期: 2024-03-31
输出格式: TXT
结果: 获取该时间段内的新闻文章并生成TXT文件
```

## ⚙️ 配置选项

### 数据库配置
应用使用SQLite数据库存储任务信息和文章数据，数据库文件位于 `instance/blog_scraper.db`

### 文件存储
生成的PDF和TXT文件保存在 `downloads/` 目录下

## 🛡️ 注意事项

- 请遵守目标网站的robots.txt协议
- 合理控制爬取频率，避免对目标服务器造成压力
- 确保有权限爬取目标网站的内容
- 注意版权和法律法规要求

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🔗 相关链接

- [trafilatura文档](https://trafilatura.readthedocs.io/)
- [ReportLab文档](https://www.reportlab.com/docs/)
- [Flask文档](https://flask.palletsprojects.com/)

---

*这是一个用于学习和研究目的的开源项目，请负责任地使用。*
