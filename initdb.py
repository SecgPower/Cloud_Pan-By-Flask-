from app import create_app, db
from app.models import User, File  # 导入新添加的File模型
import os

# 创建应用实例
app = create_app()

# 在应用上下文中创建数据库表和上传目录
with app.app_context():
    # 创建所有模型对应的表
    db.create_all()
    
    # 创建文件上传目录
    upload_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    print("数据库表和上传目录创建成功！")
    