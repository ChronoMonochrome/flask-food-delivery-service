# app/factory.py
from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv
from .logger import logger

def create_app():
    # Initialize the Flask app here, so its root_path is available
    app = Flask(__name__,
                template_folder=realpath(join(dirname(__file__), "templates")),
                # Use app.root_path to correctly locate the static folder relative to the app module
                static_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), "static"),
                static_url_path='/'
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
    app.secret_key = os.getenv("SECRET_KEY", "development_secret_key_fallback")

    app.session = Session()
    app.config['SESSION_PERMANENT'] = os.getenv("SESSION_PERMANENT", True)
    app.config['SESSION_TYPE'] = os.getenv("SESSION_TYPE", 'filesystem')
    # Ensure PERMANENT_SESSION_LIFETIME_SECONDS is an int before using it
    session_lifetime_seconds = int(os.getenv("PERMANENT_SESSION_LIFETIME_SECONDS", 5*3600))
    app.config['PERMANENT_SESSION_LIFETIME_SECONDS'] = session_lifetime_seconds
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=session_lifetime_seconds)
    app.config['SESSION_FILE_THRESHOLD'] = int(os.getenv("SESSION_FILE_THRESHOLD", 1000000))
    app.session.init_app(app)

    # Get database URI from environment variable, which will be provided by docker-compose
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///test.db") # Fallback for local dev without Docker
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Logger configuration
    app.config["DEBUG"] = True #os.getenv("DEBUG", "False").lower() in ('true', '1', 't') # Convert string to boolean
    app.debug = app.config["DEBUG"]
    app.config["LOG_ROTATE_DAYS"] = int(os.getenv("LOG_ROTATE_DAYS", 30))

    return app

