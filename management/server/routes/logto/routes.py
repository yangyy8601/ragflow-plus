from flask import request, jsonify, redirect, url_for, session
from .. import logto_bp
try:
    from logto import LogtoClient, LogtoConfig, Storage
except ImportError:
    # 如果直接导入失败，使用完整路径
    import sys
    import os
    venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'venv_new', 'lib', 'python3.11', 'site-packages')
    if venv_path not in sys.path:
        sys.path.append(venv_path)
    from logto import LogtoClient, LogtoConfig, Storage

import os
import logging
from .config import LOGTO_ENDPOINT, LOGTO_APP_ID, LOGTO_APP_SECRET
from .utils import token_required
import functools
import json

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
session.verify = False

# 创建Flask会话存储适配器
class FlaskSessionStorage(Storage):
    def __init__(self):
        pass
        
    def get(self, key):
        return session.get(key)
        
    def set(self, key, value):
        if value is None:
            session.pop(key, None)
        else:
            session[key] = value
            
    def delete(self, key):
        session.pop(key, None)

# 获取Logto客户端
def get_logto_client():
    storage = FlaskSessionStorage()
    config = LogtoConfig(
        endpoint=LOGTO_ENDPOINT,
        appId=LOGTO_APP_ID,
        appSecret=LOGTO_APP_SECRET
    )
    return LogtoClient(config, storage=storage)

# 认证装饰器
def authenticated(should_redirect=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logto_client = get_logto_client()
            logger.info(f"认证装饰器")
            if not logto_client.isAuthenticated():
                if should_redirect:
                    return redirect(url_for('logto.sign_in'))
                return jsonify({"code": 1, "message": "未认证"}), 401
            return func(logto_client=logto_client, *args, **kwargs)
        return wrapper
    return decorator

@logto_bp.route('/callback', methods=['GET'])
def callback():
    """处理Logto认证回调"""
    try:
        logger.info(f"处理Logto认证回调")
        logto_client = get_logto_client()
        url = request.url
        logto_client.handleSignInCallback(str(url))
        
        # 根据需要修改重定向目标，例如重定向到前端首页或控制面板
        redirect_target = os.environ.get("LOGTO_REDIRECT_TARGET", "/dashboard")
        logger.info(f"认证成功，重定向到: {redirect_target}")
        return redirect(redirect_target)
    except Exception as e:
        logger.error(f"回调处理错误: {str(e)}")
        return jsonify({"code": 1, "message": f"回调处理错误: {str(e)}"}), 500

@logto_bp.route('/sign-in', methods=['GET'])
def sign_in():
    """登录请求"""
    try:
        logger.info(f"登录请求")
        logto_client = get_logto_client()
        logger.info(f"logto客户端: {logto_client}")
        
        base_url = os.environ.get("LOCAL_HOST_URL", f"{request.scheme}://{request.host}")
        logger.info(f"访问基础地址: {base_url}")
        
        # 获取登录URL并重定向
        redirect_uri = f"{base_url}/api/v1/logto/callback"
        # 修改为同步调用，移除await关键字
        sign_in_url = logto_client.signIn(redirectUri=redirect_uri)
        logger.info(f"sign_in_url: {sign_in_url}")
        return redirect(sign_in_url)
    except Exception as e:
        logger.error(f"登录错误: {str(e)}")
        return jsonify({"code": 1, "message": f"登录错误: {str(e)}"}), 500

@logto_bp.route('/sign-out', methods=['GET'])
def sign_out():
    """登出请求"""
    try:
        logto_client = get_logto_client()
        base_url = os.environ.get("LOCAL_HOST_URL", f"{request.scheme}://{request.host}")
        
        # 获取登出URL并重定向
        sign_out_url = logto_client.signOut(postLogoutRedirectUri=base_url)
        return redirect(sign_out_url)
    except Exception as e:
        logger.error(f"登出错误: {str(e)}")
        return jsonify({"code": 1, "message": f"登出错误: {str(e)}"}), 500

@logto_bp.route('/user-info', methods=['GET'])
@authenticated(should_redirect=False)
def user_info(logto_client=None):
    """获取用户信息"""
    try:
        user_info = logto_client.getUserInfo()
        return jsonify({"code": 0, "data": {"user": user_info}, "message": "获取用户信息成功"})
    except Exception as e:
        return jsonify({"code": 1, "message": f"获取用户信息失败: {str(e)}"}), 500

@logto_bp.route('/protected', methods=['GET'])
@authenticated(should_redirect=False)
def protected(logto_client=None):
    """受保护的API端点示例"""
    try:
        claims = logto_client.getIdTokenClaims()
        return jsonify({
            "code": 0, 
            "data": {
                "message": "这是一个受保护的API端点",
                "user": claims
            }, 
            "message": "请求成功"
        })
    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500 