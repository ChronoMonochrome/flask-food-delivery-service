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
