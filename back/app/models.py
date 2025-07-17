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

SAUCES_CATEGORY_NAME = "Соусы"
WOK_CATEGORY_NAME = "Wok"
WOK_PRODUCT_CONSTRUCTOR_ID = "859b7336-83a8-4fa0-80c9-62681ffeb8e4"

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
    group_name = db.Column(db.String(120), nullable=False)
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

    is_customizable = db.Column(db.Boolean, default=False, nullable=False) # New: for Wok or other customizable items

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

# --- New Models for Cart and Wok Customization ---

class WokBase(db.Model):
    __tablename__ = 'wok_base'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), nullable=True)

class WokMeat(db.Model):
    __tablename__ = 'wok_meat'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), nullable=True)

class WokTopping(db.Model):
    __tablename__ = 'wok_topping'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), nullable=True)

class WokSauce(db.Model):
    __tablename__ = 'wok_sauce'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), nullable=True)

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), unique=True, nullable=False) # Each user has one cart
    total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    __tablename__ = 'cart_item'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    cart_id = db.Column(db.String(36), db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=True) # Can be null if it's a custom item (like a wok)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Fields for custom items (e.g., custom Wok)
    custom_name = db.Column(db.String(255), nullable=True)
    custom_description = db.Column(db.Text, nullable=True)
    custom_price = db.Column(db.Numeric(10, 2), nullable=True)
    custom_image = db.Column(db.String(255), nullable=True) # e.g., default Wok image

    # JSON field to store Wok customization details if applicable
    # Storing IDs and quantities for addons within the JSON, and IDs for recommendations
    # This structure mirrors the frontend's WokCustomization for simplicity of storage
    custom_wok_data = db.Column(JSON, nullable=True)

    # Relationships to Addons and Recommendations selected for *this specific cart item*
    # These are distinct from the Product's available_addons and recommendations
    selected_addons = db.relationship('CartAddon', backref='cart_item', lazy=True, cascade="all, delete-orphan")
    selected_recommendations = db.relationship('CartRecommendation', backref='cart_item', lazy=True, cascade="all, delete-orphan")

    # Link to the actual product (if not a custom item derived solely from custom_wok_data)
    product = db.relationship('Product')

class CartAddon(db.Model):
    __tablename__ = 'cart_addon'
    cart_item_id = db.Column(db.String(36), db.ForeignKey('cart_item.id'), primary_key=True)
    addon_id = db.Column(db.String(36), db.ForeignKey('addon.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1) # Quantity of this specific addon within the cart item
    addon = db.relationship('Addon')

class CartRecommendation(db.Model):
    __tablename__ = 'cart_recommendation'
    cart_item_id = db.Column(db.String(36), db.ForeignKey('cart_item.id'), primary_key=True)
    recommendation_id = db.Column(db.String(36), db.ForeignKey('recommendation.id'), primary_key=True)
    recommendation = db.relationship('Recommendation')

# --- New: DeliveryInfo Model ---
class DeliveryInfo(db.Model):
    __tablename__ = 'delivery_info'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # One-to-one relationship with Order:
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), unique=True, nullable=False)

    address = db.Column(db.String(255), nullable=False)
    apartment = db.Column(db.String(50), nullable=True)
    floor = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=False) # Marked as required in your model, so nullable=False
    longitude = db.Column(db.Float, nullable=False) # Marked as required in your model, so nullable=False

    def __repr__(self):
        return f"<DeliveryInfo {self.id} for Order {self.order_id}>"

# --- Updated: Order Model ---
class Order(db.Model):
    __tablename__ = 'order'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime, nullable=True)

    # Relationship to OrderItem (one-to-many)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    
    # Relationship to DeliveryInfo (one-to-one)
    # `uselist=False` indicates a one-to-one relationship
    # `cascade="all, delete-orphan"` ensures DeliveryInfo is managed with the Order
    delivery_info = db.relationship('DeliveryInfo', backref='order', uselist=False, lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.id}>"

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