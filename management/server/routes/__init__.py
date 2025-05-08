# 路由模块初始化
from flask import Blueprint

# 创建蓝图
users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')
teams_bp = Blueprint('teams', __name__, url_prefix='/api/v1/teams')
tenants_bp = Blueprint('tenants', __name__, url_prefix='/api/v1/tenants')
files_bp = Blueprint('files', __name__, url_prefix='/api/v1/files')
knowledgebase_bp = Blueprint('knowledgebases', __name__, url_prefix='/api/v1/knowledgebases')
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')
# 导入路由
from .users.routes import *
from .teams.routes import *
from .tenants.routes import *
from .files.routes import *
from .knowledgebases.routes import *
from .auth.routes import *


def register_routes(app):
    """注册所有路由蓝图到应用"""
    app.register_blueprint(users_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(knowledgebase_bp)
    app.register_blueprint(auth_bp)
