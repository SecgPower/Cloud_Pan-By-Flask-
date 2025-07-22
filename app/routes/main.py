from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html', title='首页')

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
