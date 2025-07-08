# scripts/migrate_categories.py (create this file)
import os
import sys
from collections import defaultdict
from sqlalchemy.exc import IntegrityError

# Assuming your app and db are initialized in app/__init__.py or similar
# Adjust this import path as per your project structure
# from app import create_app, db
# from app.models import Category, Product, MainCategory, generate_uuid

# For demonstration, let's assume a minimal app setup for this script
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database # pip install sqlalchemy-utils

# Import models from the updated models.py
# Make sure your models.py is accessible in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import db, Category, Product, MainCategory, generate_uuid, Order, OrderItem, Addon, Recommendation, ProductAddon, ProductRecommendation, JSON

# Define the consolidation mapping
# The key is the desired main category name, and the value is a list of prefixes
# or exact names of original categories that should map to this main category.
CATEGORY_CONSOLIDATION_MAP = {
    "Wok": ["Wok"],
    "Бургеры": ["Бургеры"],
    "Горячие блюда": ["Горячие блюда"],
    "Горячие закуски": ["Горячие закуски"],
    "Добавки": ["Добавки"], # Will cover "Добавки/Мясо", "Добавки/Сыр", "Добавки/Рыба и морепродукты"
    "Доставка": ["Доставка"],
    "Кимпабы": ["Кимпабы"],
    "Напитки": ["Напитки"],
    "Осетинские пироги": ["Осетинские пироги"],
    "Паста": ["Паста"],
    "Пицца": ["Пицца"], # Will cover "Пицца/Римская", "Пицца/ Неаполитано", "Пицца/Классическая", "Пицца/Кальцоне", "Пицца/Чикаго"
    "Рекомендованные (общие)": ["Рекомендованные (общие)"],
    "Рекомендованные (ситуативные)": ["Рекомендованные (сиутативные)"],
    "Рулетики": ["Рулетики"],
    "Салаты": ["Салаты"],
    "Супы": ["Супы "], # Note the space here for exact match
    "Суши и роллы": ["Суши и роллы"], # Will cover various subcategories
    "Фокачча": ["Фокачча"],
    "Хачапури": ["Хачапури"], # Will cover various subcategories
    "Хот-доги и донер": ["Хот-доги и донер"],
}

# Helper function to find the main category name for a given original category name
def get_main_category_name(original_category_name):
    for main_name, prefixes in CATEGORY_CONSOLIDATION_MAP.items():
        for prefix in prefixes:
            if original_category_name.startswith(prefix):
                return main_name
    # Handle specific cases not covered by prefixes
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

    return None # If no main category found, which shouldn't happen with a comprehensive map

def run_migration(app, db):
    with app.app_context():
        print("Starting category consolidation and migration...")

        # Step 1: Gather original categories and group them by their new main category name
        original_categories = Category.query.order_by(Category.name).all()
        grouped_categories = defaultdict(list)

        for cat in original_categories:
            main_name = get_main_category_name(cat.name)
            if main_name:
                grouped_categories[main_name].append(cat)
            else:
                print(f"Warning: Original category '{cat.name}' did not map to any main category. Skipping.")

        # Step 2: Create MainCategory entries and update original categories
        for main_name, categories_to_group in grouped_categories.items():
            print(f"Processing main category: {main_name}")

            # Try to find existing main category first (in case of re-run or partial migration)
            main_category = MainCategory.query.filter_by(name=main_name).first()

            if not main_category:
                # Pick the first original category for icon, color, description, image_url
                # This is an arbitrary choice as per your requirement
                first_cat = categories_to_group[0]
                iiko_ids = [cat.iiko_category_id for cat in categories_to_group if cat.iiko_category_id]

                main_category = MainCategory(
                    name=main_name,
                    icon=first_cat.icon,
                    color=first_cat.color,
                    description=first_cat.description,
                    image_url=first_cat.image_url,
                    is_hidden=False,
                    iiko_category_ids=iiko_ids # Store all iiko_category_ids as JSON
                )
                db.session.add(main_category)
                try:
                    db.session.commit()
                    print(f"Created new MainCategory: {main_name} (ID: {main_category.id})")
                except IntegrityError:
                    db.session.rollback()
                    print(f"MainCategory '{main_name}' already exists (likely concurrency or re-run). Fetching existing.")
                    main_category = MainCategory.query.filter_by(name=main_name).first()
                    if not main_category:
                        print(f"Error: Could not retrieve existing MainCategory '{main_name}' after rollback. Skipping.")
                        continue # Skip this main category if we can't get it

            # Update original categories to point to the new main_category_id
            for cat in categories_to_group:
                if cat.main_category_id != main_category.id:
                    cat.main_category_id = main_category.id
                    print(f"  Updated original category '{cat.name}' to point to MainCategory '{main_name}'")

        try:
            db.session.commit()
            print("Successfully linked original categories to main categories.")
        except Exception as e:
            db.session.rollback()
            print(f"Error linking original categories: {e}")
            return

        # Step 3: Update products to reference the new MainCategory IDs
        # This is the crucial step for your API to work correctly with consolidated categories.
        print("Updating products to reference MainCategory IDs...")
        products_to_update = Product.query.all()
        updated_product_count = 0

        for product in products_to_update:
            # Find the original category this product belongs to
            original_category = Category.query.get(product.categoryId)
            if original_category and original_category.main_category:
                if product.categoryId != original_category.main_category.id: # Check if categoryId already points to main_category
                    product.categoryId = original_category.main_category.id
                    updated_product_count += 1
            else:
                print(f"Warning: Product '{product.name}' (ID: {product.id}) has original category '{product.categoryId}' not found or not mapped to a MainCategory. Skipping product update.")

        try:
            db.session.commit()
            print(f"Successfully updated {updated_product_count} products to reference new MainCategory IDs.")
            print("Migration complete!")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating product category IDs: {e}")
            print("Migration failed or partially completed due to error.")


if __name__ == '__main__':
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://user:your_db_password@db:3306/mydatabase') # Or your SQLite path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        print("Ensuring database tables exist...")
        db.create_all()
        print("Tables checked/created.")

    run_migration(app, db)
