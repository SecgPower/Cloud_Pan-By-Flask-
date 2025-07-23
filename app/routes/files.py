from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import File, Folder
from app.config import BaseConfig as Config
import os
from werkzeug.utils import secure_filename
import shutil
from app.models import FileShare, FolderShare
from datetime import timedelta, datetime

# 创建文件管理蓝图
files = Blueprint('files', __name__)

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# 转换文件大小单位
def convert_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

# 获取当前路径下的内容（文件夹和文件）
def get_contents(folder_id=None):
    # 获取当前文件夹
    current_folder = None
    if folder_id:
        current_folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()
        if not current_folder:
            return None, None, None  # 文件夹不存在或无权限
    
    # 获取当前文件夹下的子文件夹
    subfolders = Folder.query.filter_by(parent_id=folder_id, user_id=current_user.id).order_by(Folder.name).all()
    
    # 获取当前文件夹下的文件
    files = File.query.filter_by(folder_id=folder_id, user_id=current_user.id).order_by(File.filename).all()
    # 转换文件大小显示
    for file in files:
        file.display_size = convert_size(file.filesize)

    # 获取当前文件夹下的文件，按文件名排序
    files = File.query.filter_by(folder_id=folder_id, user_id=current_user.id)\
                .order_by(File.filename.asc())\
                .all()
    
    return current_folder, subfolders, files

# 文件列表页面（支持文件夹导航）
@files.route('/files')
@files.route('/files/<int:folder_id>')
@login_required
def file_list(folder_id=None):
    current_folder, subfolders, files = get_contents(folder_id)
    
    if folder_id and current_folder is None:
        flash('文件夹不存在或无访问权限', 'danger')
        return redirect(url_for('files.file_list'))
    
    # 获取当前路径的导航链
    breadcrumbs = []
    current = current_folder
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent
    return render_template('file_list.html', 
                         current_folder=current_folder,
                         folders=subfolders,
                         files=files,
                         breadcrumbs=breadcrumbs,
                         timedelta=timedelta)

# 创建文件夹
@files.route('/files/create-folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form.get('folder_name').strip()
    parent_id = request.form.get('parent_id') or None
    
    if not folder_name:
        flash('文件夹名称不能为空', 'danger')
        return redirect(url_for('files.file_list', folder_id=parent_id))
    
    # 检查同名文件夹
    existing_folder = Folder.query.filter_by(
        name=folder_name, 
        parent_id=parent_id,
        user_id=current_user.id
    ).first()
    
    if existing_folder:
        flash(f'文件夹 "{folder_name}" 已存在', 'warning')
        return redirect(url_for('files.file_list', folder_id=parent_id))
    
    # 创建文件夹记录
    new_folder = Folder(
        name=folder_name,
        parent_id=parent_id,
        user_id=current_user.id
    )
    db.session.add(new_folder)
    db.session.commit()
    
    # 创建对应的物理文件夹
    user_dir = os.path.join(Config.UPLOAD_FOLDER, str(current_user.id))
    folder_path = os.path.join(user_dir, str(new_folder.id))
    os.makedirs(folder_path, exist_ok=True)
    
    flash(f'文件夹 "{folder_name}" 创建成功', 'success')
    return redirect(url_for('files.file_list', folder_id=parent_id))

# 文件上传处理（支持上传到指定文件夹）
@files.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    # 检查是否有文件被上传
    if 'file' not in request.files:
        flash('未选择文件', 'danger')
        folder_id = request.form.get('folder_id')
        return redirect(url_for('files.file_list', folder_id=folder_id))
    
    file = request.files['file']
    folder_id = request.form.get('folder_id') or None
    
    # 检查文件名是否为空
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('files.file_list', folder_id=folder_id))
    
    # 检查文件大小是否超出用户配额
    if file and allowed_file(file.filename):
        # 获取文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        if not current_user.can_upload(file_size):
            remaining = current_user.get_remaining_storage()
            flash(f'存储空间不足！剩余空间: {convert_size(remaining)}', 'danger')
            return redirect(url_for('files.file_list', folder_id=folder_id))
    
    # 检查文件是否合法
    if file and allowed_file(file.filename):
        # 确保文件名安全(已移除)
        filename = file.filename #secure_filename(file.filename)
        
        # 创建用户专属目录
        user_dir = os.path.join(Config.UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        
        # 如果指定了文件夹，使用文件夹ID作为子目录
        if folder_id:
            folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()
            if folder:
                user_dir = os.path.join(user_dir, str(folder_id))
                os.makedirs(user_dir, exist_ok=True)
        
        # 保存文件路径
        filepath = os.path.join(user_dir, filename)
        
        # 检查文件是否已存在
        if os.path.exists(filepath):
            flash(f'文件 "{filename}" 已存在', 'warning')
            return redirect(url_for('files.file_list', folder_id=folder_id))
        
        # 保存文件
        file.save(filepath)
        
        # 获取文件大小
        filesize = os.path.getsize(filepath)
        
        # 创建文件记录并保存到数据库
        new_file = File(
            filename=filename,
            filepath=filepath,
            filesize=filesize,
            user_id=current_user.id,
            folder_id=folder_id
        )
        db.session.add(new_file)
        db.session.commit()

        # 保存文件后更新用户存储使用量
        current_user.total_storage_used += filesize
        db.session.commit()
        
        flash(f'文件 "{filename}" 上传成功', 'success')
        return redirect(url_for('files.file_list', folder_id=folder_id))
    
    flash('不支持的文件类型', 'danger')
    return redirect(url_for('files.file_list', folder_id=folder_id))

# 文件重命名
@files.route('/files/rename/<int:file_id>', methods=['POST'])
@login_required
def rename_file(file_id):
    # 获取文件记录
    file = File.query.get_or_404(file_id)
    
    # 验证文件所有权
    if file.user_id != current_user.id:
        flash('没有访问权限', 'danger')
        return redirect(url_for('files.file_list', folder_id=file.folder_id))
    
    new_name = request.form.get('new_name').strip()
    if not new_name:
        flash('文件名不能为空', 'danger')
        return redirect(url_for('files.file_list', folder_id=file.folder_id))
    
    # 检查新文件名是否已存在
    existing_file = File.query.filter_by(
        filename=new_name,
        folder_id=file.folder_id,
        user_id=current_user.id
    ).first()
    
    if existing_file and existing_file.id != file.id:
        flash(f'文件 "{new_name}" 已存在', 'warning')
        return redirect(url_for('files.file_list', folder_id=file.folder_id))
    
    # 获取原文件路径和新文件路径
    old_path = file.filepath
    directory = os.path.dirname(old_path)
    new_path = os.path.join(directory, new_name)
    
    try:
        # 重命名物理文件
        os.rename(old_path, new_path)
        
        # 更新数据库记录
        file.filename = new_name
        file.filepath = new_path
        db.session.commit()
        
        flash(f'文件已重命名为 "{new_name}"', 'success')
    except Exception as e:
        flash(f'重命名失败: {str(e)}', 'danger')
    
    return redirect(url_for('files.file_list', folder_id=file.folder_id))

# 文件夹重命名
@files.route('/files/rename-folder/<int:folder_id>', methods=['POST'])
@login_required
def rename_folder(folder_id):
    # 获取文件夹记录
    folder = Folder.query.get_or_404(folder_id)
    
    # 验证文件夹所有权
    if folder.user_id != current_user.id:
        flash('没有访问权限', 'danger')
        return redirect(url_for('files.file_list', folder_id=folder.parent_id))
    
    new_name = request.form.get('new_name').strip()
    if not new_name:
        flash('文件夹名称不能为空', 'danger')
        return redirect(url_for('files.file_list', folder_id=folder.parent_id))
    
    # 检查新文件夹名是否已存在
    existing_folder = Folder.query.filter_by(
        name=new_name,
        parent_id=folder.parent_id,
        user_id=current_user.id
    ).first()
    
    if existing_folder and existing_folder.id != folder.id:
        flash(f'文件夹 "{new_name}" 已存在', 'warning')
        return redirect(url_for('files.file_list', folder_id=folder.parent_id))
    
    try:
        # 更新数据库记录
        folder.name = new_name
        db.session.commit()
        
        flash(f'文件夹已重命名为 "{new_name}"', 'success')
    except Exception as e:
        flash(f'重命名失败: {str(e)}', 'danger')
    
    return redirect(url_for('files.file_list', folder_id=folder.parent_id))

@files.route('/files/download/<int:file_id>')
def download_file(file_id):  # 移除 login_required 装饰器，允许匿名访问共享文件
    file = File.query.get_or_404(file_id)
    
    # 权限验证：要么是文件所有者，要么有有效的分享码
    is_owner = current_user.is_authenticated and file.user_id == current_user.id
    share_code = request.args.get('share_code')
    is_valid_share = False
    
    if share_code:
        # 检查分享是否有效
        share = FolderShare.query.filter_by(
            share_code=share_code,
            is_active=True,
            folder_id=file.folder_id
        ).first()
        is_valid_share = share is not None and not share.is_expired()
    
    if not is_owner and not is_valid_share:
        flash('没有访问权限或分享已过期', 'danger')
        return redirect(url_for('main.index'))
    
    # 发送文件下载
    directory = os.path.dirname(file.filepath)
    filename = os.path.basename(file.filepath)
    return send_from_directory(directory, filename, as_attachment=True)

# 文件删除
@files.route('/files/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    # 获取文件记录
    file = File.query.get_or_404(file_id)
    folder_id = file.folder_id  # 记录父文件夹ID用于重定向
    
    # 验证文件所有权
    if file.user_id != current_user.id:
        flash('没有删除权限', 'danger')
        return redirect(url_for('files.file_list', folder_id=folder_id))
    
    # 保存文件名用于提示
    filename = file.filename
    
    # 删除物理文件
    if os.path.exists(file.filepath):
        try:
            os.remove(file.filepath)
        except Exception as e:
            flash(f'删除文件失败: {str(e)}', 'danger')
            return redirect(url_for('files.file_list', folder_id=folder_id))
    
    # 从数据库删除记录
    db.session.delete(file)
    db.session.commit()
    
    flash(f'文件 "{filename}" 已删除', 'success')
    return redirect(url_for('files.file_list', folder_id=folder_id))

# 文件夹删除
@files.route('/files/delete-folder/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    # 获取文件夹记录
    folder = Folder.query.get_or_404(folder_id)
    parent_id = folder.parent_id  # 记录父文件夹ID用于重定向
    
    # 验证文件夹所有权
    if folder.user_id != current_user.id:
        flash('没有删除权限', 'danger')
        return redirect(url_for('files.file_list', folder_id=parent_id))
    
    # 保存文件夹名用于提示
    folder_name = folder.name
    
    # 删除物理文件夹及其内容
    folder_path = os.path.join(Config.UPLOAD_FOLDER, str(current_user.id), str(folder_id))
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            flash(f'删除文件夹失败: {str(e)}', 'danger')
            return redirect(url_for('files.file_list', folder_id=parent_id))
    
    # 从数据库删除记录（级联删除子文件夹和文件）
    db.session.delete(folder)
    db.session.commit()
    
    flash(f'文件夹 "{folder_name}" 已删除', 'success')
    return redirect(url_for('files.file_list', folder_id=parent_id))

# 创建文件分享
@files.route('/files/share/<int:file_id>', methods=['POST'])
@login_required
def create_share(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('没有权限分享此文件', 'danger')
        return redirect(url_for('files.file_list', folder_id=file.folder_id))
    
    # 获取过期时间（默认24小时）
    expires_in = int(request.form.get('expires_in', 24))
    
    # 创建分享记录
    share = FileShare(
        file_id=file.id,
        expires_in=expires_in
    )
    db.session.add(share)
    db.session.commit()
    
    # 生成分享链接
    share_link = url_for('files.access_shared', share_code=share.share_code, _external=True)
    flash(f'文件分享成功！分享链接：{share_link}', 'success')
    return redirect(url_for('files.file_list', folder_id=file.folder_id))

# 访问分享的文件
@files.route('/files/shared/<string:share_code>')
def access_shared(share_code):
    share = FileShare.query.filter_by(share_code=share_code, is_active=True).first()
    if not share or share.is_expired():
        flash('分享链接无效或已过期', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('shared_file.html', share=share, timedelta=timedelta)

# 下载分享的文件
@files.route('/files/shared/download/<string:share_code>')
def download_shared(share_code):
    share = FileShare.query.filter_by(share_code=share_code, is_active=True).first()
    if not share or share.is_expired():
        flash('分享链接无效或已过期', 'danger')
        return redirect(url_for('main.index'))
    
    file = share.file
    directory = os.path.dirname(file.filepath)
    filename = os.path.basename(file.filepath)
    return send_from_directory(directory, filename, as_attachment=True)

# 取消文件分享
@files.route('/files/unshare/<int:share_id>', methods=['POST'])
@login_required
def cancel_share(share_id):
    share = FileShare.query.get_or_404(share_id)
    if share.file.user_id != current_user.id:
        flash('没有权限取消此分享', 'danger')
        return redirect(url_for('files.file_list'))
    
    share.is_active = False
    db.session.commit()
    flash('文件分享已取消', 'success')
    return redirect(url_for('files.file_list', folder_id=share.file.folder_id))

# 生成文件夹分享链接
@files.route('/files/share-folder/<int:folder_id>', methods=['POST'])
@login_required
def generate_folder_share(folder_id):
    # 验证文件夹所有权
    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()
    if not folder:
        flash('文件夹不存在或无权限', 'danger')
        return redirect(url_for('files.file_list', folder_id=folder.parent_id if folder else None))
    
    # 获取用户设置的过期时间（小时）
    expires_in = int(request.form.get('expires_in', 24))
    
    # 创建分享记录
    share = FolderShare(
        folder_id=folder.id,
        expires_in=expires_in
    )
    db.session.add(share)
    db.session.commit()
    
    # 生成完整分享链接
    share_link = url_for('files.access_shared_folder', share_code=share.share_code, _external=True)
    flash(f'文件夹分享成功！分享链接：<br>{share_link}', 'success')
    return redirect(url_for('files.file_list', folder_id=folder.parent_id))

# 访问共享文件夹
@files.route('/files/shared-folder/<string:share_code>')
def access_shared_folder(share_code):
    # 验证分享有效性
    share = FolderShare.query.filter_by(share_code=share_code, is_active=True).first()
    if not share or share.is_expired():
        flash('分享链接无效或已过期', 'danger')
        return redirect(url_for('main.index'))
    
    # 获取文件夹内容
    folder = share.folder
    subfolders = Folder.query.filter_by(parent_id=folder.id, user_id=folder.user_id).order_by(Folder.name).all()
    files = File.query.filter_by(folder_id=folder.id, user_id=folder.user_id).order_by(File.filename).all()
    
    # 格式化文件大小
    for file in files:
        file.display_size = convert_size(file.filesize)
    
    return render_template('shared_folder.html', 
                         share=share,
                         folder=folder,
                         subfolders=subfolders,
                         files=files,
                         timedelta=timedelta)

# 取消文件夹分享
@files.route('/files/unshare-folder/<int:share_id>', methods=['POST'])
@login_required
def unshare_folder(share_id):
    share = FolderShare.query.get_or_404(share_id)
    # 验证所有权
    if share.folder.user_id != current_user.id:
        flash('无权限执行此操作', 'danger')
        return redirect(url_for('files.file_list'))
    
    share.is_active = False
    db.session.commit()
    flash('文件夹分享已取消', 'success')
    return redirect(url_for('files.file_list', folder_id=share.folder.parent_id))