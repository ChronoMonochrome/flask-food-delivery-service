# app/routes.py
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from app import app
from flask import send_from_directory, request
import os
from .logger import logger

# Get the absolute path to the static folder directly from the app configuration.
# This ensures consistency with how Flask itself is configured to serve static files.
STATIC_FOLDER = app.static_folder

logger.info(f"app.static_folder is: {STATIC_FOLDER}")

@app.route("/")
def home():
    logger.info(f"Request to / from host {request.remote_addr}. Attempting to serve: {os.path.join(STATIC_FOLDER, 'index.html')}")
    # Serve index.html from the static folder
    return send_from_directory(STATIC_FOLDER, 'index.html')

@app.route("/assets/<path:path>")
def assets_dir(path):
    logger.info(f"Request to /assets/{path} from host {request.remote_addr}. Attempting to serve: {os.path.join(STATIC_FOLDER, 'assets', path)}")
    # Serve files from the assets subfolder within the static folder
    return send_from_directory(os.path.join(STATIC_FOLDER, "assets"), path)

@app.route("/<path:path>")
def static_dir(path):
    logger.info(f"Request to /{path} from host {request.remote_addr}. Attempting to serve: {os.path.join(STATIC_FOLDER, path)}")
    # Serve any other static files directly from the static folder root
    return send_from_directory(STATIC_FOLDER, path)
