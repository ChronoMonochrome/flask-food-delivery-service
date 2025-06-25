# app/__init__.py

from os.path import join, realpath, dirname
from flask import Flask
from flask_session import Session
from datetime import timedelta
import os
from dotenv import load_dotenv

from .factory import create_app
from .models import db # Import db from models

app = create_app()

# Initialize SQLAlchemy with the app
db.init_app(app)

# Now import logger, models, and routes as app is fully initialized
from app.logger import logger
from app import models
from app import routes
from app.api import api_bp # Import the API blueprint

app.register_blueprint(api_bp, url_prefix='/api') # Register the API blueprint

# Function to load initial data
def load_initial_data():
    from app.models import Category, Product, Addon, Recommendation, Order, OrderItem
    import json
    from datetime import datetime

    with app.app_context():
        # Check if data already exists to prevent duplication on restarts
        if Category.query.first() and Product.query.first():
            logger.info("Database already populated. Skipping initial data load.")
            return

        logger.info("Loading initial data into the database...")
        mock_data_path = os.path.join(app.static_folder, 'mockData.json')
        if not os.path.exists(mock_data_path):
            logger.error(f"mockData.json not found at {mock_data_path}")
            return

        with open(mock_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Add Categories
        for cat_data in data['categories']:
            category = Category(id=cat_data['id'], name=cat_data['name'], icon=cat_data['icon'], color=cat_data['color'])
            db.session.add(category)
        db.session.commit()
        logger.info(f"Loaded {len(data['categories'])} categories.")

        # Add Addons
        for addon_data in data['addons']:
            addon = Addon(id=addon_data['id'], name=addon_data['name'], price=addon_data['price'])
            db.session.add(addon)
        db.session.commit()
        logger.info(f"Loaded {len(data['addons'])} addons.")

        # Add Recommendations
        for rec_data in data['recommendations']:
            recommendation = Recommendation(id=rec_data['id'], name=rec_data['name'], price=rec_data['price'], image=rec_data['image'])
            db.session.add(recommendation)
        db.session.commit()
        logger.info(f"Loaded {len(data['recommendations'])} recommendations.")

        # Add Products and link relationships
        for prod_data in data['products']:
            product = Product(
                id=prod_data['id'],
                name=prod_data['name'],
                description=prod_data['description'],
                price=prod_data['price'],
                image=prod_data['image'],
                categoryId=prod_data['categoryId'],
                nutrition=prod_data.get('nutrition'),
                ingredients=prod_data.get('ingredients')
            )
            # Link addons
            for addon_id in prod_data.get('addonIds', []):
                addon = Addon.query.get(addon_id)
                if addon:
                    product.available_addons.append(addon)
            # Link recommendations
            for rec_id in prod_data.get('recommendationIds', []):
                recommendation = Recommendation.query.get(rec_id)
                if recommendation:
                    product.recommendations.append(recommendation)
            db.session.add(product)
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
                comment=order_data['deliveryInfo']['comment'],
                status=order_data['status'],
                created_at=datetime.fromisoformat(order_data['createdAt'].replace('Z', '+00:00')),
                estimated_delivery=datetime.fromisoformat(order_data['estimatedDelivery'].replace('Z', '+00:00')) if order_data['estimatedDelivery'] else None
            )
            db.session.add(order)
            db.session.commit() # Commit to get order.id for order items

            for item_data in order_data['items']:
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
    db.create_all()
    load_initial_data()
