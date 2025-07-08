import uuid
import pymysql
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Boolean, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from decimal import Decimal

# Install PyMySQL as MySQLdb for compatibility
pymysql.install_as_MySQLdb()

# Initialize SQLAlchemy outside of create_app to avoid circular imports if app is also imported by models
db = SQLAlchemy()

# Helper function to generate UUID strings for internal primary keys
def generate_uuid():
    return str(uuid.uuid4())

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    iiko_category_id = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(255))
    color = db.Column(db.String(255))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(512))
    is_hidden = db.Column(db.Boolean, default=False)
    # This relationship is crucial for the IIKO sync to fetch products per category
    products = db.relationship('Product', backref='original_category', lazy=True) # Renamed backref for clarity
    main_category_id = db.Column(db.String(36), db.ForeignKey('main_category.id'), nullable=True)
    main_category = db.relationship('MainCategory', backref='original_categories', lazy=True)


class MainCategory(db.Model):
    __tablename__ = 'main_category'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), unique=True, nullable=False)
    icon = db.Column(db.String(255))
    color = db.Column(db.String(255))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(512))
    is_hidden = db.Column(db.Boolean, default=False)
    iiko_category_ids = db.Column(db.JSON) # Store a list of original iiko category IDs it consolidates
    display_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=9999)

    # New relationship for products that will point directly to MainCategory after migration
    # backref can be 'products' or 'main_products'
    products = db.relationship('Product', backref='main_category', lazy=True,
                               primaryjoin="Product.main_category_id == MainCategory.id")


class Addon(db.Model):
    __tablename__ = 'addon' # Explicitly define table name
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_addon_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the addon item (iiko Modifier ID)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False) # Use Numeric for currency
    image = db.Column(db.String(255), nullable=True) # If addons (modifiers) have images in iiko

    # Junction table for Product-Addon relationship (many-to-many)
    product_associations = db.relationship('ProductAddon', back_populates='addon')

class Recommendation(db.Model):
    __tablename__ = 'recommendation' # Explicitly define table name
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_recommendation_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the recommendation item (iiko Item ID from a specific category)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False) # Use Numeric for currency
    image = db.Column(db.String(255), nullable=True) # From iiko item's image_url

    # Junction table for Product-Recommendation relationship (many-to-many)
    product_associations = db.relationship('ProductRecommendation', back_populates='recommendation')

class Product(db.Model):
    __tablename__ = 'product' # Explicitly define table name
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    iiko_product_id = db.Column(db.String(36), unique=True, nullable=True) # New: iiko's ID for the product (main iiko Item ID)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False) # Use Numeric for currency
    image = db.Column(db.String(255), nullable=True) # From iiko item.itemSizes[0].buttonImageUrl
    # THIS IS THE CRUCIAL PART:
    # Keep the original categoryId linked to the 'category' table for IIKO sync
    categoryId = db.Column(db.String(36), db.ForeignKey('category.id'), nullable=False)
    # The 'original_category' backref in Category model will link to this

    # Add a *NEW* column for the main_category_id, which will be populated during migration
    main_category_id = db.Column(db.String(36), db.ForeignKey('main_category.id'), nullable=True)
    # The 'main_category' backref in MainCategory model will link to this

    nutrition = db.Column(JSON, nullable=True) # Store as JSON (from iiko item.itemSizes[0].nutritions)
    # The 'ingredients' field in your API will map to a combination of iiko allergens, tags, labels
    ingredients = db.Column(JSON, nullable=True) # Store as JSON (list of strings)

    is_hidden = db.Column(db.Boolean, default=False, nullable=False) # From iiko item.isHidden
    sku = db.Column(db.String(50), nullable=True) # From iiko item.sku
    measure_unit = db.Column(db.String(50), nullable=True) # From iiko item.measureUnit
    item_type = db.Column(db.String(50), nullable=True) # From iiko item.type (e.g., "GOODS", "DISH")

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
    __tablename__ = 'order' # Explicitly define table name
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    total = db.Column(db.Numeric(10, 2), nullable=False) # Use Numeric for currency
    delivery_address = db.Column(db.String(255), nullable=False)
    delivery_phone = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending') # e.g., 'pending', 'preparing', 'delivering', 'delivered', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_item' # Explicitly define table name
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=False) # Links to Product.id
    quantity = db.Column(db.Integer, nullable=False)

    # Store IDs of selected addons/recommendations as JSON arrays
    selected_addons_ids = db.Column(JSON, nullable=True, default=[]) # Default to empty list
    selected_recommendation_ids = db.Column(JSON, nullable=True, default=[]) # Default to empty list

    product = db.relationship('Product') # Link to the actual product
