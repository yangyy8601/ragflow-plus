# 远程服务连接配置

此目录包含管理后端服务的脚本和工具，已经修改为支持连接远程服务器上的Docker容器。

## 主要修改

1. 添加了远程服务器支持，通过修改 `database.py` 中的配置：
   - 添加了 `REMOTE_SERVER` 变量指向远程服务器（当前为192.168.6.152）
   - 添加了 `USE_REMOTE` 标志来控制是使用远程还是本地服务

2. 统一使用 `database.py` 中的连接函数和配置：
   - 所有脚本现在都从 `database.py` 导入连接函数和配置
   - 避免了重复代码和配置不一致问题

## 如何使用

1. 配置远程服务器连接：
   - 打开 `database.py` 文件
   - 修改 `REMOTE_SERVER` 变量为目标服务器IP地址
   - 设置 `USE_REMOTE = True` 以连接远程服务器，或 `False` 使用本地

2. 测试连接：
   ```bash
   python database.py
   ```
   这将测试与MySQL、MinIO和Elasticsearch的连接

3. 查看数据库表：
   ```bash
   python check_tables.py
   ```

4. 查看MinIO存储桶和文档：
   ```bash
   python minio_test.py
   ```

5. 获取图片URL：
   ```bash
   python get_minio_image_url.py --list_buckets
   python get_minio_image_url.py --kb_id <知识库ID> --list
   ```

## 注意事项

- 确保远程服务器防火墙允许连接到相关端口（MySQL、MinIO、Elasticsearch）
- 确保环境变量文件 `../../docker/.env` 存在且包含正确的凭据
- 如果远程服务器使用非标准端口，请在环境变量文件中正确设置 