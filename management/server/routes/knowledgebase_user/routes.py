import traceback
from flask import Blueprint, request, jsonify
from .. import knowledgebase_user_bp
from routes.auth.routes import authenticated
from services.knowledgebase_user import KnowledgebaseUserService

@knowledgebase_user_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口，无需认证"""
    return jsonify({
        "code": 0,
        "message": "普通用户知识库服务正常",
        "data": {"status": "OK"}
    })

@knowledgebase_user_bp.route('/knowledgebases', methods=['GET'])
@authenticated(should_redirect=False)
def get_user_knowledgebases(logto_client=None):
    """获取用户关联的知识库列表"""
    try:
        # 获取用户ID
        user_id = request.args.get('user_id')
        if not user_id:
            user_claims = logto_client.getIdTokenClaims()
            user_id = user_claims.sub if user_claims else None
            
        # 调用服务层函数
        result = KnowledgebaseUserService.get_user_knowledgebases(user_id)
        
        return jsonify({
            "code": 0, 
            "data": result, 
            "message": "获取用户知识库列表成功"
        })
        
    except ValueError as e:
        return jsonify({"code": 1, "message": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "code": 1, 
            "message": f"获取用户知识库列表失败: {str(e)}"
        }), 500

@knowledgebase_user_bp.route('/knowledgebases/<string:kb_id>', methods=['GET'])
@authenticated(should_redirect=False)
def get_user_knowledgebase_detail(kb_id, logto_client=None):
    """获取用户关联的单个知识库详情"""
    try:
        # 获取用户ID
        user_id = request.args.get('user_id')
        if not user_id:
            user_claims = logto_client.getIdTokenClaims()
            user_id = user_claims.sub if user_claims else None
            
        # 调用服务层函数
        kb_detail = KnowledgebaseUserService.get_user_knowledgebase_detail(kb_id, user_id)
        
        return jsonify({
            "code": 0, 
            "data": kb_detail, 
            "message": "获取知识库详情成功"
        })
        
    except ValueError as e:
        error_msg = str(e)
        # 根据错误类型返回不同的状态码
        if "无权访问" in error_msg:
            return jsonify({"code": 1, "message": error_msg}), 403
        elif "不存在" in error_msg:
            return jsonify({"code": 1, "message": error_msg}), 404
        else:
            return jsonify({"code": 1, "message": error_msg}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "code": 1, 
            "message": f"获取知识库详情失败: {str(e)}"
        }), 500

@knowledgebase_user_bp.route('/knowledgebases/<string:kb_id>/documents', methods=['GET'])
@authenticated(should_redirect=False)
def get_user_knowledgebase_documents(kb_id, logto_client=None):
    """获取用户关联的知识库的文档列表"""
    try:
        # 获取用户ID
        user_id = request.args.get('user_id')
        if not user_id:
            user_claims = logto_client.getIdTokenClaims()
            user_id = user_claims.sub if user_claims else None
            
        # 获取分页参数
        page = int(request.args.get('currentPage', 1))
        size = int(request.args.get('size', 10))
        name = request.args.get('name', '')

        # 调用服务层函数
        result = KnowledgebaseUserService.get_user_knowledgebase_documents(
            kb_id=kb_id,
            user_id=user_id,
            page=page,
            size=size,
            name=name
        )
        
        return jsonify({
            "code": 0, 
            "data": result, 
            "message": "获取知识库文档列表成功"
        })
        
    except ValueError as e:
        error_msg = str(e)
        # 根据错误类型返回不同的状态码
        if "无权访问" in error_msg:
            return jsonify({"code": 1, "message": error_msg}), 403
        else:
            return jsonify({"code": 1, "message": error_msg}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "code": 1, 
            "message": f"获取知识库文档列表失败: {str(e)}"
        }), 500

@knowledgebase_user_bp.route('/personal-documents', methods=['GET'])
@authenticated(should_redirect=False)
def get_personal_knowledgebase_documents(logto_client=None):
    """获取或创建个人知识库文档
    
    1. 查询用户是否有个人知识库(permission='me')，如果没有则自动创建
    2. 返回知识库关联的文档列表
    """
    try:
        # 获取用户信息
        user_id = None
        user_name = None
        user_email = None
        
        if not request.args.get('user_id'):
            user_claims = logto_client.getIdTokenClaims()
            if user_claims:
                user_id = user_claims.sub
                user_name = getattr(user_claims, 'username', None)
                user_email = getattr(user_claims, 'email', None)
        else:
            user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"code": 1, "message": "用户ID不能为空"}), 400
            
        # 获取分页参数
        page = int(request.args.get('currentPage', 1))
        size = int(request.args.get('size', 10))
        name = request.args.get('name', '')
        
        # 调用服务层函数
        result = KnowledgebaseUserService.get_or_create_personal_knowledgebase_documents(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            page=page,
            size=size,
            name=name
        )
        
        return jsonify({
            "code": 0, 
            "data": result, 
            "message": "获取个人知识库文档成功"
        })
        
    except ValueError as e:
        return jsonify({"code": 1, "message": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "code": 1, 
            "message": f"获取个人知识库文档失败: {str(e)}"
        }), 500 