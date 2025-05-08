import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'docker', '.env'))

# Logto配置
LOGTO_ENDPOINT = os.getenv('LOGTO_ENDPOINT', 'https://www.aiboxcloud.com:3001')
LOGTO_APP_ID = os.getenv('LOGTO_APP_ID', 'q3m5x3770y0nld8zgxozp')
LOGTO_APP_SECRET = os.getenv('LOGTO_APP_SECRET', 'Sb2QdXxpGkKdH4L9znmazz0L94PQ4fNr')
LOGTO_REDIRECT_URI = os.getenv('LOGTO_REDIRECT_URI', 'http://localhost:5000/api/v1/logto/callback')
LOGTO_SCOPES = os.getenv('LOGTO_SCOPES', 'openid profile email').split() 