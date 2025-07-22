import os
import hashlib
from app import create_app
from app.config import BaseConfig as Config

app = create_app()

def create_admin_key():
    # 检查密钥目录是否存在
    os.makedirs(Config.ADMIN_KEY_FOLDER, exist_ok=True)
    
    key_path = os.path.join(Config.ADMIN_KEY_FOLDER, Config.ADMIN_KEY_FILENAME)
    
    # 如果密钥已存在，询问是否覆盖
    if os.path.exists(key_path):
        response = input("管理员密钥已存在，是否覆盖？(y/n): ")
        if response.lower() != 'y':
            print("已取消操作")
            return
    
    # 生成随机密钥
    import secrets
    key_data = secrets.token_bytes(32)  # 256位随机密钥
    
    # 保存密钥文件
    with open(key_path, 'wb') as f:
        f.write(key_data)
    
    print(f"管理员密钥已创建: {key_path}")
    print("请妥善保管此密钥文件，它是访问管理员面板的凭证")
    print("注意：如果丢失此文件，您将无法访问管理员面板")

if __name__ == '__main__':
    create_admin_key()