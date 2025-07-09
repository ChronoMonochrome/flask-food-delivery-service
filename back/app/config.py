import os

class Config:
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    LOG_ROTATE_DAYS = int(os.getenv('LOG_ROTATE_DAYS', 15))
    SCHEDULER = os.getenv('SCHEDULER', 'False').lower() in ('true', '1', 'yes', 'on')

