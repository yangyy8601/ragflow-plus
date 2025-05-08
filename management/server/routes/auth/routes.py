from flask import request, jsonify, redirect, url_for, session
from .. import auth_bp
from logto import LogtoClient, LogtoConfig, Storage
import os
import logging
from .config import LOGTO_ENDPOINT, LOGTO_APP_ID, LOGTO_APP_SECRET
from .utils import token_required
import functools
import json
from typing import Union

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# 创建Flask会话存储适配器
class FlaskSessionStorage(Storage):
    def get(self, key: str) -> Union[str, None]:
        return session.get(key, None)

    def set(self, key: str, value: Union[str, None]) -> None:
        session[key] = value

    def delete(self, key: str) -> None:
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
            if not logto_client.isAuthenticated():
                if should_redirect:
                    return redirect('/api/v1/auth/sign-in')
                return jsonify({"code": 1, "message": "未认证"}), 401
            return func(logto_client=logto_client, *args, **kwargs)
        return wrapper
    
        # async def wrapper(*args, **kwargs):
        #     logto_client = get_logto_client()
        #     if logto_client.isAuthenticated() is False:
        #         if shouldRedirect:
        #             return redirect("/sign-in")
        #         return jsonify({"error": "Not authenticated"}), 401

        #     # Store user info in Flask application context
        #     g.user = (
        #         await client.fetchUserInfo()
        #         if fetchUserInfo
        #         else client.getIdTokenClaims()
        #     )
        #     return await func(*args, **kwargs)

        # return wrapper

    return decorator

@auth_bp.route('/callback', methods=['GET'])
def callback():
    """处理Logto认证回调"""
    try:
        logto_client = get_logto_client()
        url = request.url
        logger.info(f"处理Logto认证回调={request.url}")
        logto_client.handleSignInCallback(str(url))
        # return redirect('http://192.168.8.44:5173')
        return redirect('/')
    except Exception as e:
        logger.error(f"回调处理错误: {str(e)}")
        return jsonify({"code": 1, "message": f"回调处理错误: {str(e)}"}), 500

@auth_bp.route('/sign-in', methods=['GET'])
async def sign_in():
    """登录请求"""
    try:
        logger.info(f"登录请求")
        logto_client = get_logto_client()
        logger.info(logto_client)

        base_url = os.environ.get("LOCAL_HOST_URL", f"{request.scheme}://{request.host}")
        logger.info(f"访问基础地址: {base_url}")
        
        # 获取登录URL并重定向
        redirect_uri = f"{base_url}/api/v1/auth/callback"
        sign_in_url = await logto_client.signIn(redirectUri=redirect_uri)
        logger.info(f"sign_in_url====: {sign_in_url}")

        return redirect(sign_in_url)
        # return jsonify({"code": 0, "data": {"sign_in_url": sign_in_url}, "message": "登录成功"})
    except Exception as e:
        logger.error(f"登录错误: {str(e)}")
        return jsonify({"code": 1, "message": f"登录错误: {str(e)}"}), 500

@auth_bp.route('/sign-out', methods=['GET'])
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

@auth_bp.route('/user-info', methods=['GET'])
@authenticated(should_redirect=True)
def user_info(logto_client=None):
    """获取用户信息"""
    try:
        logto_client = get_logto_client()
        user_info = logto_client.getUserInfo()
        return jsonify({"code": 0, "data": {"user": user_info}, "message": "获取用户信息成功"})
    except Exception as e:
        return jsonify({"code": 1, "message": f"获取用户信息失败: {str(e)}"}), 500

@auth_bp.route('/protected', methods=['GET'])
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

@auth_bp.route('/logto-users', methods=['GET'])
# @authenticated(should_redirect=False)  # 使用认证装饰器确保只有已登录用户可访问
def get_logto_users(logto_client=None):
    """获取Logto用户列表"""
    try:
        from services.users.service import get_logto_users_list
        
        users, total = get_logto_users_list()
        
        if isinstance(users, dict) and "error" in users:
            return jsonify({
                "code": 1,
                "message": users["error"]
            }), 500
        
        return jsonify({
            "code": 0,
            "data": {
                "list": users,
                "total": total
            },
            "message": "获取Logto用户列表成功"
        })
    except Exception as e:
        logger.error(f"获取Logto用户列表错误: {str(e)}")
        return jsonify({
            "code": 1,
            "message": f"获取Logto用户列表失败: {str(e)}"
        }), 500