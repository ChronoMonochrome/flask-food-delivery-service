# app/__init__.py

import json

from datetime import datetime
from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv

from .factory import create_app
from .models import db # Import db from models
from .iiko_service import synchronize_iiko_data

app = create_app()

# Initialize SQLAlchemy with the app
db.init_app(app)

# Now import logger, models, and routes as app is fully initialized
from app.logger import logger
from app import models
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem, ProductAddon, ProductRecommendation
from app import routes
from app.api import api_bp # Import the API blueprint


app.register_blueprint(api_bp, url_prefix='/api') # Register the API blueprint


def load_initial_data(app): # Pass app as an argument since it's likely defined globally elsewhere
    with app.app_context():
        # Check if data already exists to prevent duplication on restarts
        if Category.query.first() or Product.query.first() or Addon.query.first() or Recommendation.query.first():
            logger.info("Database already populated. Skipping initial data load.")
            return

        logger.info("Loading initial data into the database from mockData.json...")
        mock_data_path = os.path.join(app.static_folder, 'mockData.json')
        if not os.path.exists(mock_data_path):
            logger.error(f"mockData.json not found at {mock_data_path}")
            return

        with open(mock_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # To handle potential UUID mismatches if IDs are not consistently UUIDs in mockData
        # and to ensure the iiko_id fields are populated for consistency with the new models.
        # However, for mockData, we're just using the provided IDs.
        # If you want to strictly adhere to UUID generation for internal IDs,
        # you'd omit id=cat_data['id'] and let SQLAlchemy generate it.
        # For now, we'll assume mockData IDs are compatible.

        # Add Categories
        for cat_data in data['categories']:
            category = Category(
                id=cat_data['id'],
                iiko_category_id=cat_data['id'], # Use mock ID as iiko_id for mock data
                name=cat_data['name'],
                icon=cat_data['icon'],
                color=cat_data['color']
            )
            db.session.add(category)
        db.session.commit()
        logger.info(f"Loaded {len(data['categories'])} categories.")

        # Add Addons
        for addon_data in data['addons']:
            addon = Addon(
                id=addon_data['id'],
                iiko_addon_id=addon_data['id'], # Use mock ID as iiko_id for mock data
                name=addon_data['name'],
                price=addon_data['price']
                # image field is nullable, no image in mock addon data
            )
            db.session.add(addon)
        db.session.commit()
        logger.info(f"Loaded {len(data['addons'])} addons.")

        # Add Recommendations
        for rec_data in data['recommendations']:
            recommendation = Recommendation(
                id=rec_data['id'],
                iiko_recommendation_id=rec_data['id'], # Use mock ID as iiko_id for mock data
                name=rec_data['name'],
                price=rec_data['price'],
                image=rec_data['image']
            )
            db.session.add(recommendation)
        db.session.commit()
        logger.info(f"Loaded {len(data['recommendations'])} recommendations.")

        # Add Products and link relationships
        # We need to fetch the created Category, Addon, and Recommendation objects
        # to establish relationships correctly via the junction tables.
        categories_map = {c.id: c for c in Category.query.all()}
        addons_map = {a.id: a for a in Addon.query.all()}
        recommendations_map = {r.id: r for r in Recommendation.query.all()}


        for prod_data in data['products']:
            # Ensure category exists before creating product
            if prod_data['categoryId'] not in categories_map:
                logger.warning(f"Category ID {prod_data['categoryId']} for product {prod_data['name']} not found. Skipping product.")
                continue

            product = Product(
                id=prod_data['id'],
                iiko_product_id=prod_data['id'], # Use mock ID as iiko_id for mock data
                name=prod_data['name'],
                description=prod_data['description'],
                price=prod_data['price'],
                image=prod_data['image'],
                categoryId=prod_data['categoryId'], # This links to the Category model
                nutrition=prod_data.get('nutrition', {}), # Ensure it's a dict for JSON type
                ingredients=prod_data.get('ingredients', []) # Ensure it's a list for JSON type
            )
            db.session.add(product)
            db.session.flush() # Flush to get the product ID before linking junction tables

            # Link addons via ProductAddon junction table
            for addon_id in prod_data.get('addonIds', []):
                addon = addons_map.get(addon_id)
                if addon:
                    product_addon = ProductAddon(product=product, addon=addon)
                    db.session.add(product_addon)
                else:
                    logger.warning(f"Addon ID {addon_id} for product {prod_data['name']} not found.")

            # Link recommendations via ProductRecommendation junction table
            for rec_id in prod_data.get('recommendationIds', []):
                recommendation = recommendations_map.get(rec_id)
                if recommendation:
                    product_recommendation = ProductRecommendation(product=product, recommendation=recommendation)
                    db.session.add(product_recommendation)
                else:
                    logger.warning(f"Recommendation ID {rec_id} for product {prod_data['name']} not found.")

        db.session.commit()
        logger.info(f"Loaded {len(data['products'])} products.")

        # Add Mock Orders
        for order_data in data['mockOrders']:
            order = Order(
                id=order_data['id'],
                total=order_data['total'],
                delivery_address=order_data['deliveryInfo']['address'],
                delivery_phone=order_data['deliveryInfo']['phone'],
                payment_method=order_data['deliveryInfo']['paymentMethod'],
                comment=order_data['deliveryInfo'].get('comment'), # Use .get for optional keys
                status=order_data['status'],
                created_at=datetime.fromisoformat(order_data['createdAt'].replace('Z', '+00:00')),
                estimated_delivery=datetime.fromisoformat(order_data['estimatedDelivery'].replace('Z', '+00:00')) if order_data['estimatedDelivery'] else None
            )
            db.session.add(order)
            db.session.flush() # Flush to get order.id for order items

            for item_data in order_data['items']:
                # Ensure product exists before creating order item
                product_in_db = Product.query.get(item_data['productId'])
                if not product_in_db:
                    logger.warning(f"Product ID {item_data['productId']} for order {order_data['id']} item not found. Skipping order item.")
                    continue

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data['productId'],
                    quantity=item_data['quantity'],
                    selected_addons_ids=item_data.get('selectedAddonIds', []),
                    selected_recommendation_ids=item_data.get('selectedRecommendationIds', [])
                )
                db.session.add(order_item)
        db.session.commit()
        logger.info(f"Loaded {len(data['mockOrders'])} mock orders.")

        logger.info("Initial data loading complete.")

# Create database tables and load initial data when the app context is available
with app.app_context():
    overwrite_existing_data = True
    db.create_all()
    if not overwrite_existing_data:
        load_initial_data(app)
    # --- Data Synchronization ---
    # Consider running this only once on deployment, or on a schedule.
    # For development, running it on every startup might be okay.
    # In a production environment, you might want a separate cron job or an admin endpoint.
    #
    # For now, let's run it once on startup for demonstration.
    try:
        synchronize_iiko_data(overwrite_existing=overwrite_existing_data)
    except Exception as e:
        app.logger.error(f"Failed to synchronize iiko data on startup: {e}")
