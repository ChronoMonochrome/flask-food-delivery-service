# app/__init__.py

from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv

from .factory import create_app
app = create_app()

# Now import logger, models, and routes as app is fully initialized
from app.logger import logger
from app import models
from app import routes

