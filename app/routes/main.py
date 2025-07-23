from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import File

main = Blueprint('main', __name__)

@main.route('/')
def index():
    recent_files = []
    if current_user.is_authenticated:
        # 获取最近5个文件，按上传时间排序
        recent_files = File.query.filter_by(user_id=current_user.id)\
                        .order_by(File.upload_time.desc())\
                        .limit(5)\
                        .all()
        # 转换文件大小显示
        for file in recent_files:
            if file.filesize < 1024:
                file.display_size = f"{file.filesize} B"
            elif file.filesize < 1024 * 1024:
                file.display_size = f"{file.filesize / 1024:.2f} KB"
            else:
                file.display_size = f"{file.filesize / (1024 * 1024):.2f} MB"
    
    return render_template('index.html', recent_files=recent_files)

@main.route('/about')
def about():
    return render_template('about.html', title='关于我们')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # 处理表单提交
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # 这里可以添加保存消息到数据库或发送邮件的逻辑
        print(f"收到来自 {name} 的消息: {message}")
        return redirect(url_for('main.index'))
    
    return render_template('contact.html', title='联系我们')

@main.route('/profile')
@login_required  # 该装饰器确保只有已登录用户才能访问此页面
def profile():
    # current_user包含当前登录用户的信息，传递给模板
    return render_template('profile.html', title='个人资料', user=current_user)
