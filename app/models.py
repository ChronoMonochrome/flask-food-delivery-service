import pymysql
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Install PyMySQL as MySQLdb for compatibility
pymysql.install_as_MySQLdb()

# Initialize SQLAlchemy outside of create_app to avoid circular imports if app is also imported by models
db = SQLAlchemy()

# Association tables for many-to-many relationships
product_addon_association = db.Table('product_addon_association',
    db.Column('product_id', db.String(50), db.ForeignKey('products.id'), primary_key=True),
    db.Column('addon_id', db.String(50), db.ForeignKey('addons.id'), primary_key=True)
)

product_recommendation_association = db.Table('product_recommendation_association',
    db.Column('product_id', db.String(50), db.ForeignKey('products.id'), primary_key=True),
    db.Column('recommendation_id', db.String(50), db.ForeignKey('recommendations.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    login = Column(String(20), unique=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = Column(db.String(50), primary_key=True)
    name = Column(db.String(100), nullable=False)
    icon = Column(db.String(10), nullable=True)
    color = Column(db.String(100), nullable=True)
    products = relationship('Product', backref='category', lazy=True)

class Addon(db.Model):
    __tablename__ = 'addons'
    id = Column(db.String(50), primary_key=True)
    name = Column(db.String(100), nullable=False)
    price = Column(db.Float, nullable=False)

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = Column(db.String(50), primary_key=True)
    name = Column(db.String(100), nullable=False)
    price = Column(db.Float, nullable=False)
    image = Column(db.String(255), nullable=True)

class Product(db.Model):
    __tablename__ = 'products'
    id = Column(db.String(50), primary_key=True)
    name = Column(db.String(255), nullable=False)
    description = Column(db.Text, nullable=True)
    price = Column(db.Float, nullable=False)
    image = Column(db.String(255), nullable=True)
    categoryId = Column(db.String(50), db.ForeignKey('categories.id'), nullable=False)
    nutrition = Column(JSON, nullable=True)  # Stores a dictionary/JSON object
    ingredients = Column(JSON, nullable=True) # Stores a list of strings

    available_addons = relationship('Addon', secondary=product_addon_association, lazy='subquery',
                                   backref=db.backref('products', lazy=True))
    recommendations = relationship('Recommendation', secondary=product_recommendation_association, lazy='subquery',
                                  backref=db.backref('products', lazy=True))

class Order(db.Model):
    __tablename__ = 'orders'
    id = Column(db.String(50), primary_key=True)
    total = Column(db.Float, nullable=False)
    delivery_address = Column(db.String(255), nullable=False)
    delivery_phone = Column(db.String(50), nullable=False)
    payment_method = Column(db.String(50), nullable=False)
    comment = Column(db.Text, nullable=True)
    status = Column(db.String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)

    items = relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = Column(db.Integer, primary_key=True)
    order_id = Column(db.String(50), db.ForeignKey('orders.id'), nullable=False)
    product_id = Column(db.String(50), db.ForeignKey('products.id'), nullable=False)
    quantity = Column(db.Integer, nullable=False)
    selected_addons_ids = Column(JSON, nullable=True) # Stores list of addon IDs
    selected_recommendation_ids = Column(JSON, nullable=True) # Stores list of recommendation IDs

    product = relationship('Product') # Relationship to get product details
