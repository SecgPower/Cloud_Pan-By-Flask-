import os
from datetime import timedelta
from flask_mail import Mail

basedir = os.path.abspath(os.path.dirname(__file__))

# 基础配置类
class BaseConfig:
    # 应用密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'site.db')
    
    # 数据库配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 服务器配置 - 添加HOST和PORT默认值
    HOST = os.environ.get('FLASK_HOST') or '127.0.0.1'  # 默认本地访问
    PORT = int(os.environ.get('FLASK_PORT') or 5000)     # 默认端口5000
    DEBUG = True  # 默认关闭调试模式
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 
        'static', 
        'uploads'
    )
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024 *20 # 100MB
    
    # 允许上传的文件类型
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp',
        'zip', 'rar', 'tar', 'gz', '7z',
        'csv', 'json', 'xml', 'md', 'mp4', 'mp3', '*'
    }

    # 头像上传配置
    AVATAR_FOLDER = os.path.join(basedir, 'static', 'avatars')
    ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
    
    # 管理员密钥配置
    ADMIN_KEY_FOLDER = os.path.join(basedir, 'admin_keys')
    ADMIN_KEY_FILENAME = 'admin_key.dat'  # 密钥文件名
    ADMIN_SESSION_DURATION = timedelta(hours=1)  # 管理员会话有效期
    
    # Flask-Login配置
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    #Flask-Mail配置
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = '3822415948@qq.com'  # 占位邮箱
    MAIL_PASSWORD = 'jmxoongwchjbcfhh'  # 占位密码
    MAIL_DEFAULT_SENDER = '3822415948@qq.com'  # 占位邮箱


# 开发环境配置
class DevelopmentConfig(BaseConfig):
    DEBUG = True  # 开发环境启用调试模式
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 
            '..', 
            'site.db'
        )


# 测试环境配置
class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:'


# 生产环境配置
class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 
            '..', 
            'prod_site.db'
        )
    # 生产环境可修改默认端口
    PORT = int(os.environ.get('FLASK_PORT') or 8000)


# 配置字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


# 初始化上传目录
def init_upload_folder():
    upload_dir = BaseConfig.UPLOAD_FOLDER
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

init_upload_folder()
    
mail = Mail()