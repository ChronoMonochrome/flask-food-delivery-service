# print_db_data.py
import os
import sys
from dotenv import load_dotenv

# Ensure the application root is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

load_dotenv() # Load environment variables from .env file

from app import create_app
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem
from app.logger import logger

def print_one_entry_per_model():
    app = create_app()
    db.init_app(app)

    with app.app_context():
        logger.info("Attempting to print one entry from each model...")

        models_to_check = [
            (Category, "Category"),
            (Product, "Product"),
            (Addon, "Addon"),
            (Recommendation, "Recommendation"),
            (Order, "Order"),
            (OrderItem, "OrderItem")
        ]

        for model_class, model_name in models_to_check:
            try:
                entry = model_class.query.first()
                if entry:
                    logger.info(f"--- {model_name} (first entry) ---")
                    # Use __repr__ for a concise representation
                    logger.info(repr(entry))
                    # You can also print specific attributes if __repr__ is not detailed enough
                    # For example:
                    # if model_name == "Product":
                    #     logger.info(f"  Name: {entry.name}, Price: {entry.price}, Category: {entry.category.name if entry.category else 'N/A'}")
                else:
                    logger.info(f"--- {model_name} ---")
                    logger.info(f"No entries found for {model_name}.")
            except Exception as e:
                logger.error(f"Error fetching {model_name} entry: {e}", exc_info=True)
                db.session.rollback() # Rollback if a query fails

        logger.info("Finished printing database entries.")

if __name__ == '__main__':
    print_one_entry_per_model()
