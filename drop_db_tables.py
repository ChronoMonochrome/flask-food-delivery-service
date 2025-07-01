# drop_db_tables.py
import os
import sys
from dotenv import load_dotenv

# Ensure the application root is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

load_dotenv() # Load environment variables from .env file

from app import create_app
from app.models import db
from app.logger import logger

def drop_all_tables():
    app = create_app()
    db.init_app(app)

    with app.app_context():
        logger.warning("!!! WARNING: Attempting to drop ALL database tables. All data will be LOST. !!!")
        try:
            db.drop_all()
            logger.info("Successfully dropped all database tables.")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}", exc_info=True)
            db.session.rollback() # Rollback in case of partial failure
            sys.exit(1) # Exit with error code

if __name__ == '__main__':
    drop_all_tables()
