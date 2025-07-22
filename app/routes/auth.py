from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user
from flask_mail import Message
from flask_login import logout_user
from app import db, mail
#from app.config import mail
from app.models import User
# 不需要单独导入werkzeug的函数，因为User模型中已经实现了密码处理

auth = Blueprint('auth', __name__)

# 新增：发送验证邮件函数
def send_confirmation_email(user):
    token = user.generate_confirmation_token()
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    subject = '请验证您的邮箱'
    message = f'请点击以下链接验证您的邮箱：{confirm_url}'
    
    msg = Message(subject, recipients=[user.email])
    msg.body = message
    mail.send(msg)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash('请检查您的登录信息并重试。', 'danger')
        return redirect(url_for('auth.login'))
    
    # 新增：检查邮箱是否已验证
    if not user.confirmed:
        flash('请先验证您的邮箱才能登录。', 'warning')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('main.index'))

@auth.route('/signup')
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    user = User.query.filter_by(email=email).first()
    if user:
        flash('该邮箱已被注册', 'danger')
        return redirect(url_for('auth.signup'))
        
    if password != password_confirm:
        flash('两次输入的密码不一致', 'danger')
        return redirect(url_for('auth.signup'))

    new_user = User(email=email, username=username)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()

    # 新增：发送验证邮件
    send_confirmation_email(new_user)
    flash('注册成功，验证邮件已发送，请查收并验证您的邮箱', 'success')
    return redirect(url_for('auth.login'))

# 新增：重新发送验证邮件
@auth.route('/resend-confirmation')
def resend_confirmation():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('该邮箱未注册', 'danger')
        return redirect(url_for('auth.signup'))
    
    if user.confirmed:
        flash('您的邮箱已验证，无需重复验证', 'info')
        return redirect(url_for('auth.login'))
    
    send_confirmation_email(user)
    flash('验证邮件已重新发送，请查收', 'success')
    return redirect(url_for('auth.login'))

# 新增：处理邮箱验证
@auth.route('/confirm/<token>')
def confirm_email(token):
    # 根据令牌查找用户
    user = User.query.filter_by(confirmation_token=token).first()
    
    if not user:
        flash('验证链接无效或已过期', 'danger')
        return redirect(url_for('auth.login'))
    
    # 标记邮箱为已验证
    user.confirmed = True
    user.confirmation_token = None  # 验证后清空令牌
    db.session.commit()
    return "已完成验证"

@auth.route('/logout')
def logout():
    logout_user()  # 使用从flask_login导入的logout_user函数
    flash('您已成功退出登录', 'info')  # 添加退出成功提示
    return redirect(url_for('main.index'))  # 退出后重定向到首页