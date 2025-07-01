# app/__init__.py

import json

from datetime import datetime
from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv

from .factory import create_app
from .models import db # Import db from models
from .iiko_service import synchronize_iiko_data

app = create_app()

# Initialize SQLAlchemy with the app
db.init_app(app)

# Now import logger, models, and routes as app is fully initialized
from app.logger import logger
from app import models
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem, ProductAddon, ProductRecommendation
from app import routes
from app.api import api_bp # Import the API blueprint


app.register_blueprint(api_bp, url_prefix='/api') # Register the API blueprint

# Create database tables
with app.app_context():
    db.create_all()
    # The synchronize_iiko_data call is removed from here.
    # It will now be handled by the separate scheduler service.
