import os
from datetime import timedelta

class Config:
    # DB
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///test.db')
    MYSQL_ROOT_PASSWORD = os.getenv('MYSQL_ROOT_PASSWORD', 'your_root_password')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'mydatabase')
    MYSQL_USER = os.getenv('MYSQL_USER', 'user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'your_db_password')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL # Flask-SQLAlchemy uses this
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask secret key
    SECRET_KEY = os.getenv('SECRET_KEY', 'development_secret_key_fallback')

    # Logger
    SCHEDULER = os.getenv('SCHEDULER', 'False').lower() in ('true', '1', 'yes', 'on')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    LOG_ROTATE_DAYS = int(os.getenv('LOG_ROTATE_DAYS', 30))

    # Session
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'True').lower() in ('true', '1', 'yes', 'on')
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    PERMANENT_SESSION_LIFETIME_SECONDS = int(os.getenv('PERMANENT_SESSION_LIFETIME_SECONDS', 18000))
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=PERMANENT_SESSION_LIFETIME_SECONDS)
    SESSION_FILE_THRESHOLD = int(os.getenv('SESSION_FILE_THRESHOLD', 1000000))

    # IIKO API
    IIKO_API_URL = os.getenv('IIKO_API_URL', 'https://api-ru.iiko.services')
    IIKO_API_TOKEN = os.getenv('IIKO_API_TOKEN', 'iiko_token')
    IIKO_CACHE_EXPIRATION_MINUTES = int(os.getenv('IIKO_CACHE_EXPIRATION_MINUTES', -1))

    # TG
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'token')
    WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://mandarin.dev.routeam.ru/')

    # Yookassa
    YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '12345')
    YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', 'your_yookassa_secret_key')
    APP_PUBLIC_URL = os.getenv('APP_PUBLIC_URL', 'https://mandarin.dev.routeam.ru')
    FRONTEND_ORDER_RETURN_URL = os.getenv('FRONTEND_ORDER_RETURN_URL', 'https://t.me/Mandarin_Cafe_Bot')

    # Flask JSON configuration
    JSON_AS_ASCII = False
    JSON_CHARSET = "utf-8"

    # No IP check fails for dev server
    DEV_NO_IP_ADDRESS_CHECK_FAIL = (WEB_APP_URL == "https://mytestapp001.ru")
