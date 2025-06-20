#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from app import app
from flask import send_from_directory
import os

# Get the absolute path to the directory where routes.py is located
# This assumes your 'static' folder is a sibling of the folder containing routes.py
# If 'static' is directly in the project root and routes.py is in a subfolder,
# you might need to adjust 'PROJECT_ROOT' accordingly.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')

print(STATIC_FOLDER)

@app.route("/")
def home():
    # Serve index.html from the static folder
    return send_from_directory(STATIC_FOLDER, 'index.html')

@app.route("/assets/<path:path>")
def assets_dir(path):
    # Serve index.html from the static folder
    return send_from_directory(os.path.join(STATIC_FOLDER, "assets"), path)

@app.route("/<path:path>")
def static_dir(path):
    # Serve index.html from the static folder
    return send_from_directory(STATIC_FOLDER, path)
