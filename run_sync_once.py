# run_sync_once.py
import os
import sys
from dotenv import load_dotenv

from app.logger import logger

# Ensure the application root is in the Python path for imports
# This is crucial when running a script outside of a direct Flask CLI context
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app
from app.models import db
from app.logger import logger
from app.iiko_service import synchronize_iiko_data

# Load environment variables
if os.path.exists(os.path.join(BASE_DIR, '.env.local')):
    load_dotenv(os.path.join(BASE_DIR, '.env.local'))
    logger.info(f"Loaded env from .env.local")
else:
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    logger.info(f"Loaded env from .env")

def run_immediate_sync():
    # Load .env variables again within the script if create_app() or other parts
    # of your app rely on them being present at this specific execution point.
    # If your create_app() handles dotenv loading, this might be redundant.
    # from dotenv import load_dotenv
    # load_dotenv()

    # Create the Flask app instance
    app = create_app()

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    with app.app_context():
        logger.info("Manual iiko data synchronization initiated.")
        db.create_all()
        try:
            synchronize_iiko_data()
            logger.info("Manual iiko data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Error during manual iiko data synchronization: {e}", exc_info=True)
            db.session.rollback()
            sys.exit(1) # Exit with an error code if sync fails

if __name__ == '__main__':
    run_immediate_sync()
