// 全局变量
let currentJobId = null;
let progressInterval = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // 绑定表单提交事件
    const scrapeForm = document.getElementById('scrapeForm');
    if (scrapeForm) {
        scrapeForm.addEventListener('submit', handleScrapeSubmit);
    }
    
    // 绑定下载按钮事件
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', handleDownload);
    }
    
    console.log('应用初始化完成');
}

async function handleScrapeSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        target_url: formData.get('target_url'),
        start_date: formData.get('start_date') || null,
        end_date: formData.get('end_date') || null,
        output_format: formData.get('output_format')
    };
    
    // 验证数据
    if (!data.target_url) {
        showAlert('请输入目标网站URL', 'warning');
        return;
    }
    
    // 如果开始日期晚于结束日期
    if (data.start_date && data.end_date && new Date(data.start_date) > new Date(data.end_date)) {
        showAlert('开始日期不能晚于结束日期', 'warning');
        return;
    }
    
    try {
        // 禁用表单
        setFormEnabled(false);
        
        // 显示进度卡片
        showProgressCard();
        
        // 发送请求
        const response = await fetch('/start_scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentJobId = result.job_id;
            showAlert(result.message, 'success');
            
            // 开始监控进度
            startProgressMonitoring();
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        console.error('启动抓取失败:', error);
        showAlert(`启动失败: ${error.message}`, 'danger');
        setFormEnabled(true);
        hideProgressCard();
    }
}

function startProgressMonitoring() {
    // 清除之前的定时器
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    // 立即检查一次进度
    updateProgress();
    
    // 每2秒检查一次进度
    progressInterval = setInterval(updateProgress, 2000);
}

async function updateProgress() {
    try {
        const response = await fetch('/progress');
        const progress = await response.json();
        
        updateProgressUI(progress);
        
        // 如果任务完成或失败，停止监控
        if (progress.status === 'completed' || progress.status === 'failed') {
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            
            if (progress.status === 'completed') {
                showDownloadSection(progress.message);
            } else {
                showErrorSection(progress.message);
            }
            
            // 重新启用表单
            setTimeout(() => {
                setFormEnabled(true);
            }, 1000);
        }
        
    } catch (error) {
        console.error('获取进度失败:', error);
    }
}

function updateProgressUI(progress) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const currentTask = document.getElementById('currentTask');
    
    if (progressBar && progressText && progressPercent) {
        let percentage = 0;
        
        if (progress.total > 0) {
            percentage = Math.round((progress.progress / progress.total) * 100);
        }
        
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        
        progressPercent.textContent = `${percentage}%`;
        progressText.textContent = getStatusText(progress.status);
        
        if (currentTask) {
            currentTask.textContent = progress.message || '';
        }
        
        // 更新进度条颜色
        progressBar.className = `progress-bar progress-bar-striped ${getProgressBarClass(progress.status)}`;
    }
}

function getStatusText(status) {
    const statusMap = {
        'idle': '等待中',
        'running': '抓取中',
        'completed': '完成',
        'failed': '失败'
    };
    
    return statusMap[status] || '未知状态';
}

function getProgressBarClass(status) {
    const classMap = {
        'idle': 'bg-secondary',
        'running': 'bg-primary progress-bar-animated',
        'completed': 'bg-success',
        'failed': 'bg-danger'
    };
    
    return classMap[status] || 'bg-primary';
}

function showProgressCard() {
    const progressCard = document.getElementById('progressCard');
    if (progressCard) {
        progressCard.style.display = 'block';
        progressCard.classList.add('fade-in');
        
        // 隐藏下载和错误部分
        hideDownloadSection();
        hideErrorSection();
    }
}

function hideProgressCard() {
    const progressCard = document.getElementById('progressCard');
    if (progressCard) {
        progressCard.style.display = 'none';
    }
}

function showDownloadSection(message) {
    const downloadSection = document.getElementById('downloadSection');
    const completionMessage = document.getElementById('completionMessage');
    
    if (downloadSection) {
        downloadSection.style.display = 'block';
        downloadSection.classList.add('fade-in');
    }
    
    if (completionMessage && message) {
        completionMessage.textContent = message;
    }
    
    hideErrorSection();
}

function hideDownloadSection() {
    const downloadSection = document.getElementById('downloadSection');
    if (downloadSection) {
        downloadSection.style.display = 'none';
    }
}

function showErrorSection(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    
    if (errorSection) {
        errorSection.style.display = 'block';
        errorSection.classList.add('fade-in');
    }
    
    if (errorMessage && message) {
        errorMessage.textContent = message;
    }
    
    hideDownloadSection();
}

function hideErrorSection() {
    const errorSection = document.getElementById('errorSection');
    if (errorSection) {
        errorSection.style.display = 'none';
    }
}

function handleDownload() {
    if (currentJobId) {
        const downloadUrl = `/download/${currentJobId}`;
        
        // 创建一个临时的a标签进行下载
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showAlert('开始下载文件...', 'info');
    } else {
        showAlert('无法获取下载链接', 'warning');
    }
}

function downloadFile(jobId) {
    const downloadUrl = `/download/${jobId}`;
    window.open(downloadUrl, '_blank');
}

function setFormEnabled(enabled) {
    const form = document.getElementById('scrapeForm');
    const startBtn = document.getElementById('startScrapeBtn');
    
    if (form) {
        const inputs = form.querySelectorAll('input, button');
        inputs.forEach(input => {
            input.disabled = !enabled;
        });
    }
    
    if (startBtn) {
        if (enabled) {
            startBtn.innerHTML = '<i class="fas fa-play me-2"></i>开始抓取';
            startBtn.classList.remove('loading');
        } else {
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>抓取中...';
            startBtn.classList.add('loading');
        }
    }
}

function showAlert(message, type = 'info') {
    // 创建alert元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
    
    const iconMap = {
        'success': 'fas fa-check-circle',
        'danger': 'fas fa-exclamation-triangle',
        'warning': 'fas fa-exclamation-circle',
        'info': 'fas fa-info-circle'
    };
    
    const icon = iconMap[type] || iconMap.info;
    
    alertDiv.innerHTML = `
        <i class="${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

// 工具函数：格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 工具函数：格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 错误处理
window.addEventListener('error', function(event) {
    console.error('JavaScript错误:', event.error);
    showAlert('页面发生错误，请刷新重试', 'danger');
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', function() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
});

console.log('博客爬虫应用脚本加载完成');
