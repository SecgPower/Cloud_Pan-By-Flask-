from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_mail import Mail
from app.config import BaseConfig
import os

# 初始化数据库
db = SQLAlchemy()

# 初始化登录管理器
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# 初始化邮件服务
mail = Mail()

# 添加用户加载函数 - 新增
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def create_app(config_class=BaseConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AVATAR_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ADMIN_KEY_FOLDER'], exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # 注册蓝图
    from app.routes.main import main as main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes.files import files as files_bp
    app.register_blueprint(files_bp, url_prefix='/files')
    
    from app.routes.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # 注册用户和管理员蓝图
    from app.routes.users import users as users_bp
    app.register_blueprint(users_bp, url_prefix='/user')
    
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app