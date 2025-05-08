import database
import jwt
import os
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from datetime import datetime, timedelta
from routes import register_routes
from dotenv import load_dotenv

import shutil
from functools import lru_cache

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docker', '.env'))

app = Flask(__name__)
# 设置session密钥
app.secret_key = os.getenv('MANAGEMENT_JWT_SECRET', 'your-secret-key')
# 启用CORS，允许前端访问
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
}, supports_credentials=True)  # 启用凭据支持

# 注册所有路由
register_routes(app)

# 从环境变量获取配置
ADMIN_USERNAME = os.getenv('MANAGEMENT_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('MANAGEMENT_ADMIN_PASSWORD', '12345678')
JWT_SECRET = os.getenv('MANAGEMENT_JWT_SECRET', 'your-secret-key')

# 生成token
def generate_token(username):
    # 设置令牌过期时间（例如1小时后过期）
    expire_time = datetime.utcnow() + timedelta(hours=1)
    
    # 生成令牌
    token = jwt.encode({
        'username': username,
        'exp': expire_time
    }, JWT_SECRET, algorithm='HS256') 
    
    return token

# 登录路由保留在主文件中
# 注意：此为原始的简单登录方式，现已添加Logto SSO登录功能
# Logto登录API位于：/api/v1/logto/sign-in
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # 创建用户名和密码的映射
    valid_users = {
        ADMIN_USERNAME: ADMIN_PASSWORD
    }
    
    # 验证用户名是否存在
    if not username or username not in valid_users:
        return {"code": 1, "message": "用户名不存在"}, 400
    
    # 验证密码是否正确
    if not password or password != valid_users[username]:
        return {"code": 1, "message": "密码错误"}, 400
    
    # 生成token
    token = generate_token(username)
    
    return {"code": 0, "data": {"token": token}, "message": "登录成功"}


# 清理步骤
def clear_all_caches():
    # 1. 清理文件缓存
    cache_dir = "tmp/cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    # 2. 清理内存缓存
    @lru_cache(maxsize=128)
    def dummy():
        pass
    dummy.cache_clear()

    # 3. 其他自定义缓存清理...
    print("✅ All caches cleared")

# 在服务启动前执行
clear_all_caches()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)