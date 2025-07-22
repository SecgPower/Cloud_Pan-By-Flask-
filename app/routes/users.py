from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user, logout_user
from app import db
from app.models import User, File, Folder
from app.config import BaseConfig as Config
import os
from werkzeug.utils import secure_filename
import shutil

users = Blueprint('users', __name__)

# 检查头像文件类型
def allowed_avatar(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_AVATAR_EXTENSIONS

# 用户资料页面
@users.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='个人资料')

# 上传头像
@users.route('/profile/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    # 检查是否有文件被上传
    if 'avatar' not in request.files:
        flash('未选择文件', 'danger')
        return redirect(url_for('users.profile'))
    
    file = request.files['avatar']
    
    # 检查文件名是否为空
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('users.profile'))
    
    # 检查文件是否合法
    if file and allowed_avatar(file.filename):
        # 确保文件名安全
        filename = secure_filename(file.filename)
        # 添加用户ID前缀，避免文件名冲突
        unique_filename = f"avatar_{current_user.id}_{filename}"
        
        # 创建头像存储目录
        os.makedirs(Config.AVATAR_FOLDER, exist_ok=True)
        
        # 保存文件路径
        filepath = os.path.join(Config.AVATAR_FOLDER, unique_filename)
        
        # 如果用户已有头像，先删除旧头像
        if current_user.avatar_path and os.path.exists(current_user.avatar_path):
            try:
                os.remove(current_user.avatar_path)
            except Exception as e:
                flash(f'删除旧头像失败: {str(e)}', 'warning')
        
        # 保存新头像
        file.save(filepath)
        
        # 更新数据库记录
        current_user.avatar_filename = unique_filename
        current_user.avatar_path = filepath
        db.session.commit()
        
        flash('头像上传成功', 'success')
        return redirect(url_for('users.profile'))
    
    flash('不支持的文件类型，仅支持 PNG, JPG, JPEG, GIF', 'danger')
    return redirect(url_for('users.profile'))

# 账号销毁确认页面
@users.route('/profile/delete-account')
@login_required
def delete_account_confirm():
    return render_template('delete_account.html', title='确认销毁账号')

# 执行账号销毁
@users.route('/profile/delete-account/confirm', methods=['POST'])
@login_required
def delete_account():
    # 验证密码
    password = request.form.get('password')
    if not current_user.check_password(password):
        flash('密码不正确，无法销毁账号', 'danger')
        return redirect(url_for('users.delete_account_confirm'))
    
    # 获取用户名用于提示
    username = current_user.username
    
    # 删除用户所有数据
    current_user.delete_all_data()
    
    # 从数据库删除用户
    db.session.delete(current_user)
    db.session.commit()
    
    # 登出用户
    logout_user()
    
    flash(f'账号 "{username}" 已成功销毁，所有相关数据已删除', 'success')
    return redirect(url_for('main.index'))