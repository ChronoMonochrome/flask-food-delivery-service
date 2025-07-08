# print_db_data.py
import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure the application root is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

load_dotenv() # Load environment variables from .env file

from app import app
from app.models import db, MainCategory, Category, Product, Addon, Recommendation, Order, OrderItem
from app.logger import logger

def print_entries(print_all=True):
    with app.app_context():
        logger.info(f"Attempting to print {'all' if print_all else 'one'} entry from each model...")

        models_to_check = [
            (Category, "Category"),
            (MainCategory, "MainCategory"),
            (Product, "Product"),
            (Addon, "Addon"),
            (Recommendation, "Recommendation"),
            (Order, "Order"),
            (OrderItem, "OrderItem")
        ]

        for model_class, model_name in models_to_check:
            try:
                if print_all:
                    entries = model_class.query.all()
                else:
                    entries = [model_class.query.first()] if model_class.query.first() else []

                if entries:
                    logger.info(f"--- {model_name} ({'all' if print_all else 'first'} entries) ---")
                    for entry in entries:
                        if model_name == "Category":
                            logger.info(f"  ID: {entry.id}, IIKO ID: {entry.iiko_category_id}, Name: {entry.name}, MainCategory ID: {entry.main_category_id}, Is Hidden: {entry.is_hidden}")
                        elif model_name == "MainCategory":
                            logger.info(f"  ID: {entry.id}, Name: {entry.name}, Icon: {entry.icon}, Color: {entry.color}, IIKO Category IDs: {entry.iiko_category_ids}, Is Hidden: {entry.is_hidden}")
                        elif model_name == "Product":
                            # Crucial check for main_category_id
                            logger.info(f"  ID: {entry.id}, IIKO ID: {entry.iiko_product_id}, Name: {entry.name}, Price: {entry.price}, Category ID (IIKO): {entry.categoryId}, MainCategory ID: {entry.main_category_id}, Is Hidden: {entry.is_hidden}")
                            if entry.nutrition:
                                logger.info(f"    Nutrition: Calories={entry.nutrition.get('calories')}, Carbs={entry.nutrition.get('carbs')}, Fat={entry.nutrition.get('fat')}, Proteins={entry.nutrition.get('proteins')}")
                            if entry.ingredients:
                                logger.info(f"    Ingredients: {entry.ingredients}")
                            if entry.available_addons:
                                logger.info(f"    Available Addon IDs: {[pa.addon_id for pa in entry.available_addons]}")
                            if entry.recommendations:
                                logger.info(f"    Recommendation IDs: {[pr.recommendation_id for pr in entry.recommendations]}")
                        elif model_name == "Addon":
                            logger.info(f"  ID: {entry.id}, IIKO Addon ID: {entry.iiko_addon_id}, Name: {entry.name}, Price: {entry.price}, Image: {entry.image}")
                        elif model_name == "Recommendation":
                            logger.info(f"  ID: {entry.id}, IIKO Recommendation ID: {entry.iiko_recommendation_id}, Name: {entry.name}, Price: {entry.price}, Image: {entry.image}")
                        elif model_name == "Order":
                            logger.info(f"  ID: {entry.id}, Total: {entry.total}, Status: {entry.status}, Created At: {entry.created_at}, Delivery Address: {entry.delivery_address}, Phone: {entry.delivery_phone}, Payment Method: {entry.payment_method}, Comment: {entry.comment}")
                        elif model_name == "OrderItem":
                            logger.info(f"  ID: {entry.id}, Order ID: {entry.order_id}, Product ID: {entry.product_id}, Quantity: {entry.quantity}, Price At Order: {entry.price_at_order}, Selected Addons: {entry.selected_addons_ids}, Selected Recommendations: {entry.selected_recommendation_ids}")
                        else:
                            logger.info(repr(entry)) # Fallback for any other models
                        logger.info("-" * 30) # Separator for multiple entries
                else:
                    logger.info(f"--- {model_name} ---")
                    logger.info(f"No entries found for {model_name}.")
            except Exception as e:
                logger.error(f"Error fetching {model_name} entry: {e}", exc_info=True)
                db.session.rollback() # Rollback if a query fails

        logger.info("Finished printing database entries.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Print database entries.")
    parser.add_argument(
        '--one',
        action='store_true',
        help="Print only one entry per model instead of all entries."
    )
    args = parser.parse_args()

    print_entries(print_all=not args.one)