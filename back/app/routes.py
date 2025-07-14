# app/routes.py
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Import the 'app' instance from __init__.py
from app import app
from flask import send_from_directory, request, jsonify, current_app
import os
from .logger import logger
from werkzeug.exceptions import HTTPException, NotFound
import traceback
import urllib
import json

# Get the absolute path to the static folder directly from the app configuration.
# This ensures consistency with how Flask itself is configured to serve static files.
STATIC_FOLDER = app.static_folder

logger.info(f"app.static_folder is: {STATIC_FOLDER}")

# These were defined in __init__.py but are logically part of routing and static serving.
# Determine the absolute path to your React build's *actual static content root*
REACT_STATIC_ROOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'static')

# This is where index.html, favicon.ico, manifest.json are.
FRONTEND_BUILD_ROOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


# --- Static File Serving for React SPA ---

# 1. Serve index.html for the root path
@app.route('/')
def serve_react_app():
    current_app.logger.info(f"Serving index.html for / from host {request.remote_addr}")
    # Assign the result of send_from_directory to 'response' first
    response = send_from_directory(FRONTEND_BUILD_ROOT_PATH, 'index.html')

    # Add cache-control headers to prevent caching of index.html
    # This tells browsers/proxies to always revalidate or not cache at all.
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# 2. Serve root-level static assets (favicon.ico, manifest.json)
#    and handle client-side routing fallback.
#    This route specifically handles paths that *do not* start with /static/.
@app.route('/<path:path>')
def serve_root_assets_or_spa_fallback(path):
    current_app.logger.info(f"Request for /{path} (not / or /api/).")

    # If the path actually starts with 'static/', it should be handled by Flask's
    # built-in static file server. If it's hitting this route, it's an issue.
    # We explicitly raise NotFound to avoid serving index.html for what should be a static file.
    if path.startswith('static/'):
        current_app.logger.error(f"Logic error: Static path /{path} caught by SPA fallback. Should be handled by Flask's default static handler.")
        raise NotFound() # This should ideally never be hit if Flask's default static handler works.

    # For other paths (like favicon.ico, manifest.json, or client-side routes like /about)
    try:
        current_app.logger.info(f"Attempting to serve root-level static file: {path} from {FRONTEND_BUILD_ROOT_PATH}")
        return send_from_directory(FRONTEND_BUILD_ROOT_PATH, path)
    except NotFound:
        current_app.logger.info(f"File not found: {path}. Serving index.html for SPA fallback.")
        return send_from_directory(FRONTEND_BUILD_ROOT_PATH, 'index.html')


# --- Error Handlers ---

@app.errorhandler(404)
def not_found_error(error):
    # For API endpoints not found, return JSON error
    if request.path.startswith('/api/'):
        current_app.logger.warning(f"API 404 for path: {request.path}")
        return jsonify(message="API Endpoint Not Found", status=404), 404

    # If the request is for a specific static file (e.g., /static/js/main.js),
    # and it genuinely wasn't found, return a proper 404.
    # This is important for browsers so they don't try to interpret index.html as JS/CSS.
    if request.path.startswith('/static/'):
        current_app.logger.warning(f"Actual static file 404 for path: {request.path}")
        return jsonify(message="Static File Not Found", status=404), 404

    # For all other non-API and non-static 404s, let React Router handle it (serve index.html).
    current_app.logger.info(f"Serving index.html as SPA fallback for path: {request.path} (general 404).")
    return send_from_directory(FRONTEND_BUILD_ROOT_PATH, 'index.html')


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e

    current_app.logger.error(f"Internal Server Error: {e}", exc_info=True)
    return jsonify(message="An unexpected error occurred at the application level.", status=500, error_type=type(e).__name__, details=traceback.format_exc()), 500

import os
import hashlib
import hmac

TELEGRAM_TOKEN =  os.getenv("TELEGRAM_TOKEN")

def validate_telegram_init_data(init_data: str, bot_token: str) -> bool: # Renamed parameter for clarity
    """
    Validates the initData received from the Telegram Web App.
    Based on Telegram's documentation: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data:
        current_app.logger.info("Validation Debug: init_data is empty.") # Added debug print
        return False

    # 1. Parse the query string parameters from init_data
    params = {}
    received_hash = None # Initialize received_hash as None

    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            if key == 'hash':
                received_hash = value # Store the raw hash value for comparison
            else:
                # !!! CRUCIAL CHANGE HERE: URL-decode the value before storing !!!
                # Use unquote_plus because Telegram's initData can use '+' for spaces.
                params[key] = urllib.parse.unquote_plus(value)

    if received_hash is None: # Check if hash was actually found
        current_app.logger.info("Validation Debug: 'hash' parameter not found in init_data.") # Added debug print
        return False

    # 2. Sort the parameters by key and concatenate them
    data_check_string_parts = []
    sorted_keys = sorted(params.keys())
    for key in sorted_keys:
        data_check_string_parts.append(f"{key}={params[key]}")
    data_check_string = "\n".join(data_check_string_parts)

    current_app.logger.info(f"Validation Debug: data_check_string = '{data_check_string}'") # Added debug print

    # 3. Create a secret key using HMAC-SHA256
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()

    current_app.logger.info(f"Validation Debug: secret_key (hex) = {secret_key.hex()}") # Added debug print

    # 4. Hash the data_check_string using the secret key
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    current_app.logger.info(f"Validation Debug: Calculated hash = '{calculated_hash}'") # Added debug print
    current_app.logger.info(f"Validation Debug: Received hash   = '{received_hash}'")     # Added debug print

    # 5. Compare the calculated hash with the received hash
    return calculated_hash == received_hash

@app.route('/api/telegram-init', methods=['POST'])
def handle_telegram_init():
    data = request.get_json()
    init_data_raw = data.get('initData')

    if not init_data_raw:
        return jsonify({"status": "error", "message": "No initData provided"}), 400

    if validate_telegram_init_data(init_data_raw, TELEGRAM_TOKEN):
        # Extract user data from init_data_raw (it will be URL-encoded)
        # You'll likely want to parse 'user' from init_data_raw if present
        # Example of parsing a single parameter (you might need a more robust parser)
        user_data_str = None
        for pair in init_data_raw.split('&'):
            if pair.startswith('user='):
                user_data_str = pair.split('=', 1)[1]
                break

        user_info = {}
        if user_data_str:
            try:
                # URL decode and then JSON parse
                import urllib.parse
                decoded_user_data_str = urllib.parse.unquote(user_data_str)
                user_info = json.loads(decoded_user_data_str)
            except (json.JSONDecodeError) as e:
                app.logger.error(f"Error decoding or parsing user data: {e}")
                user_info = {"error": "Could not parse user data"}

        app.logger.info(f"Telegram Web App init data validated successfully. User: {user_info.get('id')}")
        return jsonify({
            "status": "success",
            "message": "Telegram init data validated",
            "user": user_info
        })
    else:
        app.logger.warning("Invalid Telegram Web App init data received.")
        return jsonify({"status": "error", "message": "Invalid Telegram init data"}), 403

