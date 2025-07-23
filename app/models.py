from app import db
from datetime import datetime, timedelta
import uuid
import os

from flask_login import UserMixin
from app import db, login_manager
from app.config import BaseConfig as Config

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # 邮箱验证相关字段
    confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(36), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 注册时间
    
    # 新增头像相关字段
    avatar_filename = db.Column(db.String(255), nullable=True)  # 头像文件名
    avatar_path = db.Column(db.String(512), nullable=True)  # 头像存储路径
    
    # 关联用户的文件和文件夹
    files = db.relationship('File', backref='owner', lazy=True, cascade="all, delete-orphan")
    folders = db.relationship('Folder', backref='owner', lazy=True, cascade="all, delete-orphan")

    admin_authenticated = db.Column(db.Boolean, default=False)  # 标记是否通过管理员验证
    admin_auth_time = db.Column(db.DateTime)  # 记录验证时间

    total_storage_used = db.Column(db.BigInteger, default=0)  # 新增字段
    
    def get_remaining_storage(self):
        """获取剩余存储空间（4GB = 4 * 1024^3 bytes）"""
        return 4 * 1024 * 1024 * 1024 - self.total_storage_used
    
    def can_upload(self, file_size):
        """检查是否可以上传指定大小的文件"""
        return self.get_remaining_storage() >= file_size
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    # 生成邮箱验证令牌
    def generate_confirmation_token(self):
        self.confirmation_token = str(uuid.uuid4())
        db.session.add(self)
        db.session.commit()
        return self.confirmation_token
    
    # 获取头像URL
    def get_avatar(self, size=128):
        if self.avatar_filename:
            return f"/static/avatars/{self.avatar_filename}"
        # 默认头像
        return f"https://ui-avatars.com/api/?name={self.username}&size={size}"
    
    # 删除用户所有数据（用于账号销毁）
    def delete_all_data(self):
        # 删除用户文件夹和文件
        user_dir = os.path.join(Config.UPLOAD_FOLDER, str(self.id))
        if os.path.exists(user_dir):
            import shutil
            try:
                shutil.rmtree(user_dir)
            except Exception as e:
                print(f"删除用户文件失败: {str(e)}")
        
        # 头像文件
        if self.avatar_path and os.path.exists(self.avatar_path):
            try:
                os.remove(self.avatar_path)
            except Exception as e:
                print(f"删除头像失败: {str(e)}")
    
    def __repr__(self):
        return f'<User {self.username}>'

# 文件夹模型保持不变
class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # 文件夹名
    created_time = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)  # 支持子文件夹
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 外键关联用户
    
    # 自引用，用于子文件夹
    subfolders = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade="all, delete-orphan")
    # 关联文件夹中的文件
    files = db.relationship('File', backref='folder', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Folder {self.name}>'

# 文件模型保持不变
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # 文件名
    filepath = db.Column(db.String(512), nullable=False)  # 文件存储路径
    filesize = db.Column(db.Integer)  # 文件大小(字节)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)  # 上传时间
    # 外键关联用户和文件夹
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)  # 可以属于某个文件夹
    
    def __repr__(self):
        return f'<File {self.filename}>'
    
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
class FileShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    created_time = db.Column(db.DateTime, default=datetime.utcnow)
    expires_in = db.Column(db.Integer, default=24)  # 过期时间（小时）
    is_active = db.Column(db.Boolean, default=True)
    
    # 关联文件
    file = db.relationship('File', backref=db.backref('shares', lazy=True))
    
    def is_expired(self):
        """检查分享是否过期"""
        return datetime.utcnow() > self.created_time + timedelta(hours=self.expires_in)
    
class FolderShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_code = db.Column(db.String(36), unique=True, nullable=False, 
                          default=lambda: str(uuid.uuid4()))  # 唯一分享码
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)  # 关联文件夹
    created_time = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    expires_in = db.Column(db.Integer, nullable=False, default=24)  # 过期小时数，默认24小时
    is_active = db.Column(db.Boolean, default=True)  # 是否有效

    # 关联到文件夹
    folder = db.relationship('Folder', backref=db.backref('shares', lazy=True))

    def is_expired(self):
        """检查分享是否已过期"""
        return datetime.utcnow() > self.created_time + timedelta(hours=self.expires_in)