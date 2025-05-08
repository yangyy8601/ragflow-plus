import mysql.connector
from datetime import datetime
from utils import generate_uuid, encrypt_password
from database import DB_CONFIG
import requests

def get_users_with_pagination(current_page, page_size, username='', email=''):
    """查询用户信息，支持分页和条件筛选"""
    try:
        # 建立数据库连接
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 构建WHERE子句和参数
        where_clauses = []
        params = []
        
        if username:
            where_clauses.append("nickname LIKE %s")
            params.append(f"%{username}%")
        
        if email:
            where_clauses.append("email LIKE %s")
            params.append(f"%{email}%")
        
        # 组合WHERE子句
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总记录数
        count_sql = f"SELECT COUNT(*) as total FROM user WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页偏移量
        offset = (current_page - 1) * page_size
        
        # 执行分页查询
        query = f"""
        SELECT id, nickname, email, create_date, update_date, status, is_superuser
        FROM user
        WHERE {where_sql}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        results = cursor.fetchall()
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        # 格式化结果
        formatted_users = []
        for user in results:
            formatted_users.append({
                "id": user["id"],
                "username": user["nickname"],
                "email": user["email"],
                "createTime": user["create_date"].strftime("%Y-%m-%d %H:%M:%S") if user["create_date"] else "",
                "updateTime": user["update_date"].strftime("%Y-%m-%d %H:%M:%S") if user["update_date"] else "",
            })
        
        return formatted_users, total
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return [], 0

def delete_user(user_id):
    """删除指定ID的用户"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 删除 user 表中的用户记录
        query = "DELETE FROM user WHERE id = %s"
        cursor.execute(query, (user_id,))
        
        # 删除 user_tenant 表中的关联记录
        user_tenant_query = "DELETE FROM user_tenant WHERE user_id = %s"
        cursor.execute(user_tenant_query, (user_id,))

        # 删除 tenant 表中的关联记录
        tenant_query = "DELETE FROM tenant WHERE id = %s"
        cursor.execute(tenant_query, (user_id,))
    
        # 删除 tenant_llm 表中的关联记录
        tenant_llm_query = "DELETE FROM tenant_llm WHERE tenant_id = %s"
        cursor.execute(tenant_llm_query, (user_id,))
    
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"删除用户错误: {err}")
        return False

def create_user(user_data):
    """创建新用户，并加入最早用户的团队，并使用相同的模型配置"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 检查用户表是否为空
        check_users_query = "SELECT COUNT(*) as user_count FROM user"
        cursor.execute(check_users_query)
        user_count = cursor.fetchone()['user_count']
        
        # 如果有用户，则查询最早的tenant和用户配置
        if user_count > 0:
            # 查询最早创建的tenant配置
            query_earliest_tenant = """
            SELECT id, llm_id, embd_id, asr_id, img2txt_id, rerank_id, tts_id, parser_ids, credit
            FROM tenant 
            WHERE create_time = (SELECT MIN(create_time) FROM tenant)
            LIMIT 1
            """
            cursor.execute(query_earliest_tenant)
            earliest_tenant = cursor.fetchone()
            
            # 查询最早创建的用户ID
            query_earliest_user = """
            SELECT id FROM user 
            WHERE create_time = (SELECT MIN(create_time) FROM user)
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()
            
            # 查询最早用户的所有tenant_llm配置
            query_earliest_user_tenant_llms = """
            SELECT llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            FROM tenant_llm 
            WHERE tenant_id = %s
            """
            cursor.execute(query_earliest_user_tenant_llms, (earliest_user['id'],))
            earliest_user_tenant_llms = cursor.fetchall()
        
        # 开始插入
        user_id = generate_uuid()
        # 获取基本信息
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        # 加密密码
        encrypted_password = encrypt_password(password)

        current_datetime = datetime.now()
        create_time = int(current_datetime.timestamp() * 1000) 
        current_date = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

        # 插入用户表
        user_insert_query = """
        INSERT INTO user (
            id, create_time, create_date, update_time, update_date, access_token,
            nickname, password, email, avatar, language, color_schema, timezone,
            last_login_time, is_authenticated, is_active, is_anonymous, login_channel,
            status, is_superuser
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s
        )
        """
        user_data_tuple = (
            user_id, create_time, current_date, create_time, current_date, None,
            username, encrypted_password, email, None, "Chinese", "Bright", "UTC+8 Asia/Shanghai",
            current_date, 1, 1, 0, "password",
            1, 0
        )
        cursor.execute(user_insert_query, user_data_tuple)

        # 插入租户表
        tenant_insert_query = """
        INSERT INTO tenant (
            id, create_time, create_date, update_time, update_date, name,
            public_key, llm_id, embd_id, asr_id, img2txt_id, rerank_id, tts_id,
            parser_ids, credit, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        """

        if user_count > 0:
            # 如果有现有用户，复制其模型配置
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "'s Kingdom",
                None, str(earliest_tenant['llm_id']), str(earliest_tenant['embd_id']), 
                str(earliest_tenant['asr_id']), str(earliest_tenant['img2txt_id']), 
                str(earliest_tenant['rerank_id']), str(earliest_tenant['tts_id']),
                str(earliest_tenant['parser_ids']), str(earliest_tenant['credit']), 1
            )
        else:
            # 如果是第一个用户，模型ID使用空字符串
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "'s Kingdom",
                None, '', '', '', '', '', '',
                '', "1000", 1
            )
        cursor.execute(tenant_insert_query, tenant_data)

        # 插入用户租户关系表（owner角色）
        user_tenant_insert_owner_query = """
        INSERT INTO user_tenant (
            id, create_time, create_date, update_time, update_date, user_id,
            tenant_id, role, invited_by, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """
        user_tenant_data_owner = (
            generate_uuid(), create_time, current_date, create_time, current_date, user_id,
            user_id, "owner", user_id, 1
        )
        cursor.execute(user_tenant_insert_owner_query, user_tenant_data_owner)
        
        # 只有在存在其他用户时，才加入最早用户的团队
        if user_count > 0:
            # 插入用户租户关系表（normal角色）
            user_tenant_insert_normal_query = """
            INSERT INTO user_tenant (
                id, create_time, create_date, update_time, update_date, user_id,
                tenant_id, role, invited_by, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """
            user_tenant_data_normal = (
                generate_uuid(), create_time, current_date, create_time, current_date, user_id,
                earliest_tenant['id'], "normal", earliest_tenant['id'], 1
            )
            cursor.execute(user_tenant_insert_normal_query, user_tenant_data_normal)

            # 为新用户复制最早用户的所有tenant_llm配置
            tenant_llm_insert_query = """
            INSERT INTO tenant_llm (
                create_time, create_date, update_time, update_date, tenant_id,
                llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            # 遍历最早用户的所有tenant_llm配置并复制给新用户
            for tenant_llm in earliest_user_tenant_llms:
                tenant_llm_data = (
                    create_time, current_date, create_time, current_date, user_id,
                    str(tenant_llm['llm_factory']), str(tenant_llm['model_type']), str(tenant_llm['llm_name']),
                    str(tenant_llm['api_key']), str(tenant_llm['api_base']), str(tenant_llm['max_tokens']), 0
                )
                cursor.execute(tenant_llm_insert_query, tenant_llm_data)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"创建用户错误: {err}")
        return False

def update_user(user_id, user_data):
    """更新用户信息"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
        UPDATE user SET nickname = %s WHERE id = %s
        """
        cursor.execute(query, (
            user_data.get("username"),
            user_id
        ))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"更新用户错误: {err}")
        return False

def get_logto_users_list():
    """获取Logto用户列表"""
    try:
        # 1. 获取 access_token
        token_url = "https://www.aiboxcloud.com:3001/oidc/token"
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        token_data = {
            "grant_type": "client_credentials",
            "client_id": "05vsvauzkutwgi2w540zm",
            "client_secret": "ZJsT3qXFGaFVZ3Iz9UGrOOpvrBZvSheO",
            "resource": "https://default.logto.app/api",
            "scope": "all"
        }
        
        token_response = requests.post(token_url, headers=token_headers, data=token_data)
        
        if token_response.status_code != 200:
            return {"error": f"获取token失败: {token_response.text}"}, 0
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return {"error": "无法获取access_token"}, 0
        
        # 2. 使用获取到的token请求用户列表
        users_url = "https://www.aiboxcloud.com:3001/api/users"
        users_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        users_response = requests.get(users_url, headers=users_headers)
        
        if users_response.status_code != 200:
            return {"error": f"获取用户列表失败: {users_response.text}"}, 0
        
        users = users_response.json()
        
        # 格式化用户数据以符合前端需要
        formatted_users = []
        for user in users:
            formatted_users.append({
                "id": user.get("id", ""),
                "username": user.get("username", "") or user.get("name", ""),
                "primaryEmail": user.get("primaryEmail", ""),
                "primaryPhone": user.get("primaryPhone", ""),
                "name": user.get("name", ""),
                "avatar": user.get("avatar", ""),
                "lastSignInAt": user.get("lastSignInAt", ""),
                "createdAt": user.get("createdAt", ""),
                "updatedAt": user.get("updatedAt", ""),
                "isSuspended": user.get("isSuspended", False),
                "hasPassword": user.get("hasPassword", False)
            })
        
        return formatted_users, len(formatted_users)
        
    except Exception as e:
        print(f"获取Logto用户列表错误: {str(e)}")
        return {"error": f"获取用户列表失败: {str(e)}"}, 0