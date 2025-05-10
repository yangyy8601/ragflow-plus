import traceback
import mysql.connector
from database import DB_CONFIG
from utils import generate_uuid
from datetime import datetime
import json

class KnowledgebaseUserService:
    """用户知识库服务类"""
    
    @classmethod
    def _get_db_connection(cls):
        """创建数据库连接"""
        return mysql.connector.connect(**DB_CONFIG)
    
    @classmethod
    def get_user_knowledgebases(cls, user_id):
        """获取用户关联的知识库列表"""
        try:
            if not user_id:
                raise ValueError("用户ID不能为空")
                
            # 连接数据库
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 构建查询
            query = """
                SELECT 
                    kb.id as kb_id, 
                    kb.name, 
                    kb.description, 
                    kb.language,
                    kb.create_date, 
                    kb.update_date,
                    kb.doc_num,
                    kb.token_num,
                    kb.chunk_num,
                    kr.scope,
                    kr.id as role_id
                FROM knowledgebase_role kr
                JOIN knowledgebase kb ON kr.knowledge_id = kb.id
                WHERE kr.user_id = %s
                AND kb.permission = 'team'
            """
            
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            
            # 处理结果
            knowledgebases = []
            for result in results:
                # 转换scope (0: 只读, 1: 读写)
                result['scope_name'] = '读写' if result.get('scope') == '1' else '只读'
                
                # 添加到结果列表
                knowledgebases.append(result)
            
            cursor.close()
            conn.close()
            
            return {
                "list": knowledgebases,
                "total": len(knowledgebases)
            }
            
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"获取用户知识库列表失败: {str(e)}")
    
    @classmethod
    def get_user_knowledgebase_detail(cls, kb_id, user_id):
        """获取用户关联的单个知识库详情"""
        try:
            if not user_id:
                raise ValueError("用户ID不能为空")
                
            # 连接数据库
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 首先验证用户是否有权限访问该知识库
            query_permission = """
                SELECT id, scope
                FROM knowledgebase_role
                WHERE user_id = %s AND knowledge_id = %s
            """
            cursor.execute(query_permission, (user_id, kb_id))
            permission = cursor.fetchone()
            
            if not permission:
                cursor.close()
                conn.close()
                raise ValueError("无权访问该知识库")
            
            # 获取知识库详情
            query_kb = """
                SELECT 
                    kb.id as kb_id, 
                    kb.name, 
                    kb.description, 
                    kb.language,
                    kb.create_date, 
                    kb.update_date,
                    kb.doc_num,
                    kb.token_num,
                    kb.chunk_num,
                    kb.similarity_threshold,
                    kb.vector_similarity_weight,
                    kb.parser_id,
                    kb.parser_config
                FROM knowledgebase kb
                WHERE kb.id = %s
            """
            cursor.execute(query_kb, (kb_id,))
            kb_detail = cursor.fetchone()
            
            if not kb_detail:
                cursor.close()
                conn.close()
                raise ValueError("知识库不存在")
            
            # 添加权限信息
            kb_detail['scope'] = permission['scope']
            kb_detail['scope_name'] = '读写' if permission['scope'] == '1' else '只读'
            kb_detail['role_id'] = permission['id']
            
            cursor.close()
            conn.close()
            
            return kb_detail
            
        except ValueError as e:
            # 对于已知的验证错误，直接向上抛出
            raise
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"获取知识库详情失败: {str(e)}")
    
    @classmethod
    def get_user_knowledgebase_documents(cls, kb_id, user_id, page=1, size=10, name=''):
        """获取用户关联的知识库的文档列表"""
        try:
            if not user_id:
                raise ValueError("用户ID不能为空")
                
            # 连接数据库
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 首先验证用户是否有权限访问该知识库
            query_permission = """
                SELECT scope
                FROM knowledgebase_role
                WHERE user_id = %s AND knowledge_id = %s
            """
            cursor.execute(query_permission, (user_id, kb_id))
            permission = cursor.fetchone()
            
            if not permission:
                cursor.close()
                conn.close()
                raise ValueError("无权访问该知识库")
            
            # 构建查询文档的 SQL
            query_docs = """
                SELECT 
                    *
                FROM document kd
                WHERE kd.kb_id = %s
            """
            
            params = [kb_id]
            
            if name:
                query_docs += " AND kd.name LIKE %s"
                params.append(f"%{name}%")
                
            # 添加分页
            query_docs += " LIMIT %s OFFSET %s"
            params.extend([size, (page-1)*size])
            
            cursor.execute(query_docs, params)
            documents = cursor.fetchall()
            
            # 获取文档总数
            count_query = "SELECT COUNT(*) as total FROM document WHERE kb_id = %s"
            count_params = [kb_id]
            
            if name:
                count_query += " AND file_name LIKE %s"
                count_params.append(f"%{name}%")
                
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            # 处理结果，转换状态等
            for doc in documents:
                # 文档状态转换
                status_code = doc.get('status', '0')
                status_map = {
                    '0': '待处理',
                    '1': '处理中',
                    '2': '已完成',
                    '3': '失败'
                }
                doc['status_name'] = status_map.get(status_code, '未知状态')
                
                # 处理文件大小 (转换为KB或MB)
                if 'file_size' in doc and doc['file_size'] is not None:
                    size_in_bytes = int(doc['file_size'])
                    if size_in_bytes < 1024 * 1024:  # 小于1MB
                        doc['size_formatted'] = f"{round(size_in_bytes/1024, 2)}KB"
                    else:
                        doc['size_formatted'] = f"{round(size_in_bytes/(1024*1024), 2)}MB"
                else:
                    doc['size_formatted'] = "未知大小"
            
            return {
                "list": documents,
                "total": total
            }
            
        except ValueError as e:
            # 对于已知的验证错误，直接向上抛出
            raise 
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"获取知识库文档列表失败: {str(e)}")
            
    @classmethod
    def get_or_create_personal_knowledgebase_documents(cls, user_id, user_name='', user_email='', user_phone='', page=1, size=10, name=''):
        """获取或创建个人知识库文档
        
        1. 查询是否存在个人知识库: knowledgebase_role表中user_id为本人id, scope=1,且knowledgebase表的permission='me'
        2. 若存在，查询知识库关联的文档并返回
        3. 若不存在，创建个人知识库并返回空文档列表
        """
        try:
            if not user_id:
                raise ValueError("用户ID不能为空")
                
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 1. 查询是否存在个人知识库
            query_personal_kb = """
                SELECT 
                    kb.id as kb_id, 
                    kb.name, 
                    kb.description,
                    kb.permission
                FROM knowledgebase_role kr
                JOIN knowledgebase kb ON kr.knowledge_id = kb.id
                WHERE kr.user_id = %s 
                AND kr.scope = '1' 
                AND kb.permission = 'me'
                LIMIT 1
            """
            cursor.execute(query_personal_kb, (user_id,))
            personal_kb = cursor.fetchone()
            
            kb_id = None
            is_new_created = False
            
            # 2. 如果不存在个人知识库，创建一个
            if not personal_kb:
                try:
                    kb_id = cls._create_personal_knowledgebase(user_id, user_name, user_email, user_phone)
                    is_new_created = True
                except Exception as e:
                    cursor.close()
                    conn.close()
                    raise Exception(f"创建个人知识库失败: {str(e)}")
            else:
                kb_id = personal_kb['kb_id']
            
            # 如果是新创建的知识库，返回空文档列表
            if is_new_created:
                cursor.close()
                conn.close()
                return {
                    "kb_id": kb_id,
                    "is_new_created": True,
                    "documents": {
                        "list": [],
                        "total": 0
                    }
                }
            
            # 3. 查询个人知识库的文档
            query_docs = """
                SELECT 
                    *
                FROM document d
                WHERE d.kb_id = %s
            """
            
            params = [kb_id]
            
            if name:
                query_docs += " AND d.file_name LIKE %s"
                params.append(f"%{name}%")
                
            # 添加分页
            query_docs += " LIMIT %s OFFSET %s"
            params.extend([size, (page-1)*size])
            
            cursor.execute(query_docs, params)
            documents = cursor.fetchall()
            
            # 获取文档总数
            count_query = "SELECT COUNT(*) as total FROM document WHERE kb_id = %s"
            count_params = [kb_id]
            
            if name:
                count_query += " AND file_name LIKE %s"
                count_params.append(f"%{name}%")
                
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            # 处理结果，转换状态等
            for doc in documents:
                # 文档状态转换
                status_code = doc.get('status', '0')
                status_map = {
                    '0': '待处理',
                    '1': '处理中',
                    '2': '已完成',
                    '3': '失败'
                }
                doc['status_name'] = status_map.get(status_code, '未知状态')
                
                # 处理文件大小 (转换为KB或MB)
                if 'size' in doc and doc['size'] is not None:
                    size_in_bytes = int(doc['size'])
                    if size_in_bytes < 1024 * 1024:  # 小于1MB
                        doc['size_formatted'] = f"{round(size_in_bytes/1024, 2)}KB"
                    else:
                        doc['size_formatted'] = f"{round(size_in_bytes/(1024*1024), 2)}MB"
                elif 'file_size' in doc and doc['file_size'] is not None:
                    size_in_bytes = int(doc['file_size'])
                    if size_in_bytes < 1024 * 1024:  # 小于1MB
                        doc['size_formatted'] = f"{round(size_in_bytes/1024, 2)}KB"
                    else:
                        doc['size_formatted'] = f"{round(size_in_bytes/(1024*1024), 2)}MB"
                else:
                    doc['size_formatted'] = "未知大小"
            
            return {
                "kb_id": kb_id,
                "is_new_created": False,
                "documents": {
                    "list": documents,
                    "total": total
                }
            }
            
        except ValueError as e:
            raise
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"获取个人知识库文档失败: {str(e)}")
    
    @classmethod
    def _create_personal_knowledgebase(cls, user_id, user_name='', user_email='', user_phone=''):
        """创建个人知识库
        
        创建一个个人知识库，并将其与用户关联。
        """
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 准备时间数据
            current_time = datetime.now()
            create_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
            create_time = int(current_time.timestamp() * 1000)  # 毫秒级时间戳
            
            # 生成新知识库ID
            kb_id = generate_uuid()
            
            # 设置知识库名称
            kb_name = f"{user_name or user_id}的个人知识库"
            
            # 获取embedding模型ID
            dynamic_embd_id = None
            default_embd_id = 'bge-m3___VLLM@VLLM'  # 默认值
            try:
                query_embedding_model = """
                    SELECT llm_name
                    FROM tenant_llm
                    WHERE model_type = 'embedding'
                    ORDER BY create_time ASC
                    LIMIT 1
                """
                cursor.execute(query_embedding_model)
                embedding_model = cursor.fetchone()

                if embedding_model and embedding_model.get('llm_name'):
                    dynamic_embd_id = embedding_model['llm_name']
                else:
                    dynamic_embd_id = default_embd_id
            except Exception as e:
                dynamic_embd_id = default_embd_id
                print(f"查询embedding模型失败: {str(e)}，使用默认值: {dynamic_embd_id}")
                traceback.print_exc()
            
            # 默认解析器配置
            default_parser_config = json.dumps({
                "layout_recognize": "DeepDOC", 
                "chunk_token_num": 512, 
                "delimiter": "\n!?;。；！？", 
                "auto_keywords": 0, 
                "auto_questions": 0, 
                "html4excel": False, 
                "raptor": {"use_raptor": False}, 
                "graphrag": {"use_graphrag": False}
            })
            
            # 创建知识库
            query_create_kb = """
                INSERT INTO knowledgebase (
                    id, create_time, create_date, update_time, update_date,
                    avatar, tenant_id, name, language, description,
                    embd_id, permission, created_by, doc_num, token_num,
                    chunk_num, similarity_threshold, vector_similarity_weight, parser_id, parser_config,
                    pagerank, status
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s
                )
            """
            
            # 设置参数
            kb_params = (
                kb_id, create_time, create_date, create_time, create_date,  # ID和时间
                None, user_id, kb_name, 'Chinese', '个人知识库',  # 头像到描述
                dynamic_embd_id, 'me', user_id, 0, 0,  # embedding到token数
                0, 0.7, 0.3, 'naive', default_parser_config,  # chunk数到解析器配置
                0, '1'  # pagerank和状态
            )
            
            cursor.execute(query_create_kb, kb_params)
            
            # 创建用户与知识库的关联关系
            role_id = generate_uuid()
            query_create_role = """
                INSERT INTO knowledgebase_role (
                    id, knowledge_id, user_id, user_name, user_phone, user_email, scope, 
                    create_time, create_date, update_time, update_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s
                )
            """
            
            role_params = (
                role_id, kb_id, user_id, user_name, user_phone, user_email, '1',
                create_time, create_date, create_time, create_date
            )
            
            cursor.execute(query_create_role, role_params)
            
            # 提交事务
            conn.commit()
            
            return kb_id
        except Exception as e:
            if conn:
                conn.rollback()
            traceback.print_exc()
            raise Exception(f"创建个人知识库失败: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close() 