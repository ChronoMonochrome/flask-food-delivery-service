from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session

from datetime import timedelta
import os # Import the os module for path manipulation

root_dir = realpath(join(dirname(__file__), ".."))
dot_env = realpath(join(root_dir, ".env"))

flask_templates_dir = realpath(join(dirname(__file__), "templates"))

# --- STATIC FILE CONFIGURATION START ---
# Define the path to your static folder.
# Assuming 'static' is a sibling of the 'app' directory (i.e., in the project root).
static_folder_path = realpath(join(root_dir, "static"))

app = Flask(__name__,
            template_folder=flask_templates_dir,
            static_folder='/', # Specify the path to your static files
            static_url_path='/'         # Define the URL prefix for static files (e.g., /static/css/style.css)
           )
# --- STATIC FILE CONFIGURATION END ---

app.config["TEMPLATES_DIR"] = flask_templates_dir

app.secret_key = "development key"

app.session = Session()
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
# The maximum number of items the session stores
# before it starts deleting some, default 500
app.config['SESSION_FILE_THRESHOLD'] = 1000000
app.session.init_app(app)

app.config["SQLALCHEMY_DATABASE_URI"] = open(dot_env, "r").read().split("\n")[0]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

from app import models
from app import routes
