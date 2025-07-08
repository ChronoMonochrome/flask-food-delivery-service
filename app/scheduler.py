# scheduler.py
import os
import atexit
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError # Import ProgrammingError for table existence check

# Load environment variables specific to the scheduler if any
load_dotenv()

from app import create_app
# Import MainCategory and ensure db is initialized
from app.models import db, Category, MainCategory, Product # Added Product here for clarity
from app.logger import logger
from app.iiko_service import synchronize_iiko_data

# --- Start of inlined migration logic (or import from scripts.migrate_categories) ---
# You can put this into a separate file and import, but for self-containment in scheduler,
# copying it here might be simpler for Docker.

# Define the consolidation mapping (copied from scripts/migrate_categories.py)
CATEGORY_CONSOLIDATION_MAP = {
    "Wok": ["Wok"],
    "Бургеры": ["Бургеры"],
    "Горячие блюда": ["Горячие блюда"],
    "Горячие закуски": ["Горячие закуски"],
    "Добавки": ["Добавки"],
    "Доставка": ["Доставка"],
    "Кимпабы": ["Кимпабы"],
    "Напитки": ["Напитки"],
    "Осетинские пироги": ["Осетинские пироги"],
    "Паста": ["Паста"],
    "Пицца": ["Пицца"],
    "Рекомендованные (общие)": ["Рекомендованные (общие)"],
    "Рекомендованные (ситуативные)": ["Рекомендованные (сиутативные)"],
    "Рулетики": ["Рулетики"],
    "Салаты": ["Салаты"],
    "Супы": ["Супы "],
    "Суши и роллы": ["Суши и роллы"],
    "Фокачча": ["Фокачча"],
    "Хачапури": ["Хачапури"],
    "Хот-доги и донер": ["Хот-доги и донер"],
}

# Helper function to find the main category name (copied from scripts/migrate_categories.py)
def get_main_category_name(original_category_name):
    for main_name, prefixes in CATEGORY_CONSOLIDATION_MAP.items():
        for prefix in prefixes:
            if original_category_name.startswith(prefix):
                return main_name
    if "Хачапури по-имеретински" in original_category_name:
        return "Хачапури"
    if "Суши и роллы/Гунканы" in original_category_name or \
       "Суши и роллы/Маки" in original_category_name or \
       "Суши и роллы/Серия \"Черный бархат\"" in original_category_name or \
       "Суши и роллы/Нигири" in original_category_name or \
       "Суши и роллы/горячие роллы" in original_category_name or \
       "Суши и роллы/Роллы" in original_category_name or \
       "Суши и роллы/онигири" in original_category_name or \
       "Суши и роллы/Спайси" in original_category_name or \
       "Суши и роллы/запеченные роллы" in original_category_name or \
       "Суши и роллы/Сеты" in original_category_name or \
       "Суши и роллы/Соевый соус, васаби, имбирь" in original_category_name:
        return "Суши и роллы"
    if "Пицца/Римская" in original_category_name or \
       "Пицца/ Неаполитано" in original_category_name or \
       "Пицца/Классическая" in original_category_name or \
       "Пицца/Кальцоне" in original_category_name or \
       "Пицца/Чикаго" in original_category_name:
        return "Пицца"
    if "Добавки/Мясо" in original_category_name or \
       "Добавки/Сыр" in original_category_name or \
       "Добавки/Рыба и морепродукты" in original_category_name:
        return "Добавки"
    if "Хачапури по-аджарски" in original_category_name:
        return "Хачапури"
    return None

def run_category_migration_logic(current_app_instance, current_db_instance):
    """
    Consolidates categories into main categories and updates product links.
    This function replicates the core logic from scripts/migrate_categories.py
    """
    from collections import defaultdict
    from sqlalchemy.exc import IntegrityError
    from app.models import Category, Product, MainCategory # Re-import within function scope if needed
                                                        # or ensure they are imported globally

    logger.info("Starting category consolidation and migration logic (inlined)...")

    # Step 1: Gather original categories and group them by their new main category name
    original_categories = Category.query.order_by(Category.name).all()
    grouped_categories = defaultdict(list)

    for cat in original_categories:
        main_name = get_main_category_name(cat.name)
        if main_name:
            grouped_categories[main_name].append(cat)
        else:
            logger.warning(f"Migration: Original category '{cat.name}' did not map to any main category. Skipping.")

    # Step 2: Create MainCategory entries and update original categories
    for main_name, categories_to_group in grouped_categories.items():
        logger.info(f"Migration: Processing main category: {main_name}")

        main_category = MainCategory.query.filter_by(name=main_name).first()

        if not main_category:
            first_cat = categories_to_group[0]
            iiko_ids = [cat.iiko_category_id for cat in categories_to_group if cat.iiko_category_id]

            main_category = MainCategory(
                name=main_name,
                icon=first_cat.icon,
                color=first_cat.color,
                description=first_cat.description,
                image_url=first_cat.image_url,
                is_hidden=False,
                iiko_category_ids=iiko_ids
            )
            current_db_instance.session.add(main_category)
            try:
                current_db_instance.session.commit()
                logger.info(f"Migration: Created new MainCategory: {main_name} (ID: {main_category.id})")
            except IntegrityError:
                current_db_instance.session.rollback()
                logger.warning(f"Migration: MainCategory '{main_name}' already exists. Fetching existing.")
                main_category = MainCategory.query.filter_by(name=main_name).first()
                if not main_category:
                    logger.error(f"Migration: Could not retrieve existing MainCategory '{main_name}' after rollback. Skipping.")
                    continue

        for cat in categories_to_group:
            if cat.main_category_id != main_category.id: # Avoid unnecessary updates
                cat.main_category_id = main_category.id
                logger.debug(f"Migration: Updated original category '{cat.name}' to point to MainCategory '{main_name}'")

    try:
        current_db_instance.session.commit()
        logger.info("Migration: Successfully linked original categories to main categories.")
    except Exception as e:
        current_db_instance.session.rollback()
        logger.error(f"Migration: Error linking original categories: {e}", exc_info=True)
        return

    # Step 3: Update products to reference the new MainCategory IDs
    logger.info("Migration: Updating products to reference MainCategory IDs...")
    products_to_update = Product.query.all()
    updated_product_count = 0

    for product in products_to_update:
        original_category = Category.query.get(product.categoryId) # Get original category by its ID
        if original_category and original_category.main_category:
            # CORRECTED LINE: Update product.main_category_id, NOT product.categoryId
            if product.main_category_id != original_category.main_category.id:
                product.main_category_id = original_category.main_category.id
                updated_product_count += 1
        else:
            logger.warning(f"Migration: Product '{product.name}' (ID: {product.id}) original category "
                           f"'{product.categoryId}' not found or not mapped to a MainCategory. "
                           "Setting product.main_category_id to None if applicable.")
            # Optionally, set main_category_id to None if no mapping exists
            if product.main_category_id is not None:
                product.main_category_id = None
                updated_product_count += 1

    try:
        current_db_instance.session.commit()
        logger.info(f"Migration: Successfully updated {updated_product_count} products to reference new MainCategory IDs.")
        logger.info("Migration complete!")
    except Exception as e:
        current_db_instance.session.rollback()
        logger.error(f"Migration: Error updating product main category IDs: {e}", exc_info=True)
        logger.info("Migration failed or partially completed due to error.")

# --- End of inlined migration logic ---


app = create_app()
db.init_app(app)

def check_and_sync_initial_data():
    """
    Checks if database tables are synchronized. If not, performs an initial synchronization.
    After sync, checks if MainCategory table is empty and runs migration if necessary.
    """
    with app.app_context():
        # This will create tables if they don't exist.
        # In a production setup with Flask-Migrate, 'db.create_all()'
        # might be replaced by ensuring 'flask db upgrade' has run.
        db.create_all()
        logger.info("Scheduler: Database tables ensured (created if not existing).")

        # Perform initial iiko data synchronization
        logger.info("Scheduler: Starting initial iiko data synchronization...")
        try:
            synchronize_iiko_data()
            logger.info("Scheduler: Initial iiko data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Scheduler: Error during initial iiko data synchronization: {e}", exc_info=True)
            db.session.rollback()
            # If initial sync fails, we might not want to proceed with migration
            return

        # Check if main_category table exists and is empty
        inspector = inspect(db.engine)
        # Check for both 'main_category' and 'product' tables to be safe,
        # as the product table needs main_category_id column.
        if 'main_category' not in inspector.get_table_names() or \
           'product' not in inspector.get_table_names() or \
           'main_category_id' not in [c['name'] for c in inspector.get_columns('product')]:
            logger.warning("Scheduler: 'main_category' table or 'product.main_category_id' column does not exist. This indicates migrations might not have run correctly.")
            # In a production environment, you would typically halt here and
            # instruct the user to run migrations. For a first run, db.create_all()
            # should have created it if the model was defined before.
            # If it's truly not there after create_all, there's a deeper issue.
            return

        try:
            main_category_count = db.session.query(MainCategory).count()
            if main_category_count == 0:
                logger.info("Scheduler: 'main_category' table is empty. Running category consolidation migration.")
                run_category_migration_logic(app, db) # Pass app and db to the inlined function
            else:
                logger.info("Scheduler: 'main_category' table is not empty. Skipping category consolidation migration.")
        except ProgrammingError as e:
            # This can happen if the table wasn't created yet or other DB issues
            logger.error(f"Scheduler: Database error while checking main_category table: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Scheduler: An unexpected error occurred during category migration check: {e}", exc_info=True)


def sync_data_job():
    """
    Scheduled job to synchronize iiko data.
    """
    with app.app_context():
        logger.info("Scheduler: Starting iiko data synchronization (scheduled run)...")
        try:
            synchronize_iiko_data()
            logger.info("Scheduler: iiko data synchronization completed successfully.")
            # No migration check here; migration is a one-time process on initial data load
        except Exception as e:
            logger.error(f"Scheduler: Error during iiko data synchronization: {e}", exc_info=True)
            db.session.rollback()

scheduler = BlockingScheduler()

# --- Initial check and sync on startup ---
logger.info("Scheduler: Performing initial database table check and synchronization...")
check_and_sync_initial_data() # This call now includes the conditional migration

# --- Schedule regular data synchronization ---
scheduler.add_job(
    func=sync_data_job,
    trigger=CronTrigger(hour="*", minute="*/30"), # Every 30 minutes
    id='iiko_data_sync',
    name='Synchronize iiko data every 30 minutes',
    replace_existing=True
)

# Shutdown hook for the scheduler
atexit.register(lambda: scheduler.shutdown())

logger.info("Scheduler: Starting scheduler...")
scheduler.start()