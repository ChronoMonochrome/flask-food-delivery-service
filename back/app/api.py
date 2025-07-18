# app/api.py

import traceback
from flask import Blueprint, jsonify, current_app, request
from flask_restx import Api, Namespace, Resource, fields
from werkzeug.exceptions import HTTPException, InternalServerError
from app.models import (
    db, DeliveryInfo, MainCategory, Category, Product, ProductAddon, Addon, Recommendation,
    Order, OrderItem, ProductRecommendation, Cart, CartItem, CartAddon, CartRecommendation,
    WokBase, WokMeat, WokTopping, WokSauce, WOK_PRODUCT_CONSTRUCTOR_ID, WOK_CATEGORY_NAME
)
from app import iiko_service # Assuming this is your IIKO integration service
from sqlalchemy import distinct # Import distinct for unique values
from sqlalchemy.orm import joinedload
from datetime import datetime,  timedelta, timezone
from shapely.geometry import Point, Polygon, LineString
import json
import requests
from decimal import Decimal
from uuid import uuid4
import re

from .geojson import geojson_data
from .yookassa_service import yookassa_service

api_bp = Blueprint('api', __name__)

api = Api(api_bp, version='1.0', title='Mandarin Food Delivery API',
          description='A comprehensive API for Mandarin Food Delivery App', doc='/doc',
          catch_all_404s=True)

# --- Define a model for error responses ---
error_model = api.model('Error', {
    'message': fields.String(description='A descriptive error message'),
    'status': fields.Integer(description='HTTP status code'),
    'error_type': fields.String(description='Type of the error (e.g., "InternalServerError", "BadRequest")'),
    'details': fields.String(description='More specific details about the error (e.g., traceback in debug mode)', allow_null=True)
})

# --- Models ---
ingredient_item_model = api.model('IngredientItem', {
    'code': fields.String(description='Ingredient code', allow_null=True),
    'name': fields.String(required=True, description='Ingredient name')
})

# Update category_model to represent MainCategory
main_category_model = api.model('MainCategory', {
    'id': fields.String(required=True, description='Main Category ID'),
    'name': fields.String(required=True, description='Main Category name'),
    'icon': fields.String(description='Main Category icon (emoji)', allow_null=True),
    'color': fields.String(description='Main Category color (Tailwind CSS gradient classes)', allow_null=True),
    'description': fields.String(description='Main Category description', allow_null=True),
    'image_url': fields.String(description='Main Category image URL', allow_null=True)
})

addon_model = api.model('Addon', {
    'id': fields.String(required=True, description='Addon ID'),
    'group_name': fields.String(required=True, description='Addon group name'),
    'name': fields.String(required=True, description='Addon name'),
    'price': fields.Float(required=True, description='Addon price'),
    'image': fields.String(description='Addon image URL', allow_null=True)
})

cart_addon_response_model = api.model('CartAddonResponse', {
    'id': fields.String(required=True, description='ID of the addon'),
    'group_name': fields.String(description='The group this addon belongs to (e.g., "Sauces")', allow_null=True),
    'name': fields.String(required=True, description='Name of the addon'),
    'price': fields.Float(required=True, description='Price of the addon'),
    'image': fields.String(allow_null=True, description='Image URL of the addon'),
    'quantity': fields.Integer(required=True, description='Quantity of this specific addon for the cart item') # <-- New quantity field
})

recommendation_model = api.model('Recommendation', {
    'id': fields.String(required=True, description='Recommendation ID'),
    'name': fields.String(required=True, description='Recommendation name'),
    'price': fields.Float(required=True, description='Recommendation price'),
    'image': fields.String(description='Recommendation image URL', allow_null=True)
})

nutrition_model = api.model('Nutrition', {
    'calories': fields.Float(description='Energy in kcal', allow_null=False, default=0.0),
    'carbs': fields.Float(description='Carbohydrates in grams', allow_null=False, default=0.0),
    'fat': fields.Float(description='Fat in grams', allow_null=False, default=0.0),
    'proteins': fields.Float(description='Proteins in grams', allow_null=False, default=0.0)
})

product_model = api.model('Product', {
    'id': fields.String(required=True, description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description', allow_null=True),
    'price': fields.Float(required=True, description='Product price'),
    'image': fields.String(description='Product image URL', allow_null=True),
    'categoryId': fields.String(required=True, description='ID of the main category this product belongs to'),
    'iikoCategoryId': fields.String(required=True, description='ID of the iiko category this product belongs to'),
    'nutrition': fields.Nested(nutrition_model, description='Nutritional information', allow_null=False, default={
        "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0
    }),
    'ingredients': fields.List(fields.Nested(ingredient_item_model), description='List of ingredients', allow_null=True, default=[]),
    'availableAddons': fields.List(fields.Nested(addon_model), description='List of available addons for this product', allow_null=True, default=[]),
    'recommendations': fields.List(fields.Nested(recommendation_model), description='List of recommended products for this product', allow_null=True, default=[]),
    'isCustomizable': fields.Boolean(required=True, description='Indicates if the product is customizable (e.g., Wok)', default=False) # New field
})

# --- NEW: Request model for incoming POST /api/orders (FLAT) ---
request_order_payload_model = api.model('RequestOrderPayload', {
    'address': fields.String(required=True, description='Delivery address'),
    'apartment': fields.String(description='Apartment number', allow_null=True),
    'floor': fields.String(description='Floor number', allow_null=True),
    'phone': fields.String(required=True, description='Contact phone number'),
    'paymentMethod': fields.String(required=True, description='Payment method (e.g., cash, card)'),
    'comment': fields.String(description='Additional comments for delivery', allow_null=True),
    'latitude': fields.Float(required=True, description='Latitude for delivery'),
    'longitude': fields.Float(required=True, description='Longitude for delivery')
})

# --- Existing: Response models (NESTED) ---
delivery_info_model_new = api.model('DeliveryInfoNew', {
    'address': fields.String(required=True, description='Delivery address'),
    'apartment': fields.String(description='Apartment number', allow_null=True),
    'floor': fields.String(description='Floor number', allow_null=True),
    'phone': fields.String(required=True, description='Contact phone number'),
    'paymentMethod': fields.String(required=True, description='Payment method (e.g., cash, card)'),
    'comment': fields.String(description='Additional comments for delivery', allow_null=True),
    'latitude': fields.Float(required=True, description='Latitude for delivery'),
    'longitude': fields.Float(required=True, description='Longitude for delivery')
})

order_item_model = api.model('OrderItem', {
    'product': fields.Nested(product_model, description='Product details'),
    'quantity': fields.Integer(required=True, description='Quantity of the product'),
    'selectedAddons': fields.List(fields.Nested(addon_model), description='Selected addons for this product item', default=[]),
    'selectedRecommendations': fields.List(fields.Nested(recommendation_model), description='Selected recommendations for this product item', default=[])
})

order_model = api.model('Order', {
    'id': fields.String(required=True, description='Order ID'),
    'items': fields.List(fields.Nested(order_item_model), description='List of items in the order'),
    'total': fields.Float(required=True, description='Total price of the order'),
    'deliveryInfo': fields.Nested(delivery_info_model_new, required=True, description='Delivery information'),
    'status': fields.String(required=True, description='Current status of the order'),
    'createdAt': fields.DateTime(dt_format='iso8601', description='Timestamp of order creation'),
    'estimatedDelivery': fields.DateTime(dt_format='iso8601', description='Estimated delivery time', allow_null=True),
    'paymentUrl': fields.String(description='URL for online payment confirmation', attribute='confirmation_url', allow_null=True), # <--- ADDED THIS LINE
    'yookassaPaymentId': fields.String(description='Yookassa payment ID for online payments', allow_null=True), # <--- ADDED THIS LINE (if needed on frontend)
})

# --- Cart Models ---

# Helper function to get user ID from header
def get_telegram_user_id():
    user_id = request.headers.get('X-Telegram-User-ID')
    if not user_id:
        # Abort with 401 or 403 if user ID is mandatory for this endpoint
        api.abort(401, "X-Telegram-User-ID header is required.")
    return user_id

# Wok Customization Models
wok_component_model = api.model('WokComponent', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'price': fields.Float(required=True),
    'image': fields.String(allow_null=True)
})

custom_wok_request_model = api.model('CustomWokRequest', {
    'baseId': fields.String(required=True),
    'meatIds': fields.List(fields.String, required=True),
    'toppingIds': fields.List(fields.String, required=True),
    'sauceIds': fields.List(fields.String, required=True)
})

custom_wok_response_model = api.model('CustomWokResponse', {
    'base': fields.Nested(wok_component_model, required=True),
    'meats': fields.List(fields.Nested(wok_component_model), required=True),
    'toppings': fields.List(fields.Nested(wok_component_model), required=True),
    'sauces': fields.List(fields.Nested(wok_component_model), required=True)
})

# --- NEW: Simplified Product Model for Cart Items ---
product_summary_model = api.model('ProductSummary', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'description': fields.String(allow_null=True),
    'price': fields.Float(required=True),
    'image': fields.String(allow_null=True),
    'categoryId': fields.String(attribute='main_category_id', required=True),
    'nutrition': fields.Nested(nutrition_model),
    'ingredients': fields.List(fields.Nested(ingredient_item_model), description='List of ingredients', allow_null=True, default=[]),
    'isCustomizable': fields.Boolean
    # Removed 'availableAddons' and 'recommendations'
})
# --- END NEW MODEL ---

# --- MODIFIED: cart_item_response_model ---
cart_item_response_model = api.model('CartItemResponse', {
    'id': fields.String(required=True, description='Unique ID of the cart item'),
    'productId': fields.String(description='ID of the product', allow_null=True),
    # Flattened product details:
    'name': fields.String(description='Name of the product/custom item', required=True),
    'description': fields.String(description='Description of the product/custom item', allow_null=True),
    'image': fields.String(description='Image URL of the product/custom item', allow_null=True),
    'isCustomizable': fields.Boolean(description='Is the item customizable?'),
    #'categoryId': fields.String(description='Category ID of the product', allow_null=True),
    #'nutrition': fields.Nested(nutrition_model, description='Nutrition information', allow_null=True),
    #'ingredients': fields.List(fields.Nested(ingredient_item_model), description='List of ingredients', allow_null=True),

    'quantity': fields.Integer(required=True, description='Quantity of the item'),
    'priceTotal': fields.Float(required=True, description='Total price for this single cart item (base price + addons + recommendations)'), # NEW FIELD

    'selectedAddons': fields.List(fields.Nested(cart_addon_response_model), description='Selected addons for this item', default=[]),
    'selectedRecommendations': fields.List(fields.Nested(recommendation_model), description='Selected recommendations for this item', default=[]),
    #'customWok': fields.Nested(custom_wok_response_model, description='Wok customization details if applicable', allow_null=True),
    #'customName': fields.String(description='Custom name for the item (e.g., for Wok)', allow_null=True),
    #'customDescription': fields.String(description='Custom description for the item (e.g., for Wok)', allow_null=True),
    #'customPrice': fields.Float(description='Custom price for the item (e.g., for Wok)', allow_null=True), # Keep customPrice for internal calculations, but priceTotal is what client sees
    #'customImage': fields.String(description='Custom image for the item (e.g., for Wok)', allow_null=True)
})

cart_response_model = api.model('CartResponse', {
    'items': fields.List(fields.Nested(cart_item_response_model), description='List of items in the cart'),
    'total': fields.Float(required=True, description='Total price of the cart')
})

# **FIX FOR THE ERROR:** Define AddonRequest model separately, then use fields.Nested
addon_request_model = api.model('AddonRequest', {
    'id': fields.String(required=True),
    'quantity': fields.Integer(required=True, default=1)
})

# Request Models for Cart Operations
add_to_cart_request = api.model('AddToCartRequest', {
    'productId': fields.String(required=True, description='ID of the product to add'),
    'quantity': fields.Integer(description='Quantity to add (default 1)', default=1),
    'addons': fields.List(fields.Nested(addon_request_model), description='List of selected addon IDs and their quantities', default=[]),
    'recommendations': fields.List(fields.String, description='List of selected recommendation IDs', default=[]),
    'customWok': fields.Nested(custom_wok_request_model, description='Wok customization details if adding a custom Wok', allow_null=True),
    'customName': fields.String(description='Custom name for the item (e.g., for Wok)', allow_null=True),
    'customDescription': fields.String(description='Custom description for the item (e.g., for Wok)', allow_null=True),
    'customPrice': fields.Float(description='Custom price for the item (e.g., for Wok)', allow_null=True),
})

update_cart_item_request = api.model('UpdateCartItemRequest', {
    'itemId': fields.String(required=True, description='ID of the cart item to update'),
    'quantity': fields.Integer(required=True, description='New quantity for the item')
})

remove_from_cart_request = api.model('RemoveFromCartRequest', {
    'itemId': fields.String(required=True, description='ID of the cart item to remove')
})

# --- New Models for Addon Group Names ---

# Model for listing unique addon group names with a placeholder ID
addon_group_name_model = api.model('AddonGroupName', {
    'name': fields.String(required=True, description='Unique addon group name')
})

# Namespace for addon-related operations
addon_ns = api.namespace('addons', description='Addon related operations')

@addon_ns.route('/groups')
class AddonGroupList(Resource):
    @addon_ns.doc('list_addon_groups')
    def get(self):
        """
        List all unique addon group names.
        Returns a list of objects, each with a placeholder ID and the group name.
        """
        unique_group_names = db.session.query(distinct(Addon.group_name)).all()
        # Transform the list of tuples into a list of dictionaries

        result = [
            {'name': group_name[0]}
            for group_name in unique_group_names
        ]
        return jsonify(result)

@addon_ns.route('/by_group_name/<string:group_name>')
class AddonsByGroupName(Resource):
    @addon_ns.doc('get_addons_by_group_name')
    def get(self, group_name):
        """
        Returns a list of addons belonging to a specific group name.
        """
        addons = Addon.query.filter_by(group_name=group_name).all()
        if not addons:
            addon_ns.abort(404, message=f"No addons found for group name '{group_name}'")
        return jsonify(api.marshal(addons, addon_model))

# Helper to calculate individual cart item price
def calculate_item_price(product, selected_addons_data, selected_recommendations_data, custom_wok_data, custom_price):
    item_price = Decimal('0.00')

    if custom_price is not None:
        item_price = Decimal(str(custom_price))
    elif product:
        item_price = Decimal(str(product.price))

    # Add addon prices
    for addon_data in selected_addons_data:
        addon_id = addon_data['id']
        addon_quantity = addon_data.get('quantity', 1)
        addon = Addon.query.get(addon_id)
        if addon:
            item_price += Decimal(str(addon.price)) * addon_quantity

    # Add recommendation prices (only if not a custom WOK, as per frontend logic)
    if not custom_wok_data:
        for rec_id in selected_recommendations_data:
            rec = Recommendation.query.get(rec_id)
            if rec:
                item_price += Decimal(str(rec.price))

    # Add custom Wok component prices if it's a custom Wok (overrides product price)
    if custom_wok_data:
        if 'baseId' in custom_wok_data:
            base = WokBase.query.get(custom_wok_data['baseId'])
            if base:
                item_price += Decimal(str(base.price))
        for meat_id in custom_wok_data.get('meatIds', []):
            meat = WokMeat.query.get(meat_id)
            if meat:
                item_price += Decimal(str(meat.price))
        for topping_id in custom_wok_data.get('toppingIds', []):
            topping = WokTopping.query.get(topping_id)
            if topping:
                item_price += Decimal(str(topping.price))
        for sauce_id in custom_wok_data.get('sauceIds', []):
            sauce = WokSauce.query.get(sauce_id)
            if sauce:
                item_price += Decimal(str(sauce.price))

    return item_price

def get_or_create_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart

def update_cart_total(cart):
    total = Decimal('0.00')
    for item in cart.items:
        # Load product if available, else use custom price
        product = item.product
        current_app.logger.debug(f"Calculating price for cart item {item.id}: Product ID: {item.product_id}, Custom Wok: {item.custom_wok_data is not None}")

        # Re-fetch selected addons and recommendations to get current prices
        selected_addons_for_calc = []
        for ca in item.selected_addons:
            selected_addons_for_calc.append({'id': ca.addon_id, 'quantity': ca.quantity})

        selected_recommendations_for_calc = []
        for cr in item.selected_recommendations:
            selected_recommendations_for_calc.append(cr.recommendation_id)

        item_price_unit = calculate_item_price(
            product,
            selected_addons_for_calc,
            selected_recommendations_for_calc,
            item.custom_wok_data,
            item.custom_price
        )
        total += item_price_unit * item.quantity
    cart.total = total
    db.session.commit()

## Category Endpoints

@api.route('/categories')
class CategoryList(Resource):
    def get(self):
        """Get all categories"""
        # Define the prefixes to exclude
        EXCLUDED_PREFIXES = ["Доставка", "Рекомендованные", "Добавки", "Соусы"]

        # Fetch all categories from the database, ordered by display_order
        all_categories = MainCategory.query.order_by(MainCategory.display_order).all()

        # Filter the categories based on the excluded prefixes
        filtered_categories = []
        for category in all_categories:
            # Check if the category name starts with any of the excluded prefixes
            if not any(category.name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                filtered_categories.append(category)
        marshaled_categories = api.marshal(filtered_categories, main_category_model)
        return jsonify(marshaled_categories)

## Product Endpoints
@api.route('/products')
class ProductList(Resource):
    @api.param('categoryId', 'Filter products by category ID')
    def get(self):
        """Get all products, optionally filtered by category"""
        category_id = api.parser().add_argument('categoryId', type=str, location='args').parse_args()['categoryId']

        query = Product.query.filter_by(is_hidden=False).options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).order_by(Product.categoryId) # Order by IIKO category

        if category_id:
            query = query.filter_by(main_category_id=category_id)

        products = query.all()
        
        # --- NEW LOGIC FOR REORDERING WOK PRODUCTS ---
        wok_category = MainCategory.query.filter_by(name=WOK_CATEGORY_NAME).first()

        # Check if the requested category is the Wok category AND
        # if the Wok category was actually found in the database
        if wok_category and category_id == str(wok_category.id): # Ensure ID comparison is string to string
            wok_constructor_product = None
            other_products = []

            # Separate the constructor product from others
            for product in products:
                if str(product.id) == WOK_PRODUCT_CONSTRUCTOR_ID: # Ensure ID comparison is string to string
                    wok_constructor_product = product
                else:
                    other_products.append(product)

            # Reconstruct the products list with the constructor first
            if wok_constructor_product:
                products = [wok_constructor_product] + other_products
            else:
                # If constructor product wasn't found, just use the original list (or other_products)
                # This case might happen if the ID is wrong or product is hidden/deleted
                current_app.logger.warning(f"Wok constructor product with ID {WOK_PRODUCT_CONSTRUCTOR_ID} not found in Wok category.")
                products = other_products # Or just `products` if you want to keep original order if constructor is missing

        # --- END NEW LOGIC ---
        marshaled_products = []
        for product in products:
            nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
            for key in ["calories", "carbs", "fat", "proteins"]:
                if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                    nutrition_data_for_marshal[key] = 0.0
                if isinstance(nutrition_data_for_marshal[key], Decimal):
                    nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

            processed_ingredients = product.ingredients if product.ingredients is not None else []
            cleaned_ingredients = []
            for ing in processed_ingredients:
                if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                    cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
                else:
                    current_app.logger.warning(f"Skipping malformed ingredient for product {product.id}: {ing!r}")

            marshaled_recommendations = [
                api.marshal(pr.recommendation, recommendation_model)
                for pr in product.recommendations if pr.recommendation
            ]

            marshaled_available_addons = [
                api.marshal(pa.addon, addon_model)
                for pa in product.available_addons if pa.addon
            ]

            product_for_marshal = {
                'id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
                'image': product.image,
                'categoryId': str(product.main_category_id), # This is now the MainCategory ID
                'iikoCategoryId': str(product.categoryId), # IIKO category id
                'nutrition': nutrition_data_for_marshal,
                'ingredients': cleaned_ingredients,
                'availableAddons': marshaled_available_addons,
                'recommendations': marshaled_recommendations,
                'isCustomizable': product.is_customizable # Include new field
            }
            marshaled_products.append(api.marshal(product_for_marshal, product_model))

        return jsonify(marshaled_products)

@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, product_id):
        """Get a single product by ID"""
        product = Product.query.options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get_or_404(product_id)

        if product.is_hidden:
            api.abort(404, "Product not found or is hidden.")

        nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
        for key in ["calories", "carbs", "fat", "proteins"]:
            if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                nutrition_data_for_marshal[key] = 0.0
            if isinstance(nutrition_data_for_marshal[key], Decimal):
                nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

        processed_ingredients = product.ingredients if product.ingredients is not None else []
        cleaned_ingredients = []
        for ing in processed_ingredients:
            if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
            else:
                current_app.logger.warning(f"Skipping malformed ingredient for product {product.id}: {ing!r}")

        marshaled_recommendations = [
            api.marshal(pr.recommendation, recommendation_model)
            for pr in product.recommendations if pr.recommendation
        ]

        marshaled_available_addons = [
            api.marshal(pa.addon, addon_model)
            for pa in product.available_addons if pa.addon
        ]

        product_for_marshal = {
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
            'image': product.image,
            'categoryId': str(product.main_category_id),
            'iikoCategoryId': str(product.categoryId),
            'nutrition': nutrition_data_for_marshal,
            'ingredients': cleaned_ingredients,
            'availableAddons': marshaled_available_addons,
            'recommendations': marshaled_recommendations,
            'isCustomizable': product.is_customizable # Include new field
        }
        return product_for_marshal


## Order Endpoints

@api.route('/orders')
class OrderList(Resource):
    @api.marshal_with(order_model, as_list=True) # Use marshal_list_with for lists of orders
    def get(self):
        """Get all orders"""
        orders = Order.query.options(
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.available_addons)
            .joinedload(ProductAddon.addon), # Assuming ProductAddon.addon is the correct path
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.recommendations)
            .joinedload(ProductRecommendation.recommendation), # Assuming ProductRecommendation.recommendation is the correct path
            joinedload(Order.delivery_info) # Eager load delivery info
        ).all()

        serialized_orders = []
        for order in orders:
            items_data = []
            for item in order.items:
                product_obj = item.product

                fetched_addons = []
                if item.selected_addons_ids:
                    addons_from_db = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                    # Ensure addon_model has 'group_name' and 'image' if you want them in response
                    fetched_addons = [api.marshal(addon, addon_model) for addon in addons_from_db]

                fetched_recommendations = []
                if item.selected_recommendation_ids:
                    recs_from_db = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
                    fetched_recommendations = [api.marshal(rec, recommendation_model) for rec in recs_from_db]

                # Manually construct product_marshaled to match product_model structure
                product_marshaled = {
                    'id': str(product_obj.id),
                    'name': product_obj.name,
                    'description': product_obj.description,
                    'price': float(product_obj.price) if isinstance(product_obj.price, Decimal) else product_obj.price,
                    'image': product_obj.image,
                    'categoryId': str(product_obj.main_category_id), # Corrected from product_obj.categoryId
                    'iikoCategoryId': str(product_obj.categoryId), # Original categoryId from IIKO
                    'nutrition': product_obj.nutrition, # Assuming JSON directly
                    'ingredients': product_obj.ingredients, # Assuming JSON directly
                    'availableAddons': [api.marshal(pa.addon, addon_model) for pa in product_obj.available_addons if pa.addon],
                    'recommendations': [api.marshal(pr.recommendation, recommendation_model) for pr in product_obj.recommendations if pr.recommendation],
                    'isCustomizable': product_obj.is_customizable
                }
                marshaled_product_in_order_item = api.marshal(product_marshaled, product_model)

                items_data.append({
                    'product': marshaled_product_in_order_item,
                    'quantity': item.quantity,
                    'selectedAddons': fetched_addons,
                    'selectedRecommendations': fetched_recommendations
                })

            # Reconstruct the nested deliveryInfo for the response
            delivery_info_obj = order.delivery_info
            delivery_info_for_response = {}
            if delivery_info_obj:
                delivery_info_for_response = api.marshal({
                    'address': delivery_info_obj.address,
                    'apartment': delivery_info_obj.apartment,
                    'floor': delivery_info_obj.floor,
                    'phone': delivery_info_obj.phone,
                    'paymentMethod': delivery_info_obj.payment_method,
                    'comment': delivery_info_obj.comment,
                    'latitude': delivery_info_obj.latitude,
                    'longitude': delivery_info_obj.longitude
                }, delivery_info_model_new)


            serialized_orders.append({
                'id': str(order.id),
                'items': items_data,
                'total': float(order.total) if isinstance(order.total, Decimal) else order.total,
                'deliveryInfo': delivery_info_for_response, # Nested object for response
                'status': order.status,
                'createdAt': order.created_at.isoformat(),
                'estimatedDelivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None
            })
        return serialized_orders


    @api.expect(request_order_payload_model) # <-- Use the FLAT request model for input
    @api.marshal_with(order_model, code=201) # <-- Still marshal output with the NESTED order_model
    def post(self):
        """Create a new order and send it to IIKO."""
        user_id = get_telegram_user_id()
        data = api.payload # This contains the flat delivery fields from the frontend

        # --- Validate delivery coordinates and get delivery cost ---
        load_delivery_areas() # Ensure areas are loaded
        global VALID_DELIVERY_AREAS, DELIVERY_COST_MOCK

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not latitude or not longitude:
            api.abort(400, "Latitude and Longitude are required for delivery.")

        point = Point(longitude, latitude)
        is_in_delivery_area = False
        for area_polygon in VALID_DELIVERY_AREAS:
            if area_polygon.contains(point):
                is_in_delivery_area = True
                break

        if not is_in_delivery_area:
            api.abort(404, "The provided coordinates are outside our valid delivery areas.")

        delivery_cost = DELIVERY_COST_MOCK # Use the mock delivery cost

        # --- Dynamic retrieval of Organization ID and Terminal Group ID ---
        iiko_token = iiko_service.get_iiko_token()
        if not iiko_token:
            current_app.logger.error("Failed to get IIKO access token for order creation.")
            api.abort(500, "Failed to connect to external ordering system (IIKO).")

        organization_id = None
        terminal_group_id = None
        selected_iiko_payment_type = None

        try:
            organizations = iiko_service.get_organizations(iiko_token)
            if organizations:
                organization_id = organizations[0].get("id")
                current_app.logger.info(f"Using IIKO Organization ID: {organization_id}")
            else:
                current_app.logger.error("No organizations found from IIKO API.")
                api.abort(500, "Could not determine organization ID for external order.")

            terminal_groups = iiko_service.get_terminal_groups(organization_id, iiko_token)
            if terminal_groups and terminal_groups[0].get("items"):
                terminal_group_id = terminal_groups[0]["items"][0].get("id")
                current_app.logger.info(f"Using IIKO Terminal Group ID: {terminal_group_id}")
            else:
                current_app.logger.error(f"No terminal groups found for organization {organization_id} from IIKO API.")
                api.abort(500, "Could not determine terminal group ID for external order.")

            # --- Fetch Payment Types ---
            iiko_payment_types = iiko_service.get_payment_types([organization_id], iiko_token)
            if not iiko_payment_types:
                current_app.logger.error(f"No payment types found for organization {organization_id} from IIKO API.")
                api.abort(500, "Could not determine payment types for external order.")

            client_payment_method = data['paymentMethod'].lower()

            for pt in iiko_payment_types:
                pt_kind = pt.get('paymentTypeKind', '').lower()
                pt_code = pt.get('code', '').lower()

                if client_payment_method == "cash" and pt_kind == "cash":
                    selected_iiko_payment_type = pt
                    break
                elif client_payment_method == "card" and pt_kind == "card":
                    selected_iiko_payment_type = pt
                    break
                elif client_payment_method == "card" and (pt_kind in ["loyaltycard", "external"] or pt_code == "bank"):
                    selected_iiko_payment_type = pt
                    break
                elif client_payment_method == "online":
                    selected_iiko_payment_type = pt
                    break

            if not selected_iiko_payment_type:
                current_app.logger.warning(f"Could not find a specific IIKO payment type for client method '{client_payment_method}'. Using the first available payment type as fallback.")
                selected_iiko_payment_type = iiko_payment_types[0]

            current_app.logger.info(f"Using IIKO Payment Type: ID='{selected_iiko_payment_type.get('id')}', Name='{selected_iiko_payment_type.get('name')}', Kind='{selected_iiko_payment_type.get('paymentTypeKind')}', Code='{selected_iiko_payment_type.get('code')}'")

        except Exception as e:
            current_app.logger.error(f"Error fetching IIKO organization/terminal group/payment type IDs: {e}", exc_info=True)
            api.abort(500, f"Failed to initialize external ordering system: {str(e)}")
        # --- End Dynamic retrieval ---

        calculated_total = Decimal('0.00')
        order_items_to_add = []
        iiko_order_items = []

        # --- Retrieve items from the user's cart ---
        cart = get_or_create_cart(user_id)
        if not cart.items:
            api.abort(400, "Cart is empty. Please add items before creating an order.")

        # Eager load cart items and their related products/addons/recommendations
        # This ensures all necessary data is available for calculating total and IIKO payload
        cart_with_items = db.session.query(Cart).filter_by(user_id=user_id).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.selected_addons).joinedload(CartAddon.addon),
            joinedload(Cart.items).joinedload(CartItem.selected_recommendations).joinedload(CartRecommendation.recommendation)
        ).first()

        if not cart_with_items or not cart_with_items.items:
            api.abort(400, "Cart is empty or could not load cart items.")


        for cart_item in cart_with_items.items:
            item_price = Decimal('0.00')
            product = None
            product_name = None # For custom wok
            product_id_for_iiko = None # For custom wok

            if cart_item.product_id:
                product = Product.query.get(cart_item.product_id) # Product should already be loaded via joinedload
                if not product:
                    current_app.logger.warning(f"Product with ID {cart_item.product_id} not found for cart item {cart_item.id}. Skipping.")
                    continue # Skip this item if product is missing
                item_price += Decimal(str(product.price))
            elif cart_item.custom_wok_data:
                item_price += Decimal(str(cart_item.custom_price)) if cart_item.custom_price else Decimal('0.00')
                product_name = cart_item.custom_name if cart_item.custom_name else "Custom Wok"
                product_id_for_iiko = "GENERIC_WOK_PRODUCT_ID_IIKO" # Placeholder, replace with actual IIKO ID
            else:
                current_app.logger.warning(f"Cart item {cart_item.id} has no product or custom wok data. Skipping.")
                continue # Skip malformed cart items


            iiko_modifiers = []

            for cart_addon in cart_item.selected_addons:
                addon = cart_addon.addon # Already loaded via joinedload
                if addon:
                    item_price += Decimal(str(addon.price)) * cart_addon.quantity
                    iiko_modifiers.append({
                        "id": addon.iiko_addon_id,
                        "type": "Product", # Assuming IIKO treats addons as 'Product' modifiers
                        "amount": cart_addon.quantity
                    })
                else:
                    current_app.logger.warning(f"Selected addon with ID {cart_addon.addon_id} not found for cart item {cart_item.id}.")

            for cart_rec in cart_item.selected_recommendations:
                recommendation = cart_rec.recommendation # Already loaded via joinedload
                if recommendation:
                    item_price += Decimal(str(recommendation.price))
                    iiko_modifiers.append({
                        "id": recommendation.iiko_recommendation_id,
                        "type": "Product", # Assuming IIKO treats recommendations as 'Product' modifiers
                        "amount": 1
                    })
                else:
                    current_app.logger.warning(f"Selected recommendation with ID {cart_rec.recommendation_id} not found for cart item {cart_item.id}.")

            calculated_total += item_price * Decimal(str(cart_item.quantity))

            # Prepare for database persistence
            order_items_to_add.append(OrderItem(
                product_id=product.id if product else None,
                quantity=cart_item.quantity,
                selected_addons_ids=[ca.addon_id for ca in cart_item.selected_addons],
                selected_recommendation_ids=[cr.recommendation_id for cr in cart_item.selected_recommendations]
            ))

            # Prepare for IIKO payload
            iiko_order_items.append({
                "productId": product.iiko_product_id if product else product_id_for_iiko,
                "productCode": product.iiko_product_id if product else product_id_for_iiko,
                "name": product.name if product else product_name,
                "amount": cart_item.quantity,
                "price": float(item_price),
                "modifiers": iiko_modifiers,
                "comboId": None,
                "positionId": str(uuid4())
            })

        # Add delivery cost to the total
        final_total = calculated_total + delivery_cost
        current_app.logger.info(f"Order calculated total (without delivery): {calculated_total}, with delivery: {final_total}")

        # Parse city from address. This is a simple regex, might need refinement.
        full_address = data['address']
        city_match = re.search(r',\s*([^,]+?)(?:\s*\d{5})?\s*$', full_address)
        city = "Default City" # Fallback
        if city_match:
            city = city_match.group(1).strip()
        elif full_address:
            parts = full_address.split(',')
            if len(parts) > 1:
                city = parts[-1].strip()
            else:
                city = full_address.split()[-1] if full_address.split() else "Default City"

        # Create DeliveryInfo object from the flat incoming data
        delivery_info_obj = DeliveryInfo(
            address=data['address'],
            apartment=data.get('apartment'),
            floor=data.get('floor'),
            phone=data['phone'],
            payment_method=data['paymentMethod'],
            comment=data.get('comment'),
            latitude=data['latitude'],
            longitude=data['longitude']
        )
        # db.session.add(delivery_info_obj) # Will be added via cascade from Order

        # Store new order in DB
        new_order = Order(
            id=str(uuid4()),
            total=final_total,
            status='pending',
            created_at=datetime.utcnow(),
            # Link DeliveryInfo to Order
            delivery_info=delivery_info_obj # Assign the object directly
        )
        db.session.add(new_order) # Add the order (which will cascade add delivery_info)
        db.session.flush() # Flush to get new_order.id if it's auto-generated

        for item in order_items_to_add:
            item.order_id = new_order.id
            db.session.add(item)

        try:
            if client_payment_method == 'online':
                # --- Интеграция с ЮKassa ---
                if not yookassa_service:
                    api.abort(500, "Сервис ЮKassa не настроен.")

                # FRONTEND_ORDER_RETURN_URL должен быть URL на вашем фронтенде, куда ЮKassa перенаправит пользователя после оплаты
                frontend_return_url = current_app.config.get('FRONTEND_ORDER_RETURN_URL', 'https://your-frontend-domain.com/order-status')

                payment_description = f"Заказ #{new_order.id} из {new_order.delivery_info.address}"
                yookassa_response = yookassa_service.create_payment(
                    amount=new_order.total,
                    description=payment_description,
                    order_id=new_order.id, # Используем наш внутренний ID заказа как метаданные и ключ идемпотентности
                    return_url=frontend_return_url
                )

                if yookassa_response and yookassa_response.get('confirmation', {}).get('confirmation_url'):
                    new_order.yookassa_payment_id = yookassa_response['id']
                    new_order.confirmation_url = yookassa_response['confirmation']['confirmation_url']
                    new_order.status = 'pending_payment' # Устанавливаем статус в ожидание оплаты
                    current_app.logger.info(f"Платеж ЮKassa инициирован для заказа {new_order.id}. URL подтверждения: {new_order.confirmation_url}")
                else:
                    new_order.status = 'payment_initiation_failed'
                    current_app.logger.error(f"Не удалось получить confirmation_url от ЮKassa для заказа {new_order.id}. Ответ: {yookassa_response}")
                    api.abort(500, "Не удалось инициировать платеж по карте.")
                    
            else:
                # --- Интеграция с IIKO для других типов платежей ---
                iiko_order_data_for_payload = {
                    "id": new_order.id,
                    "externalNumber": f"WEB-{new_order.id.split('-')[0]}",
                    "phone": new_order.delivery_info.phone,
                    "items": iiko_order_items,
                    "deliveryPoint": {
                        "address": {
                            "street": new_order.delivery_info.address,
                            "city": city,
                        },
                        "coordinates": {
                            "latitude": new_order.delivery_info.latitude,
                            "longitude": new_order.delivery_info.longitude,
                        }
                    },
                    "payments": [
                        {
                            "sum": float(final_total),
                            "paymentTypeKind": selected_iiko_payment_type.get('paymentTypeKind'),
                            "paymentTypeId": selected_iiko_payment_type.get('id'),
                            "isProcessedExternally": selected_iiko_payment_type.get('paymentProcessingType') == 'External',
                            "isFiscalizedExternally": False,
                            "isPrepay": False
                        }
                    ],
                    "comment": new_order.delivery_info.comment,
                    "completeBefore": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                }

                iiko_response = iiko_service.create_delivery_order(
                    organization_id=organization_id,
                    terminal_group_id=terminal_group_id,
                    order=iiko_order_data_for_payload,
                    create_order_settings={"transportToFrontTimeout": 0}
                )

                if iiko_response and iiko_response.get('orderId'):
                    #new_order.status = 'sent_to_iiko'
                    current_app.logger.info(f"Заказ {new_order.id} успешно отправлен в IIKO. IIKO Order ID: {iiko_response['orderId']}")
                else:
                    #new_order.status = 'iiko_send_failed'
                    current_app.logger.error(f"Не удалось отправить заказ {new_order.id} в IIKO. Ответ: {iiko_response}")
                    api.abort(500, f"Не удалось отправить заказ в IIKO: {iiko_response.get('error', 'Неизвестная ошибка')}")

            # Очищаем корзину после успешной обработки заказа (будь то инициирование платежа или отправка в IIKO)
            db.session.delete(cart_with_items)

        except Exception as e:
            db.session.rollback() # Откатываем транзакцию в случае ошибки
            current_app.logger.error(f"Ошибка при обработке платежа/интеграции с IIKO для заказа: {e}", exc_info=True)
            api.abort(500, f"Заказ создан внутренне, но произошел сбой платежа или интеграции с внешней системой: {str(e)}")

        db.session.commit() # Коммитим все изменения в базу данных

        # Загружаем созданный заказ со всеми связями для маршалинга
        created_order = Order.query.options(
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.available_addons)
            .joinedload(ProductAddon.addon),
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.recommendations)
            .joinedload(ProductRecommendation.recommendation),
            joinedload(Order.delivery_info)
        ).get(new_order.id)

        return created_order, 201

## Addon Endpoints
@api.route('/addons')
class AddonList(Resource):
    def get(self):
        """Get all addons"""
        addons_data = Addon.query.all()
        valid_addons = [api.marshal(addon, addon_model) for addon in addons_data if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None]
        for addon in addons_data:
            if not (addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None):
                print(f"WARNING: Skipping malformed addon in AddonList: ID={getattr(addon, 'id', 'N/A')}, Name={repr(getattr(addon, 'name', 'N/A'))} (Type: {type(getattr(addon, 'name', None))}), Price={getattr(addon, 'price', 'N/A')}")
        return jsonify(valid_addons)

## Recommendation Endpoints

@api.route('/recommendations')
class RecommendationList(Resource):
    def get(self):
        """Get all recommendations"""
        recommendations_data = Recommendation.query.all()
        valid_recommendations = [api.marshal(rec, recommendation_model) for rec in recommendations_data if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)]
        for rec in recommendations_data:
            if not (rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)):
                print(f"WARNING: Skipping malformed recommendation in RecommendationList: ID={getattr(rec, 'id', 'N/A')}, Name={repr(getattr(rec, 'name', 'N/A'))} (Type: {type(getattr(rec, 'name', None))}), Price={getattr(rec, 'price', 'N/A')})")
        return jsonify(valid_recommendations)


## Cart Endpoints

@api.route('/cart')
class CartResource(Resource):
    def get(self):
        """Get the current user's cart"""
        user_id = get_telegram_user_id()
        cart = get_or_create_cart(user_id)

        # Eager load related data for cart items
        # (This part of the query remains the same)
        cart = db.session.query(Cart).filter_by(user_id=user_id).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.selected_addons).joinedload(CartAddon.addon),
            joinedload(Cart.items).joinedload(CartItem.selected_recommendations).joinedload(CartRecommendation.recommendation)
        ).first()

        if not cart:
            return {'items': [], 'total': 0.0}, 200

        marshaled_items = []
        for item in cart.items:
            # Initialize fields that might come from product or custom_wok
            item_id = str(item.id)
            product_id = str(item.product_id) if item.product_id else None
            item_name = None
            item_description = None
            item_image = None
            item_is_customizable = False
            item_category_id = None
            item_nutrition = {}
            item_ingredients = []
            item_base_price = Decimal('0.0') # Base price of the product or custom wok

            # Determine fields based on whether it's a custom wok or a regular product
            if item.custom_wok_data:
                # For custom wok, use its custom fields or derive from components
                item_name = item.custom_name
                item_description = item.custom_description
                item_image = item.custom_image
                item_is_customizable = True # A custom wok is inherently customizable
                item_base_price = Decimal(str(item.custom_price)) if item.custom_price is not None else Decimal('0.0')

                # You might want to build a more detailed description from wok components here if customDescription is null
                if not item_description:
                    base = WokBase.query.get(item.custom_wok_data.get('baseId'))
                    meats = [WokMeat.query.get(mid) for mid in item.custom_wok_data.get('meatIds', [])]
                    toppings = [WokTopping.query.get(tid) for tid in item.custom_wok_data.get('toppingIds', [])]
                    sauces = [WokSauce.query.get(sid) for sid in item.custom_wok_data.get('sauceIds', [])]
                    # Example: generate a description like "Rice with Chicken, Mushrooms, Teriyaki"
                    desc_parts = []
                    if base: desc_parts.append(base.name)
                    if meats: desc_parts.append(", ".join([m.name for m in meats]))
                    if toppings: desc_parts.append(", ".join([t.name for t in toppings]))
                    if sauces: desc_parts.append(", ".join([s.name for s in sauces]))
                    item_description = "Wok: " + " with ".join(filter(None, desc_parts)) if desc_parts else "Custom Wok"


            elif item.product:
                # For regular products, use product details
                item_name = item.product.name
                item_description = item.product.description
                item_image = item.product.image
                item_is_customizable = item.product.is_customizable
                item_category_id = str(item.product.main_category_id) if item.product.main_category_id else None
                item_nutrition = item.product.nutrition if isinstance(item.product.nutrition, dict) else {}
                item_ingredients = item.product.ingredients if item.product.ingredients is not None else []
                item_base_price = Decimal(str(item.product.price)) if item.product.price is not None else Decimal('0.0')

                # Ensure nutrition values are floats
                for key in ["calories", "carbs", "fat", "proteins"]:
                    if key not in item_nutrition or item_nutrition[key] is None:
                        item_nutrition[key] = 0.0
                    if isinstance(item_nutrition[key], Decimal):
                        item_nutrition[key] = float(item_nutrition[key])

                # Clean ingredients for the model
                cleaned_ingredients = []
                for ing in item_ingredients:
                    if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                        cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
                item_ingredients = cleaned_ingredients

            # Calculate priceTotal for the item
            current_item_total_price = item_base_price * item.quantity

            marshaled_selected_addons = []
            for ca in item.selected_addons:
                if ca.addon:
                    addon_price = Decimal(str(ca.addon.price)) if ca.addon.price is not None else Decimal('0.0')
                    current_item_total_price += addon_price * ca.quantity
                    marshaled_selected_addons.append({
                        'id': str(ca.addon.id),
                        'group_name': ca.addon.group_name,
                        'name': ca.addon.name,
                        'price': float(addon_price),
                        'image': ca.addon.image,
                        'quantity': ca.quantity
                    })

            marshaled_selected_recommendations = []
            for cr in item.selected_recommendations:
                if cr.recommendation:
                    rec_price = Decimal(str(cr.recommendation.price)) if cr.recommendation.price is not None else Decimal('0.0')
                    current_item_total_price += rec_price
                    marshaled_selected_recommendations.append(api.marshal(cr.recommendation, recommendation_model))

            # Handle custom Wok details
            custom_wok_details = None
            if item.custom_wok_data:
                base = WokBase.query.get(item.custom_wok_data.get('baseId'))
                meats = [WokMeat.query.get(mid) for mid in item.custom_wok_data.get('meatIds', [])]
                toppings = [WokTopping.query.get(tid) for tid in item.custom_wok_data.get('toppingIds', [])]
                sauces = [WokSauce.query.get(sid) for sid in item.custom_wok_data.get('sauceIds', [])]

                custom_wok_details = api.marshal({
                    'base': api.marshal(base, wok_component_model) if base else None,
                    'meats': [api.marshal(m, wok_component_model) for m in meats if m],
                    'toppings': [api.marshal(t, wok_component_model) for t in toppings if t],
                    'sauces': [api.marshal(s, wok_component_model) for s in sauces if s],
                }, custom_wok_response_model)

            marshaled_items.append({
                'id': item_id,
                'productId': product_id,
                'name': item_name,
                'description': item_description,
                'image': item_image,
                'isCustomizable': item_is_customizable,
                #'categoryId': item_category_id,
                #'nutrition': item_nutrition,
                #'ingredients': item_ingredients,
                'quantity': item.quantity,
                'priceTotal': float(current_item_total_price), # Use the calculated total price for this item
                'selectedAddons': marshaled_selected_addons,
                'selectedRecommendations': marshaled_selected_recommendations,
                #'customWok': custom_wok_details,
                #'customName': item.custom_name, # These are raw custom fields, not what frontend displays directly
                #'customDescription': item.custom_description,
                #'customPrice': float(item.custom_price) if item.custom_price is not None else None,
                #'customImage': item.custom_image
            })

        update_cart_total(cart) # Ensure cart.total is updated
        return jsonify(api.marshal({
            'items': marshaled_items,
            'total': float(cart.total)
        }, cart_response_model))


@api.route('/cart/add')
class AddToCartResource(Resource):
    @api.expect(add_to_cart_request)
    @api.marshal_with(cart_response_model, code=201)
    def post(self):
        """Add an item to the cart or increment quantity if it exists."""
        user_id = get_telegram_user_id()
        data = api.payload
        product_id = data.get('productId')
        quantity_to_add = data.get('quantity', 1)
        addons_data = data.get('addons', []) # [{'id': 'addon_id', 'quantity': 1}]
        recommendation_ids = data.get('recommendations', [])
        custom_wok_data = data.get('customWok')
        custom_name = data.get('customName')
        custom_description = data.get('customDescription')
        custom_price = data.get('customPrice')

        current_app.logger.debug(f"Received add to cart request: {data}")

        cart = get_or_create_cart(user_id)

        product = None
        if product_id:
            product = Product.query.get(product_id)
            if not product:
                api.abort(404, "Product not found.")

        is_custom_item = custom_wok_data is not None

        existing_item = None
        for item in cart.items:
            if not is_custom_item and item.product_id == product_id:
                current_addons = sorted([{'id': ca.addon_id, 'quantity': ca.quantity} for ca in item.selected_addons], key=lambda x: x['id'])
                request_addons = sorted(addons_data, key=lambda x: x['id'])
                addons_match = (current_addons == request_addons)

                current_recs = sorted([cr.recommendation_id for cr in item.selected_recommendations])
                request_recs = sorted(recommendation_ids)
                recs_match = (current_recs == request_recs)

                if addons_match and recs_match and item.custom_wok_data is None:
                    existing_item = item
                    break
            elif is_custom_item and item.custom_wok_data is not None:
                if item.custom_wok_data == custom_wok_data:
                    if item.custom_name == custom_name and \
                       item.custom_description == custom_description and \
                       item.custom_price == (Decimal(str(custom_price)) if custom_price is not None else None):
                        existing_item = item
                        break

        if existing_item:
            existing_item.quantity += quantity_to_add
        else:
            new_cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id if not is_custom_item else None,
                quantity=quantity_to_add,
                custom_wok_data=custom_wok_data,
                custom_name=custom_name,
                custom_description=custom_description,
                custom_price=Decimal(str(custom_price)) if custom_price is not None else None,
                custom_image=product.image if product and is_custom_item else None
            )
            db.session.add(new_cart_item)
            db.session.flush()

            for addon_data in addons_data:
                addon_obj = Addon.query.get(addon_data['id'])
                if addon_obj:
                    cart_addon = CartAddon(
                        cart_item_id=new_cart_item.id,
                        addon_id=addon_obj.id,
                        quantity=addon_data.get('quantity', 1)
                    )
                    db.session.add(cart_addon)
                else:
                    current_app.logger.warning(f"Addon with ID {addon_data['id']} not found.")

            for rec_id in recommendation_ids:
                rec_obj = Recommendation.query.get(rec_id)
                if rec_obj:
                    cart_rec = CartRecommendation(
                        cart_item_id=new_cart_item.id,
                        recommendation_id=rec_obj.id
                    )
                    db.session.add(cart_rec)
                else:
                    current_app.logger.warning(f"Recommendation with ID {rec_id} not found.")

        db.session.commit()
        update_cart_total(cart)

        # Corrected line: Instantiate CartResource and call its get method
        updated_cart_data = CartResource().get() 
        return api.marshal(updated_cart_data, cart_response_model), 201

@api.route('/cart/update')
class UpdateCartItemResource(Resource):
    @api.expect(update_cart_item_request)
    @api.marshal_with(cart_response_model)
    def put(self):
        """Update the quantity of a specific item in the cart."""
        user_id = get_telegram_user_id()
        data = api.payload
        item_id = data.get('itemId')
        new_quantity = data.get('quantity')

        if new_quantity is None or new_quantity < 0:
            api.abort(400, "Quantity must be a non-negative integer.")

        cart = get_or_create_cart(user_id)
        item_to_update = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if not item_to_update:
            item_to_update = CartItem.query.filter_by(product_id=item_id, cart_id=cart.id).first()

        if not item_to_update:
            api.abort(404, "Cart item not found in your cart.")

        if new_quantity == 0:
            db.session.delete(item_to_update)
        else:
            item_to_update.quantity = new_quantity
        
        db.session.commit()
        update_cart_total(cart)
        
        # Corrected line: Instantiate CartResource and call its get method
        updated_cart_data = CartResource().get() 
        return api.marshal(updated_cart_data, cart_response_model)


@api.route('/cart/remove')
class RemoveFromCartResource(Resource):
    @api.expect(remove_from_cart_request)
    @api.marshal_with(cart_response_model)
    def delete(self):
        """Remove a specific item from the cart."""
        user_id = get_telegram_user_id()
        data = api.payload
        item_id = data.get('itemId')

        cart = get_or_create_cart(user_id)
        item_to_remove = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()

        if not item_to_remove:
            api.abort(404, "Cart item not found in your cart.")

        db.session.delete(item_to_remove)
        db.session.commit()
        update_cart_total(cart)
        
        # Corrected line: Instantiate CartResource and call its get method
        updated_cart_data = CartResource().get() 
        return api.marshal(updated_cart_data, cart_response_model)

@api.route('/cart/clear')
class ClearCartResource(Resource):
    @api.marshal_with(cart_response_model)
    def delete(self):
        """Clear all items from the cart."""
        user_id = get_telegram_user_id()
        cart = get_or_create_cart(user_id)
        # Delete all cart items associated with this cart
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
        update_cart_total(cart) # This will set total to 0
        
        # Corrected line: Instantiate CartResource and call its get method
        updated_cart_data = CartResource().get() 
        return api.marshal(updated_cart_data, cart_response_model)

# --- Configuration ---
DELIVERY_COST_MOCK = 100 # Mock value for delivery cost

# IMPORTANT: User-Agent for Nominatim API
# Replace 'YourDeliveryApp/1.0 (your.email@example.com)' with your actual app name and email.
NOMINATIM_USER_AGENT = "MyDeliveryApp/1.0 (my.email@example.com)"

# Store loaded polygons globally
VALID_DELIVERY_AREAS = []

# --- Helper Function for Reverse Geocoding ---
def get_address_from_coordinates(latitude, longitude):
    """
    Retrieves the address for given latitude and longitude coordinates
    using OpenStreetMap's Nominatim reverse geocoding service.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        str or None: The full address string if found, otherwise None.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": latitude,
        "lon": longitude,
        "zoom": 18,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": NOMINATIM_USER_AGENT
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data and "display_name" in data:
            return data["display_name"]
        else:
            print(f"Nominatim: No address found for {latitude}, {longitude}. Response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Nominatim Error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Nominatim JSON Decode Error: {e}. Raw response: {response.text}")
        return None

# Cache for memoization
_delivery_areas_cache = {}
_last_geojson_hash = None

def load_delivery_areas():
    global VALID_DELIVERY_AREAS
    global _delivery_areas_cache
    global _last_geojson_hash

    # Calculate a hash of the current geojson_data to use as a cache key
    # Use json.dumps with sort_keys to ensure consistent hashing
    current_geojson_hash = hash(json.dumps(geojson_data, sort_keys=True))

    if current_geojson_hash == _last_geojson_hash:
        print("Using memoized delivery areas.")
        VALID_DELIVERY_AREAS = _delivery_areas_cache[current_geojson_hash]
        return

    # If the geojson_data has changed or it's the first run, reload
    print("Loading delivery areas...")
    VALID_DELIVERY_AREAS = [] # Clear previous loads

    if geojson_data and geojson_data.get("type") == "FeatureCollection":
        for feature in geojson_data.get("features", []):
            geometry_type = feature.get("geometry", {}).get("type")
            geometry_coords = feature.get("geometry", {}).get("coordinates")

            if geometry_type == "Polygon":
                # Polygon coordinates are usually [exterior_ring, interior_ring1, ...]
                # We assume only one exterior ring for simplicity here.
                polygon_coords_shapely = [tuple(coord) for coord in geometry_coords[0]]
                VALID_DELIVERY_AREAS.append(Polygon(polygon_coords_shapely))
            elif geometry_type == "LineString":
                linestring_points_shapely = [tuple(coord) for coord in geometry_coords]
                # Note: For LineString as a boundary, Shapely's Polygon will close it.
                # Be careful if your LineString isn't intended to form a closed polygon.
                VALID_DELIVERY_AREAS.append(Polygon(linestring_points_shapely))
            else:
                print(f"Warning: Skipping unsupported geometry type: {geometry_type}")
        print(f"Loaded {len(VALID_DELIVERY_AREAS)} delivery areas from geojson")
        
        # Store the newly loaded areas in the cache
        _delivery_areas_cache[current_geojson_hash] = VALID_DELIVERY_AREAS
        _last_geojson_hash = current_geojson_hash
    else:
        print(f"Error: Expected FeatureCollection from geojson, got {geojson_data.get('type') if geojson_data else 'None/Invalid'}")

@api.route('/map')
class MapResource(Resource):
    # If you want to document input parameters
    # @api.expect(map_query_parser) # Define a parser if needed
    # @api.marshal_with(map_output_model) # Define an output model if needed
    def get(self):
        load_delivery_areas()
        global VALID_DELIVERY_AREAS, DELIVERY_COST_MOCK 

        lat_str = request.args.get('latitude')
        lon_str = request.args.get('longitude')

        if not lat_str or not lon_str:
            # Use api.abort which integrates with Flask-RESTx's error handling
            # api.abort will automatically return a JSON response with the error message
            api.abort(400, "Latitude (lat) and Longitude (lon) are required query parameters.")

        try:
            latitude = float(lat_str)
            longitude = float(lon_str)
        except ValueError:
            api.abort(400, "Invalid latitude or longitude format. Must be numbers.")

        point = Point(longitude, latitude)

        if not VALID_DELIVERY_AREAS:
            api.abort(503, "Delivery areas not loaded. Please try again later.")

        is_in_delivery_area = False
        for area_polygon in VALID_DELIVERY_AREAS:
            if area_polygon.contains(point):
                is_in_delivery_area = True
                break

        if not is_in_delivery_area:
            return {
                "address": None,
                "delivery_cost": None,
                "message": "Coordinates are outside our valid delivery areas."
            }, 404

        address = get_address_from_coordinates(latitude, longitude)

        if address:
            return {
                "address": address,
                "delivery_cost": DELIVERY_COST_MOCK
            }, 200
        else:
            api.abort(500, "Coordinates are within a valid delivery area, but address lookup failed.")

# Error handling for the API blueprint
@api_bp.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        response = jsonify({
            'message': e.description,
            'status': e.code,
            'error_type': e.__class__.__name__
        })
        response.status_code = e.code
        return response
    
    current_app.logger.error(f"An unhandled error occurred: {e}", exc_info=True)
    response = jsonify({
        'message': 'An unexpected error occurred. Please try again later.',
        'status': InternalServerError.code,
        'error_type': 'InternalServerError',
        'details': str(e) if current_app.debug else None
    })
    response.status_code = InternalServerError.code
    return response
    
# --- Define a simple SQLAlchemy Model for the Alembic Version Table ---
# We don't need to add this to db.init_app or db.create_all; it's just for querying.
class AlembicVersion(db.Model):
    __tablename__ = 'alembic_version' # Default Alembic table name
    version_num = db.Column(db.String(32), primary_key=True) # Column that holds the current version UUID

    def __repr__(self):
        return f"<AlembicVersion {self.version_num}>"

# --- New Model for Alembic Version Response ---
alembic_version_model = api.model('AlembicVersion', {
    'version': fields.String(required=True, description='Current Alembic migration version (UUID)'),
    'timestamp': fields.String(description='Timestamp of when the version was retrieved', attribute='_timestamp', default=lambda: datetime.now().isoformat())
})

# --- New Alembic Version Endpoint ---
@api.route('/alembic-version')
class AlembicVersionResource(Resource):
    @api.marshal_with(alembic_version_model)
    def get(self):
        """Get the current Alembic database migration version."""
        version = "unknown"
        try:
            # Query the alembic_version table
            # There should only ever be one row in this table, representing the current head.
            alembic_rec = db.session.query(AlembicVersion).first()

            if alembic_rec:
                version = alembic_rec.version_num
            else:
                current_app.logger.warning("Alembic version table 'alembic_version' found, but it is empty. No migrations applied?")
                # Return a default, or an error if you consider an empty table an issue.
                version = "no_migrations_applied"
        except Exception as e:
            # This could happen if the table doesn't exist yet, or other DB errors.
            current_app.logger.error(f"Error querying Alembic version from DB: {e}")
            # Depending on your desired behavior, you might want to return an error,
            # or a default value like "unknown" or "db_error".
            api.abort(500, "Could not retrieve Alembic version from database.")

        # Flask-RESTx will automatically jsonify and set headers with UTF-8
        # because ensure_ascii=False is already configured.
        return {'version': version}

payment_webhook_ns = Namespace('payment', description='Payment webhooks')

# Add the new namespace to your existing 'api' instance
# The 'path' argument here defines the URL prefix for this namespace.
# So, /payment/callback will be the full URL for the webhook.
api.add_namespace(payment_webhook_ns, path='/payment')

# Вспомогательная функция для парсинга города (скопирована для согласованности)
def _parse_city_from_address(full_address):
    city_match = re.search(r',\s*([^,]+?)(?:\s*\d{5})?\s*$', full_address)
    city = "Default City" # Запасной вариант
    if city_match:
        city = city_match.group(1).strip()
    elif full_address:
        parts = full_address.split(',')
        if len(parts) > 1:
            city = parts[-1].strip()
        else:
            city = full_address.split()[-1] if full_address.split() else "Default City"
    return city

@payment_webhook_ns.route('/callback')
class PaymentCallback(Resource):
    @api.doc(responses={200: 'Success', 400: 'Invalid Request', 403: 'Forbidden'})
    def post(self):
        """Обработка вебхуков платежей ЮKassa."""
        current_app.logger.info("Получен вебхук ЮKassa.")
        try:
            payload = request.json
            if not payload:
                current_app.logger.error("Вебхук ЮKassa: JSON-payload не получен.")
                return {'message': 'No JSON payload'}, 400

            event = payload.get('event')
            payment_object = payload.get('object')

            if not event or not payment_object:
                current_app.logger.error(f"Вебхук ЮKassa: Отсутствуют 'event' или 'object' в payload: {payload}")
                return {'message': 'Invalid webhook payload structure'}, 400

            payment_id = payment_object.get('id')
            payment_status = payment_object.get('status')
            order_id = payment_object.get('metadata', {}).get('order_id') # Наш внутренний ID заказа

            if not payment_id or not payment_status or not order_id:
                current_app.logger.error(f"Вебхук ЮKassa: Отсутствуют важные поля (id, status, или metadata.order_id): {payload}")
                return {'message': 'Missing vital payment details'}, 400

            current_app.logger.info(f"Получен вебхук ЮKassa для платежа {payment_id} (Заказ {order_id}), событие: {event}, статус: {payment_status}")

            # Загружаем заказ со всеми необходимыми связями
            order = Order.query.filter_by(id=order_id).options(
                joinedload(Order.delivery_info),
                joinedload(Order.items).joinedload(OrderItem.product)
            ).first()

            if not order:
                current_app.logger.error(f"Вебхук ЮKassa: Заказ {order_id} не найден в БД для платежа {payment_id}.")
                return {'message': 'Order not found'}, 404

            # Обновляем payment_id заказа, если он еще не установлен
            if not order.yookassa_payment_id:
                order.yookassa_payment_id = payment_id
                db.session.add(order) # Помечаем для сохранения

            if event == 'payment.succeeded':
                if order.status == 'pending_payment' or order.status == 'payment_initiation_failed': # Только если ожидаем оплату
                    current_app.logger.info(f"Платеж успешно завершен для заказа {order_id}. Попытка отправить в IIKO.")

                    # --- Теперь отправляем заказ в IIKO ---
                    try:
                        # Получаем актуальный токен IIKO
                        iiko_token = iiko_service.get_iiko_token()
                        if not iiko_token:
                            current_app.logger.error(f"Вебхук: Не удалось получить токен IIKO для заказа {order.id}.")
                            order.status = 'iiko_send_failed_no_token'
                            db.session.commit()
                            return {'message': 'IIKO token unavailable'}, 500

                        # Получаем данные организации и группы терминалов (желательно кешировать)
                        organizations = iiko_service.get_organizations(iiko_token)
                        organization_id = organizations[0].get("id") if organizations else None
                        if not organization_id:
                            current_app.logger.error(f"Вебхук: Не удалось получить ID организации IIKO для заказа {order.id}.")
                            order.status = 'iiko_send_failed_no_org'
                            db.session.commit()
                            return {'message': 'IIKO organization ID unavailable'}, 500

                        terminal_groups = iiko_service.get_terminal_groups(organization_id, iiko_token)
                        terminal_group_id = terminal_groups[0]["items"][0].get("id") if terminal_groups and terminal_groups[0].get("items") else None
                        if not terminal_group_id:
                            current_app.logger.error(f"Вебхук: Не удалось получить ID группы терминалов IIKO для заказа {order.id}.")
                            order.status = 'iiko_send_failed_no_terminal'
                            db.session.commit()
                            return {'message': 'IIKO terminal group ID unavailable'}, 500

                        iiko_payment_types = iiko_service.get_payment_types([organization_id], iiko_token)
                        selected_iiko_payment_type = None
                        for pt in iiko_payment_types:
                            if pt.get('paymentTypeKind', '').lower() == 'card':
                                selected_iiko_payment_type = pt
                                break
                        if not selected_iiko_payment_type:
                            current_app.logger.error(f"Не удалось найти тип платежа 'Card' в IIKO для заказа {order.id}.")
                            order.status = 'iiko_send_failed_no_card_pt'
                            db.session.commit()
                            return {'message': 'IIKO card payment type not found'}, 500

                        iiko_order_items = []
                        for item in order.items:
                            product_obj = item.product
                            if not product_obj:
                                current_app.logger.error(f"Продукт отсутствует для элемента заказа {item.id} заказа {order.id}. Пропускаем.")
                                continue

                            item_price = Decimal(str(product_obj.price))

                            iiko_modifiers = []
                            if item.selected_addons_ids:
                                for addon_id in item.selected_addons_ids:
                                    addon = Addon.query.get(addon_id)
                                    if addon:
                                        item_price += Decimal(str(addon.price)) * item.quantity # Предполагаем, что количество относится и к аддону
                                        iiko_modifiers.append({
                                            "id": addon.iiko_addon_id,
                                            "type": "Product",
                                            "amount": item.quantity # Количество модификатора связано с количеством элемента
                                        })
                            if item.selected_recommendation_ids:
                                for rec_id in item.selected_recommendation_ids:
                                    rec = Recommendation.query.get(rec_id)
                                    if rec and rec.price:
                                        item_price += Decimal(str(rec.price))
                                        iiko_modifiers.append({
                                            "id": rec.iiko_recommendation_id,
                                            "type": "Product",
                                            "amount": 1
                                        })

                            iiko_order_items.append({
                                "productId": product_obj.iiko_product_id,
                                "productCode": product_obj.iiko_product_id,
                                "name": product_obj.name,
                                "amount": item.quantity,
                                "price": float(item_price),
                                "modifiers": iiko_modifiers,
                                "comboId": None,
                                "positionId": str(uuid4())
                            })

                        # Используем DeliveryInfo из объекта заказа
                        delivery_info = order.delivery_info
                        city = _parse_city_from_address(delivery_info.address)

                        iiko_order_data_for_payload = {
                            "id": order.id,
                            "externalNumber": f"WEB-{order.id.split('-')[0]}",
                            "phone": delivery_info.phone,
                            "items": iiko_order_items,
                            "deliveryPoint": {
                                "address": {
                                    "street": delivery_info.address,
                                    "city": city,
                                },
                                "coordinates": {
                                    "latitude": delivery_info.latitude,
                                    "longitude": delivery_info.longitude,
                                }
                            },
                            "payments": [
                                {
                                    "sum": float(order.total),
                                    "paymentTypeKind": selected_iiko_payment_type.get('paymentTypeKind'),
                                    "paymentTypeId": selected_iiko_payment_type.get('id'),
                                    "isProcessedExternally": selected_iiko_payment_type.get('paymentProcessingType') == 'External',
                                    "isFiscalizedExternally": False, # Уточните, фискализируется ли ЮKassa
                                    "isPrepay": True # Это предоплата через ЮKassa
                                }
                            ],
                            "comment": delivery_info.comment,
                            "completeBefore": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        }

                        iiko_response = iiko_service.create_delivery_order(
                            organization_id=organization_id,
                            terminal_group_id=terminal_group_id,
                            order=iiko_order_data_for_payload,
                            create_order_settings={"transportToFrontTimeout": 0}
                        )

                        if iiko_response and iiko_response.get('orderId'):
                            order.status = 'sent_to_iiko'
                            current_app.logger.info(f"Заказ {order.id} успешно отправлен в IIKO через вебхук. IIKO Order ID: {iiko_response['orderId']}")
                        else:
                            order.status = 'iiko_send_failed'
                            current_app.logger.error(f"Не удалось отправить заказ {order.id} в IIKO через вебхук. Ответ: {iiko_response}")
                            # Здесь можно реализовать механизм повторных попыток
                            db.session.rollback() # Откатываем, если IIKO не удалось, даже если ЮKassa успешно
                            return {'message': 'IIKO integration failed after payment success'}, 500

                    except Exception as e:
                        current_app.logger.error(f"Ошибка отправки заказа {order.id} в IIKO после успеха ЮKassa: {e}", exc_info=True)
                        order.status = 'iiko_send_failed_exception'
                        db.session.rollback()
                        return {'message': f'Internal server error during IIKO integration: {str(e)}'}, 500


                else:
                    current_app.logger.info(f"Вебхук ЮKassa: Платеж {payment_id} успешно завершен для заказа {order_id}, но статус заказа уже был '{order.status}'. Никаких действий не требуется.")

            elif event == 'payment.canceled':
                order.status = 'payment_canceled'
                current_app.logger.warning(f"Вебхук ЮKassa: Платеж {payment_id} отменен для заказа {order_id}.")
            elif event == 'payment.waiting_for_capture':
                # Этот статус может возникнуть, если 'capture' был установлен в false.
                # Наш сервис устанавливает capture=True, поэтому этот случай может указывать на проблему или другой флоу.
                order.status = 'waiting_for_capture'
                current_app.logger.info(f"Вебхук ЮKassa: Платеж {payment_id} ожидает захвата для заказа {order_id}.")
            else:
                current_app.logger.warning(f"Вебхук ЮKassa: Необработанное событие '{event}' для платежа {payment_id}.")
                # Логируйте или обрабатывайте другие статусы, если необходимо (например, 'refunded', 'pending')

            db.session.commit() # Сохраняем изменения статуса заказа
            return {'message': 'Webhook processed successfully'}, 200

        except Exception as e:
            db.session.rollback() # Откатываем транзакцию в случае любой неожиданной ошибки
            current_app.logger.error(f"Ошибка при обработке вебхука ЮKassa: {e}", exc_info=True)
            return {'message': f'Internal server error: {str(e)}'}, 500
