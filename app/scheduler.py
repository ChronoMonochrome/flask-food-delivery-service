# scheduler.py
import os
import atexit
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from sqlalchemy import inspect # Import inspect for checking table existence

# Load environment variables specific to the scheduler if any
load_dotenv()

from app import create_app
from app.models import db, Category # Import at least one model to check for table existence
from app.logger import logger
from app.iiko_service import synchronize_iiko_data

app = create_app()
db.init_app(app)

def check_and_sync_initial_data():
    """
    Checks if database tables are synchronized. If not, performs an initial synchronization.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        # Check if a known table (e.g., 'category') exists in the database
        if not inspector.has_table(Category.__tablename__):
            logger.warning("Scheduler: Database tables not found. Performing initial data synchronization...")
            try:
                # Attempt to create all tables (this is idempotent)
                db.create_all()
                logger.info("Scheduler: Database tables created.")
                synchronize_iiko_data()
                logger.info("Scheduler: Initial iiko data synchronization completed successfully.")
            except Exception as e:
                logger.error(f"Scheduler: Error during initial data synchronization: {e}", exc_info=True)
                db.session.rollback()
        else:
            logger.info("Scheduler: Database tables already exist. Skipping initial synchronization check.")

def sync_data_job():
    """
    Scheduled job to synchronize iiko data.
    """
    with app.app_context():
        logger.info("Scheduler: Starting iiko data synchronization (scheduled run)...")
        try:
            synchronize_iiko_data()
            logger.info("Scheduler: iiko data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Scheduler: Error during iiko data synchronization: {e}", exc_info=True)
            db.session.rollback()

scheduler = BlockingScheduler()

# --- Initial check and sync on startup ---
logger.info("Scheduler: Performing initial database table check and synchronization...")
check_and_sync_initial_data()

# Add the sync job to the scheduler to run daily at 3 AM
# Note: The time is based on the container's timezone.
# Docker containers typically default to UTC unless otherwise configured.
logger.info("Scheduler: iiko data synchronization job scheduled to run daily at 3:00 AM.")
scheduler.add_job(
    sync_data_job,
    CronTrigger(hour=3, minute=0), # Set to 3 AM (hour=3, minute=0)
    id='iiko_sync_job',
    name='iiko_data_synchronization',
    replace_existing=True,
    max_instances=1
)

atexit.register(lambda: scheduler.shutdown())

logger.info("Scheduler: Starting APScheduler...")
try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    pass