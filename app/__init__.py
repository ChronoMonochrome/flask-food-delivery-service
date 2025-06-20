# app/__init__.py
from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from .logger import logger

# Initialize the Flask app here, so its root_path is available
app = Flask(__name__,
            template_folder=realpath(join(dirname(__file__), "templates")),
            # Use app.root_path to correctly locate the static folder relative to the app module
            static_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), "static"),
            static_url_path='/'
           )

# Set TEMPLATES_DIR based on the app's resolved template_folder
app.config["TEMPLATES_DIR"] = app.template_folder

logger.info(f"Flask app root_path: {app.root_path}")
logger.info(f"Flask app static_folder configured as: {app.static_folder}")
logger.info(f"Flask app template_folder configured as: {app.template_folder}")


# Use an environment variable for the secret key for better security in production
app.secret_key = os.getenv("SECRET_KEY", "development_secret_key_fallback")

app.session = Session()
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.config['SESSION_FILE_THRESHOLD'] = 1000000
app.session.init_app(app)

# Get database URI from environment variable, which will be provided by docker-compose
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///test.db") # Fallback for local dev without Docker
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import models and routes after app initialization to avoid circular imports
from app import models
from app import routes
