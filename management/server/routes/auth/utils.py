import jwt
import os
from functools import wraps
from flask import request, jsonify, redirect, url_for

# 从环境变量获取JWT密钥
JWT_SECRET = os.getenv('MANAGEMENT_JWT_SECRET', 'your-secret-key')

def verify_token(token):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "令牌已过期"
    except jwt.InvalidTokenError:
        return False, "无效的令牌"

def jwt_token_required(f):
    """JWT令牌验证装饰器 - 用于API访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"code": 1, "message": "缺少认证令牌"}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # 从环境变量获取JWT密钥
            jwt_secret = os.getenv('MANAGEMENT_JWT_SECRET', 'your-secret-key')
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            request.user = payload
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 1, "message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"code": 1, "message": "无效的令牌"}), 401
    
    return decorated

# 保持token_required别名兼容性
token_required = jwt_token_required 