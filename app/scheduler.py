# scheduler.py
import os
import atexit
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Load environment variables specific to the scheduler if any
load_dotenv()

# Import create_app and db from your Flask application
# It's important to import them after loading dotenv if DB_URL is in .env
from app import create_app
from app.models import db
from app.logger import logger
from app.iiko_service import synchronize_iiko_data

# Create the Flask app instance
app = create_app()

# Initialize SQLAlchemy with the app. This is crucial for scheduler tasks.
db.init_app(app)

def sync_data_job():
    """
    This function will be executed by the scheduler.
    It runs inside an app context to allow database operations.
    """
    with app.app_context():
        logger.info("Scheduler: Starting iiko data synchronization...")
        try:
            # Set overwrite_existing to False for periodic updates,
            # so it updates existing records and adds new ones.
            # If you want to purge and re-import everything on each sync, set to True.
            # For periodic updates, False is generally preferred.
            synchronize_iiko_data(overwrite_existing=False)
            logger.info("Scheduler: iiko data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Scheduler: Error during iiko data synchronization: {e}", exc_info=True)
            db.session.rollback() # Rollback any pending changes on error

# Initialize APScheduler
scheduler = BlockingScheduler()

# Add the sync job to the scheduler
# The interval is configurable via environment variable
sync_interval_hours = int(os.getenv("IIKO_SYNC_INTERVAL_HOURS", 1)) # Default to 1 hour
logger.info(f"Scheduler: iiko data synchronization job scheduled to run every {sync_interval_hours} hour(s).")

scheduler.add_job(
    sync_data_job,
    IntervalTrigger(hours=sync_interval_hours),
    id='iiko_sync_job',
    name='iiko_data_synchronization',
    replace_existing=True, # Replace job if it already exists (useful for re-initialization)
    max_instances=1 # Ensure only one instance of the job runs at a time
)

# Register a cleanup function to gracefully shut down the scheduler
atexit.register(lambda: scheduler.shutdown())

logger.info("Scheduler: Starting APScheduler...")
try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    pass # Handle graceful exit
