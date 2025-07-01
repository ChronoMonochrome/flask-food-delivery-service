# scheduler.py
import os
import atexit
from apscheduler.schedulers.blocking import BlockingScheduler
# from apscheduler.triggers.interval import IntervalTrigger # Remove or comment out this line
from apscheduler.triggers.cron import CronTrigger # Import CronTrigger
from dotenv import load_dotenv

# Load environment variables specific to the scheduler if any
load_dotenv()

from app import create_app
from app.models import db
from app.logger import logger
from app.iiko_service import synchronize_iiko_data

app = create_app()
db.init_app(app)

def sync_data_job():
    with app.app_context():
        logger.info("Scheduler: Starting iiko data synchronization...")
        try:
            synchronize_iiko_data()
            logger.info("Scheduler: iiko data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Scheduler: Error during iiko data synchronization: {e}", exc_info=True)
            db.session.rollback()

scheduler = BlockingScheduler()

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
