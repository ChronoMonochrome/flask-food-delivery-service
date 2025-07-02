import uuid
import pymysql
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Install PyMySQL as MySQLdb for compatibility
pymysql.install_as_MySQLdb()

# Initialize SQLAlchemy outside of create_app to avoid circular imports if app is also imported by models
db = SQLAlchemy()

# Helper function to generate UUID strings
def generate_uuid():
    return str(uuid.uuid4())

class Category(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_category_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the category
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(20), nullable=True)
    color = db.Column(db.String(100), nullable=True)
    products = db.relationship('Product', backref='category', lazy=True)

class Addon(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_addon_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the addon item
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    # Add other fields if needed from iiko data that are common for addons, e.g., image
    image = db.Column(db.String(255), nullable=True) # If addons have images in iiko

    # Junction table for Product-Addon relationship (many-to-many)
    product_associations = db.relationship('ProductAddon', back_populates='addon')

class Recommendation(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_recommendation_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the recommendation item
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)

    # Junction table for Product-Recommendation relationship (many-to-many)
    product_associations = db.relationship('ProductRecommendation', back_populates='recommendation')


class Product(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_product_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the product
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    categoryId = db.Column(db.String(36), db.ForeignKey('category.id'), nullable=False)

    nutrition = db.Column(JSON, nullable=True) # Store as JSON
    ingredients = db.Column(JSON, nullable=True) # Store as JSON (list of strings)

    # Many-to-many relationships with Addons and Recommendations
    available_addons = db.relationship('ProductAddon', back_populates='product')
    recommendations = db.relationship('ProductRecommendation', back_populates='product')

class ProductAddon(db.Model):
    __tablename__ = 'product_addon'
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), primary_key=True)
    addon_id = db.Column(db.String(36), db.ForeignKey('addon.id'), primary_key=True)
    product = db.relationship('Product', back_populates='available_addons')
    addon = db.relationship('Addon', back_populates='product_associations')

class ProductRecommendation(db.Model):
    __tablename__ = 'product_recommendation'
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), primary_key=True)
    recommendation_id = db.Column(db.String(36), db.ForeignKey('recommendation.id'), primary_key=True)
    product = db.relationship('Product', back_populates='recommendations')
    recommendation = db.relationship('Recommendation', back_populates='product_associations')


class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    total = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    delivery_phone = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending') # e.g., 'pending', 'preparing', 'delivering', 'delivered', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    # Store IDs of selected addons/recommendations as JSON arrays
    selected_addons_ids = db.Column(JSON, nullable=True)
    selected_recommendation_ids = db.Column(JSON, nullable=True)

    product = db.relationship('Product') # Link to the actual product
