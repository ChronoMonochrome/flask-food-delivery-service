# app/__init__.py

import json
import traceback

from datetime import datetime
from os.path import join, realpath, dirname
from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException, NotFound

from .factory import create_app
from .models import db # Import db from models
from .iiko_service import synchronize_iiko_data

app = create_app()

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize CORS
cors = CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"], "allow_headers": "*"}})

# Now import logger, models, and routes as app is fully initialized
from app.logger import logger
from app import models
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem, ProductAddon, ProductRecommendation
from app import routes
from app.api import api_bp # Import the API blueprint

# UTF-8 encoding in API
# Set this configuration BEFORE your Blueprints are registered or initialized
app.json.ensure_ascii = False
app.json.charset = "utf-8" # Ensure charset is explicitly set (though usually default for jsonify)

app.register_blueprint(api_bp, url_prefix='/api') # Register the API blueprint
