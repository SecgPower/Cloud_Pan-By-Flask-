from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models import User, File, Folder
from app.config import BaseConfig as Config
import os
import hashlib
from datetime import datetime, timedelta
import shutil

admin = Blueprint('admin', __name__)

# 密钥验证函数
def verify_admin_key(uploaded_file):
    # 检查管理员密钥文件是否存在
    admin_key_path = os.path.join(Config.ADMIN_KEY_FOLDER, Config.ADMIN_KEY_FILENAME)
    print(f"本地密钥文件路径: {admin_key_path}")  # 调试用
    
    if not os.path.exists(admin_key_path):
        print("本地密钥文件不存在")  # 调试用
        return False
    
    # 检查文件是否可读取
    if not os.access(admin_key_path, os.R_OK):
        print("没有本地密钥文件的读取权限")  # 调试用
        return False
    
    # 计算本地密钥文件的哈希（必须用二进制模式读取）
    try:
        with open(admin_key_path, 'rb') as f:
            local_content = f.read()
            local_hash = hashlib.sha256(local_content).hexdigest()
        print(f"本地密钥哈希: {local_hash}")  # 调试用
    except Exception as e:
        print(f"读取本地密钥失败: {str(e)}")  # 调试用
        return False
    
    # 计算上传文件的哈希（同样用二进制模式）
    try:
        # 重置文件指针到开头（避免上传文件读取不完整）
        uploaded_file.seek(0)
        uploaded_content = uploaded_file.read()
        uploaded_hash = hashlib.sha256(uploaded_content).hexdigest()
        print(f"上传文件哈希: {uploaded_hash}")  # 调试用
    except Exception as e:
        print(f"读取上传文件失败: {str(e)}")  # 调试用
        return False
    
    # 对比哈希值
    return local_hash == uploaded_hash

# 管理员登录页面（密钥验证）
@admin.route('/admin/login', methods=['GET', 'POST'])
@login_required
def admin_login():
    # 检查用户是否已通过管理员验证
    if hasattr(current_user, 'admin_authenticated') and current_user.admin_authenticated:
        # 检查会话是否过期
        if hasattr(current_user, 'admin_auth_time') and \
           datetime.utcnow() - current_user.admin_auth_time < Config.ADMIN_SESSION_DURATION:
            return redirect(url_for('admin.dashboard'))
        else:
            # 会话过期，清除认证状态
            current_user.admin_authenticated = False
            current_user.admin_auth_time = None
    
    if request.method == 'POST':
        # 检查是否有文件被上传
        if 'admin_key' not in request.files:
            flash('未选择密钥文件', 'danger')
            return render_template('admin_login.html', title='管理员验证')
        
        key_file = request.files['admin_key']
        
        # 检查文件名是否为空
        if key_file.filename == '':
            flash('未选择密钥文件', 'danger')
            return render_template('admin_login.html', title='管理员验证')
        
        # 验证密钥
        if verify_admin_key(key_file):
            # 记录认证状态和时间
            current_user.admin_authenticated = True
            current_user.admin_auth_time = datetime.utcnow()
            db.session.commit()
            print("密钥验证成功，已设置管理员会话")  # 调试用
            return redirect(url_for('admin.dashboard'))  # 注意蓝图名称是admin
        else:
            print("密钥验证失败，哈希不匹配")  # 调试用
            flash('密钥验证失败，请使用正确的管理员密钥文件', 'danger')
    
    return render_template('admin_login.html', title='管理员验证')

# 管理员登出
@admin.route('/admin/logout')
@login_required
def admin_logout():
    current_user.admin_authenticated = False
    current_user.admin_auth_time = None
    db.session.commit()
    flash('已退出管理员模式', 'info')
    return redirect(url_for('main.index'))

# 检查管理员权限的装饰器
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否已认证
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        
        # 检查是否通过管理员验证
        if not hasattr(current_user, 'admin_authenticated') or not current_user.admin_authenticated:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('admin.admin_login'))  # 确保这里的路由正确
        
        # 检查会话是否过期
        if hasattr(current_user, 'admin_auth_time'):
            time_diff = datetime.utcnow() - current_user.admin_auth_time
            if time_diff >= Config.ADMIN_SESSION_DURATION:
                current_user.admin_authenticated = False
                current_user.admin_auth_time = None
                db.session.commit()
                flash('管理员会话已过期，请重新验证', 'warning')
                return redirect(url_for('admin.admin_login'))  # 确保路由正确
        else:
            # 如果没有认证时间，视为未认证
            current_user.admin_authenticated = False
            db.session.commit()
            return redirect(url_for('admin.admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

# 管理员控制面板
@admin.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    # 获取用户总数和文件总数
    user_count = User.query.count()
    file_count = File.query.count()
    folder_count = Folder.query.count()
    
    # 计算总存储量
    total_storage = sum(file.filesize for file in File.query.all())
    
    # 转换存储单位显示
    def convert_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    total_storage_display = convert_size(total_storage)
    
    return render_template('admin_dashboard.html', 
                         title='管理员面板',
                         user_count=user_count,
                         file_count=file_count,
                         folder_count=folder_count,
                         total_storage=total_storage_display)

# 用户管理页面
@admin.route('/admin/users')
@login_required
@admin_required
def user_management():
    users = User.query.order_by(User.username).all()
    return render_template('admin_users.html', title='用户管理', users=users)

# 删除用户
@admin.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('不能删除当前登录的管理员账号', 'danger')
        return redirect(url_for('admin.user_management'))
    
    user = User.query.get_or_404(user_id)
    username = user.username
    
    # 删除用户所有数据
    user.delete_all_data()
    
    # 从数据库删除用户
    db.session.delete(user)
    db.session.commit()
    
    flash(f'用户 "{username}" 已成功删除', 'success')
    return redirect(url_for('admin.user_management'))

# 文件管理页面
@admin.route('/admin/files')
@login_required
@admin_required
def file_management():
    # 可以按用户筛选文件
    user_id = request.args.get('user_id', type=int)
    if user_id:
        files = File.query.filter_by(user_id=user_id).order_by(File.upload_time.desc()).all()
        current_user_filter = User.query.get(user_id)
    else:
        files = File.query.order_by(File.upload_time.desc()).all()
        current_user_filter = None
    
    # 获取所有用户用于筛选
    users = User.query.order_by(User.username).all()
    
    # 转换文件大小显示
    for file in files:
        if file.filesize < 1024:
            file.display_size = f"{file.filesize} B"
        elif file.filesize < 1024 * 1024:
            file.display_size = f"{file.filesize / 1024:.2f} KB"
        else:
            file.display_size = f"{file.filesize / (1024 * 1024):.2f} MB"
    
    return render_template('admin_files.html', 
                         title='文件管理',
                         files=files,
                         users=users,
                         current_user_filter=current_user_filter)

# 删除文件
@admin.route('/admin/files/delete/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    filename = file.filename
    user_id = file.user_id
    
    # 删除物理文件
    if os.path.exists(file.filepath):
        try:
            os.remove(file.filepath)
        except Exception as e:
            flash(f'删除文件失败: {str(e)}', 'danger')
            return redirect(url_for('admin.file_management', user_id=user_id))
    
    # 从数据库删除记录
    db.session.delete(file)
    db.session.commit()
    
    flash(f'文件 "{filename}" 已删除', 'success')
    return redirect(url_for('admin.file_management', user_id=user_id))