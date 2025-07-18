# app/__init__.py

import json
import traceback

from datetime import datetime
from os.path import join, realpath, dirname
from flask import Flask, current_app, jsonify, request, send_from_directory
from flask_cors import CORS

# Import Migrate
from flask_migrate import Migrate
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException, NotFound

from .factory import create_app
from .models import db # Import db from models
from .iiko_service import synchronize_iiko_data
from .yookassa_service import YookassaService
  
# Determine the absolute path to your React build's *actual static content root*
# This is where Create React App places its JS/CSS/image bundles.
# Inside the container, this is /app/app/static
FRONTEND_BUILD_ROOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Now, set Flask's static_folder to the root of your build output
# as it contains both index.html and the 'assets' folder directly.
app = create_app(static_folder=FRONTEND_BUILD_ROOT_PATH, static_url_path='/static')

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize Flask-Migrate AFTER db.init_app(app)
migrate = Migrate(app, db)

# Initialize CORS
cors = CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"], "allow_headers": "*"}})

# Now import logger, models, and routes as app is fully initialized
# IMPORTANT: Import routes AFTER 'app' is fully configured and extensions initialized
from app.logger import logger
from app import models
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem, ProductAddon, ProductRecommendation

# Import and register the API blueprint
from app.api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# Import and register the main application routes (including static file serving and error handlers)
from app import routes # This import will execute the route decorators on the 'app' instance

# UTF-8 encoding in API
# Set this configuration BEFORE your Blueprints are registered or initialized (api_bp is registered above, this is fine)
app.json.ensure_ascii = False
app.json.charset = "utf-8" # Ensure charset is explicitly set (though usually default for jsonify)

# No more route definitions or error handlers here in __init__.py
# They should all be in app/routes.py