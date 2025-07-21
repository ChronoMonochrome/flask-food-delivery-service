# app/factory.py
from os.path import join, realpath, dirname
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
# from flask_session import Session # Removed, will be initialized in __init__.py
from datetime import timedelta
import os
from dotenv import load_dotenv
from .logger import logger

def create_app(static_folder: str = "", static_url_path: str = ""):
    # Initialize the Flask app here, so its root_path is available
    app = Flask(__name__,
                template_folder=realpath(join(dirname(__file__), "templates")),
                # Use app.root_path to correctly locate the static folder relative to the app module
                static_folder=static_folder,
                static_url_path=static_url_path
               )

    # Configure ProxyFix
    # This tells Flask to trust the X-Forwarded-For, X-Forwarded-Proto,
    # and X-Forwarded-Host headers.
    # num_proxies=1 if Nginx is the only proxy directly in front of Flask.
    # If you have multiple layers (e.g., Load Balancer -> Nginx -> Flask),
    # you might need to increase num_proxies accordingly.
    # Based on your docker-compose, it's just Nginx -> Flask, so 1 is correct.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
    )

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load environment variables
    if os.path.exists(os.path.join(BASE_DIR, '.env.local')):
        load_dotenv(os.path.join(BASE_DIR, '.env.local'))
        logger.info(f"Loaded env from .env.local")
    else:
        load_dotenv(os.path.join(BASE_DIR, '.env'))
        logger.info(f"Loaded env from .env")

    # Set TEMPLATES_DIR based on the app's resolved template_folder
    app.config["TEMPLATES_DIR"] = app.template_folder

    # Use an environment variable for the secret key for better security in production
    # This remains here as it's a direct assignment to app.secret_key, not app.config['SECRET_KEY']
    app.secret_key = os.getenv("SECRET_KEY", "development_secret_key_fallback")

    # Session initialization moved to __init__.py after config is loaded
    # app.session = Session()
    # app.config['SESSION_PERMANENT'] = os.getenv("SESSION_PERMANENT", True)
    # app.config['SESSION_TYPE'] = os.getenv("SESSION_TYPE", 'filesystem')
    # session_lifetime_seconds = int(os.getenv("PERMANENT_SESSION_LIFETIME_SECONDS", 5*3600))
    # app.config['PERMANENT_SESSION_LIFETIME_SECONDS'] = session_lifetime_seconds
    # app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=session_lifetime_seconds)
    # app.config['SESSION_FILE_THRESHOLD'] = int(os.getenv("SESSION_FILE_THRESHOLD", 1000000))
    # app.session.init_app(app)

    # Database and Logger configurations are now loaded from app.config.from_object(Config)
    # app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///test.db")
    # app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # app.config["DEBUG"] = True
    # app.debug = app.config["DEBUG"]
    # app.config["LOG_ROTATE_DAYS"] = int(os.getenv("LOG_ROTATE_DAYS", 30))

    return app
