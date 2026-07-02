# app/api.py

import traceback
from flask import Blueprint, jsonify, current_app, request
from flask_restx import Api, Namespace, Resource, fields, reqparse
from werkzeug.exceptions import HTTPException, InternalServerError
from app.models import (
    db, DeliveryInfo, MainCategory, Category, Product, ProductAddon, Addon, Recommendation,
    Order, OrderItem, ProductRecommendation, Cart, CartItem, CartAddon, CartRecommendation,
    DRINKS_CATEGORY_NAME, WokBase, WokMeat, WokTopping, WokSauce, WOK_PRODUCT_CONSTRUCTOR_ID,
    WOK_BUILDER_PRODUCT_ID, WOK_CATEGORY_NAME, DELIVERY_PRODUCT_IDS
)
from app import iiko_service # Assuming this is your IIKO integration service
from app.iiko_service import USING_MOCK
from sqlalchemy import desc, distinct
from sqlalchemy.orm import joinedload
from decimal import Decimal
from datetime import datetime,  timedelta, timezone
from shapely.geometry import Point, Polygon, LineString
import json
import requests
import uuid
import re
import time

from fuzzywuzzy import fuzz

from .geojson import get_geojson_data
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


# New models for selected addons/recommendations with quantity
selected_addon_with_quantity_model = api.model('SelectedAddonWithQuantity', {
    'addon': fields.Nested(addon_model, description='Addon details'),
    'quantity': fields.Integer(required=True, description='Quantity of this selected addon')
})

selected_recommendation_with_quantity_model = api.model('SelectedRecommendationWithQuantity', {
    'recommendation': fields.Nested(recommendation_model, description='Recommendation details'),
    'quantity': fields.Integer(required=True, description='Quantity of this selected recommendation')
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

    # ФИКС: связываем с полем payment_method в СУБД
    'paymentMethod': fields.String(required=True, description='Payment method (e.g., cash, card)', attribute='payment_method'),

    'comment': fields.String(description='Additional comments for delivery', allow_null=True),
    'latitude': fields.Float(required=True, description='Latitude for delivery'),
    'longitude': fields.Float(required=True, description='Longitude for delivery'),
    'postcode': fields.String(description='Postal code', allow_null=True),
    'city_name': fields.String(description='City name from geocoding', allow_null=True),
    'street_name': fields.String(description='Street name from geocoding', allow_null=True),
    'house_number': fields.String(description='House number from geocoding', allow_null=True)
})

order_item_model = api.model('OrderItem', {
    'product': fields.Nested(product_model, description='Product details', allow_null=True),
    'quantity': fields.Integer(required=True, description='Quantity of the product'),
    'selectedAddons': fields.List(fields.Nested(selected_addon_with_quantity_model), description='Selected addons for this product item', default=[]), # Updated to use new model
    'selectedRecommendations': fields.List(fields.Nested(selected_recommendation_with_quantity_model), description='Selected recommendations for this product item', default=[]), # Updated to use new model
    'customWokData': fields.Raw(attribute='custom_wok_data', description='Custom Wok data if applicable', allow_null=True),
    'customPrice': fields.Float(attribute='custom_price', description='Custom price for wok if applicable', allow_null=True),
    'customName': fields.String(attribute='custom_name', description='Custom name for wok if applicable', allow_null=True),
})
order_model = api.model('Order', {
    'id': fields.String(required=True, description='Order ID'),

    # ФИКС: связываем с user_id
    'userId': fields.String(required=True, description='Telegram User ID', attribute='user_id'),

    'items': fields.List(fields.Nested(order_item_model), description='List of items in the order'),
    'total': fields.Float(required=True, description='Total price of the order'),

    # ФИКС: связываем с delivery_info связью таблицы Order
    'deliveryInfo': fields.Nested(delivery_info_model_new, required=True, description='Delivery information', attribute='delivery_info'),

    'status': fields.String(required=True, description='Current status of the order'),

    # ФИКС: связываем с created_at
    'createdAt': fields.DateTime(dt_format='iso8601', description='Timestamp of order creation', attribute='created_at'),

    # ФИКС: связываем с estimated_delivery
    'estimatedDelivery': fields.DateTime(dt_format='iso8601', description='Estimated delivery time', allow_null=True, attribute='estimated_delivery'),

    'paymentUrl': fields.String(description='URL for online payment confirmation', attribute='confirmation_url', allow_null=True),

    # ФИКС: связываем с yookassa_payment_id
    'yookassaPaymentId': fields.String(description='Yookassa payment ID for online payments', allow_null=True, attribute='yookassa_payment_id'),

    # ФИКС: связываем с display_status
    'displayStatus': fields.Boolean(required=True, description='Boolean flag to control if the order is displayed to the user', attribute='display_status')
})

# Model for updating order display status
order_display_status_update_model = api.model('OrderDisplayStatusUpdate', {
    'orderId': fields.String(required=True, description='ID of the order to update'),
    'displayStatus': fields.Boolean(required=True, description='New display status for the order (true to display, false to hide)')
})

# --- Cart Models ---
MOCK_TELEGRAM_USER_ID = 123

# Helper function to get user ID from header
def get_telegram_user_id():
    user_id = request.headers.get('X-Telegram-User-ID')
    if not user_id:
        return MOCK_TELEGRAM_USER_ID
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

# --- IIKO internal ----
MATCH_THRESHOLD = 90

# Helper function to normalize Russian characters
def _normalize_russian_chars(text: str) -> str:
    """Replaces 'ё' with 'е' for consistent comparison."""
    return text.replace('ё', 'е')

# Helper function to match client street name to IIKO streets
def _match_iiko_street(client_street_name: str, iiko_streets_list: list) -> tuple[str, str]:
    """
    Performs fuzzy matching to find the best IIKO street ID and name for a given client street name.
    Ignores differences between 'ё' and 'е'.
    If multiple candidates exist, selects the highest-scoring one.
    If no candidates exist, falls back to the first street in the provided IIKO list.

    Args:
        client_street_name (str): The street name provided by the client (from Nominatim).
        iiko_streets_list (list): A list of dictionaries, each representing an IIKO street
                                  (e.g., [{'id': 'uuid', 'name': 'Улица Ленина'}]).

    Returns:
        tuple[str, str]: A tuple containing (selected_street_id, selected_street_name).

    Raises:
        RuntimeError: If no IIKO streets are provided for matching.
    """
    if not iiko_streets_list:
        current_app.logger.error(f"No IIKO streets provided for matching client street '{client_street_name}'.")
        raise RuntimeError("No IIKO streets available for matching.")

    # Normalize client street name and generate variations
    client_name_lower_normalized = _normalize_russian_chars(client_street_name.lower())
    client_name_variations = {client_name_lower_normalized}

    # Common street type variations
    if " улица" in client_name_lower_normalized:
        client_name_variations.add(client_name_lower_normalized.replace(" улица", ""))
    if client_name_lower_normalized.startswith("улица "):
        client_name_variations.add(client_name_lower_normalized.replace("улица ", "", 1))
    if " проспект" in client_name_lower_normalized:
        client_name_variations.add(client_name_lower_normalized.replace(" проспект", ""))
    if client_name_lower_normalized.startswith("проспект "):
        client_name_variations.add(client_name_lower_normalized.replace("проспект ", "", 1))
    if "переулок" in client_name_lower_normalized:
        client_name_variations.add(client_name_lower_normalized.replace("переулок", "пер."))
    if "бульвар" in client_name_lower_normalized:
        client_name_variations.add(client_name_lower_normalized.replace("бульвар", "б-р"))

    number_replacements = {
        "1-я": "первая", "1-й": "первый", "1-го": "первого",
        "2-я": "вторая", "2-й": "второй", "2-го": "второго",
        "3-я": "третья", "3-й": "третий", "3-го": "третьего",
        "4-я": "четвертая", "4-й": "четвертый",
        "5-я": "пятая", "5-й": "пятый",
        "8-го": "восьмого",
        "им.": "имени",
    }
    initial_variations_list = list(client_name_variations)

    for var in initial_variations_list:
        current_processed_var = var
        for old_val, new_val in number_replacements.items():
            if old_val in current_processed_var:
                new_var = current_processed_var.replace(old_val, new_val)
                client_name_variations.add(new_var)
                
                if " улица" in new_var:
                    client_name_variations.add(new_var.replace(" улица", ""))
                if new_var.startswith("улица "):
                    client_name_variations.add(new_var.replace("улица ", "", 1))
                if " проспект" in new_var:
                    client_name_variations.add(new_var.replace(" проспект", ""))
                if new_var.startswith("проспект "):
                    client_name_variations.add(new_var.replace("проспект ", "", 1))

    potential_matches = []
    for street in iiko_streets_list:
        iiko_street_name_lower_normalized = _normalize_russian_chars(street['name'].lower())
        best_score_for_current_iiko_street = 0
        for client_var in client_name_variations:
            score = fuzz.ratio(client_var, iiko_street_name_lower_normalized)
            if score > best_score_for_current_iiko_street:
                best_score_for_current_iiko_street = score

        if best_score_for_current_iiko_street >= MATCH_THRESHOLD:
            potential_matches.append({
                "score": best_score_for_current_iiko_street,
                "street": street
            })

    potential_matches.sort(key=lambda x: x['score'], reverse=True)

    if potential_matches:
        best_match = potential_matches[0]
        selected_street_id = best_match['street']['id']
        selected_street_name = best_match['street']['name']

        if len(potential_matches) > 1:
            top_matches_str = ", ".join([f"{m['street']['name']} ({m['score']}%)" for m in potential_matches[:3]])
            current_app.logger.warning(
                f"Multiple IIKO streets matched '{client_street_name}' with over {MATCH_THRESHOLD}% similarity. "
                f"Picking best match: '{selected_street_name}' (Score: {best_match['score']}%). Top matches were: [{top_matches_str}]."
            )
        else:
            current_app.logger.info(
                f"Matched client street '{client_street_name}' to IIKO street: "
                f"ID={selected_street_id}, Name='{selected_street_name}' (Score: {best_match['score']}%)"
            )
        return selected_street_id, selected_street_name
    else:
        fallback_street = iiko_streets_list[0]
        selected_street_id = fallback_street['id']
        selected_street_name = fallback_street['name']
        current_app.logger.warning(
            f"No IIKO street matched '{client_street_name}' with over {MATCH_THRESHOLD}% similarity. "
            f"Falling back to the first available IIKO street: ID={selected_street_id}, Name='{selected_street_name}'."
        )
        return selected_street_id, selected_street_name

def _match_iiko_city(client_city_name: str, iiko_cities_list: list) -> tuple[str, str]:
    """
    Performs fuzzy matching to find the best IIKO city ID and name for a given client city name.
    Handles city-specific variations like "город", "пгт.", etc.
    """
    if not iiko_cities_list:
        current_app.logger.error(f"No IIKO cities provided for matching client city '{client_city_name}'.")
        raise RuntimeError("No IIKO cities available for matching.")

    client_name_lower_normalized = _normalize_russian_chars(client_city_name.lower())
    client_name_variations = {client_name_lower_normalized}

    # Common city type variations
    city_replacements = {
        " город": "", "г. ": "", " г ": "",
        "поселок городского типа": "", "пгт": "", " пгт ": "",
        "поселок": "", " п. ": "",
        "село": "",
        "деревня": "", "д. ": ""
    }

    initial_variations_list = list(client_name_variations)
    for var in initial_variations_list:
        for old_val, new_val in city_replacements.items():
            if old_val in var:
                client_name_variations.add(var.replace(old_val, new_val).strip())

    potential_matches = []
    for city in iiko_cities_list:
        iiko_city_name_lower_normalized = _normalize_russian_chars(city['name'].lower())
        best_score_for_current_iiko_city = 0
        for client_var in client_name_variations:
            score = fuzz.ratio(client_var, iiko_city_name_lower_normalized)
            if score > best_score_for_current_iiko_city:
                best_score_for_current_iiko_city = score

        if best_score_for_current_iiko_city >= MATCH_THRESHOLD:
            potential_matches.append({
                "score": best_score_for_current_iiko_city,
                "city": city
            })
    
    potential_matches.sort(key=lambda x: x['score'], reverse=True)

    if potential_matches:
        best_match = potential_matches[0]
        selected_city_id = best_match['city']['id']
        selected_city_name = best_match['city']['name']
        current_app.logger.info(
            f"Fuzzy matched client city '{client_city_name}' to IIKO city: "
            f"ID={selected_city_id}, Name='{selected_city_name}' (Score: {best_match['score']}%)"
        )
        return selected_city_id, selected_city_name
    else:
        fallback_city = iiko_cities_list[0]
        selected_city_id = fallback_city['id']
        selected_city_name = fallback_city['name']
        current_app.logger.warning(
            f"No IIKO city matched '{client_city_name}' with over {MATCH_THRESHOLD}% similarity. "
            f"Falling back to the first available IIKO city: ID={selected_city_id}, Name='{selected_city_name}'."
        )
        return selected_city_id, selected_city_name

def _get_iiko_essential_data(iiko_token: str, client_payment_method: str, client_street_name: str, client_city_name: str):
    """
    Helper to fetch essential IIKO dynamic data: organization, terminal group,
    selected payment type, and default city/street (with fuzzy matching).
    Raises an error if critical data cannot be fetched or matching fails.
    """
    organization_id = None
    terminal_group_id = None
    selected_iiko_payment_type = None
    selected_city_id = None
    selected_city_name = None
    selected_street_id = None
    selected_street_name = None

    # 1. Fetch Organization ID
    organizations = iiko_service.get_organizations(iiko_token)
    if organizations:
        organization_id = organizations[0].get("id")
        current_app.logger.info(f"Using IIKO Organization ID: {organization_id}")
    else:
        current_app.logger.error("No organizations found from IIKO API.")
        raise RuntimeError("Could not determine organization ID for external order.")

    # 2. Fetch Terminal Group ID
    terminal_groups = iiko_service.get_terminal_groups(organization_id, iiko_token)
    if terminal_groups and terminal_groups[0].get("items"):
        terminal_group_id = terminal_groups[0]["items"][0].get("id")
        current_app.logger.info(f"Using IIKO Terminal Group ID: {terminal_group_id}")
    else:
        current_app.logger.error(f"No terminal groups found for organization {organization_id} from IIKO API.")
        raise RuntimeError("Could not determine terminal group ID for external order.")

    # 3. Fetch Payment Types and select based on client method
    # CORRECTED: Reverted to the original logic which handles a flat list of payment types.
    iiko_payment_types = iiko_service.get_payment_types([organization_id], iiko_token)
    if not iiko_payment_types:
        current_app.logger.error(f"No payment types found for organization {organization_id} from IIKO API.")
        raise RuntimeError("Could not determine payment types for external order.")

    client_payment_method_lower = client_payment_method.lower()
    for pt in iiko_payment_types:
        pt_kind = pt.get('paymentTypeKind', '').lower()
        pt_code = pt.get('code', '').lower()
        if client_payment_method_lower == "cash" and pt_kind == "cash":
            selected_iiko_payment_type = pt
            break
        elif client_payment_method_lower == "card" and pt_kind == "card":
            selected_iiko_payment_type = pt
            break
        elif client_payment_method_lower == "card" and (pt_kind in ["loyaltycard", "external"] or pt_code == "bank"):
            selected_iiko_payment_type = pt
            break
        elif client_payment_method_lower == "online":
            if pt_kind == "card" or pt_code == "bank":
                selected_iiko_payment_type = pt
                break
            selected_iiko_payment_type = pt
            break

    if not selected_iiko_payment_type:
        current_app.logger.warning(f"Could not find a specific IIKO payment type for client method '{client_payment_method_lower}'. Using the first available payment type as fallback.")
        selected_iiko_payment_type = iiko_payment_types[0]

    current_app.logger.info(f"Using IIKO Payment Type: ID='{selected_iiko_payment_type.get('id')}', Name='{selected_iiko_payment_type.get('name')}', Kind='{selected_iiko_payment_type.get('paymentTypeKind')}', Code='{selected_iiko_payment_type.get('code')}'")

    # 4. Fetch City and Street with Fuzzy Matching
    cities_data = iiko_service.get_cities([organization_id])
    if not cities_data:
        current_app.logger.error("No cities data returned from IIKO. Cannot determine address for order.")
        raise RuntimeError("No cities data returned from IIKO. Cannot create order.")

    org_cities_list = next((org_data.get('items') for org_data in cities_data if org_data.get('organizationId') == organization_id), [])
    if not org_cities_list:
        current_app.logger.error("No cities found for selected organization. Cannot determine address for order.")
        raise RuntimeError("No cities found for organization in IIKO. Cannot create order.")

    # find "Черноголовка" city
    found_chernogolovka = False
    for city in org_cities_list:
        if city.get('name') == "Черноголовка":
            selected_city_id = city['id']
            selected_city_name = city['name']
            current_app.logger.info(f"Prioritizing IIKO City: ID={selected_city_id}, Name='{selected_city_name}' (explicitly 'Черноголовка')")
            found_chernogolovka = True
            break
    
    # use the new fuzzy matching function
    if client_city_name:
        selected_city_id, selected_city_name = _match_iiko_city(client_city_name, org_cities_list)
    elif not found_chernogolovka:
        current_app.logger.warning("No city name from Nominatim and no 'Черноголовка' found. Using the first available city as fallback.")
        selected_city_id = org_cities_list[0]['id']
        selected_city_name = org_cities_list[0]['name']

    # 5. Fetch streets for the selected city and perform detailed fuzzy matching
    streets_data = iiko_service.get_streets_by_city(organization_id, selected_city_id)
    if not streets_data:
        current_app.logger.error(f"No streets found for city '{selected_city_name}' from IIKO API. Cannot match street for order.")
        raise RuntimeError("No streets found for the selected city in IIKO. Cannot create order.")

    selected_street_id, selected_street_name = _match_iiko_street(client_street_name, streets_data)
    
    return {
        "organization_id": organization_id,
        "terminal_group_id": terminal_group_id,
        "selected_iiko_payment_type": selected_iiko_payment_type,
        "selected_city_id": selected_city_id,
        "selected_city_name": selected_city_name,
        "selected_street_id": selected_street_id,
        "selected_street_name": selected_street_name
    }
    
def integer_to_uuid_like_string(integer_id):
    """
    Converts an integer ID into a deterministic UUID-like string.
    
    Example: integer_id = 2 -> "00000000-0000-0000-0000-000000000002"
    """
    hex_id = f'{integer_id:032x}' # Format as a 32-digit hex string
    return f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"

def _send_order_to_iiko_internal(order: Order, iiko_token: str, client_payment_method: str,
                                 client_street_name: str, nominatim_postcode: str, nominatim_house_number: str,
                                 client_city_name: str, delivery_area_number: int, is_free_delivery: bool):
    """
    Constructs the IIKO payload and sends the order to IIKO.
    
    Args:
        order (Order): The SQLAlchemy Order object, must be loaded with its delivery_info and items.
                       OrderItem.product should be loaded. Addons/Recommendations will be fetched by ID.
        iiko_token (str): The IIKO access token.
        client_payment_method (str): The client's chosen payment method (e.g., 'cash', 'card', 'online').
                                     Used to determine IIKO payment type.
        client_street_name (str): The street name extracted from the client's coordinates (Nominatim 'road').
                                  Used for fuzzy matching with IIKO streets.
        nominatim_postcode (str): The postal code extracted from Nominatim.
        nominatim_house_number (str): The house number extracted from Nominatim (e.g., '9', '2/1').
        client_city_name (str): The city name extracted from Nominatim.
        delivery_area_number (int): IIKO delivery area number.
        is_free_delivery (bool): Is the delivery free
    
    Returns:
        dict: The response from the IIKO /deliveries/create API.
        
    Raises:
        RuntimeError: If essential IIKO data cannot be fetched or if IIKO API call fails.
    """
    current_app.logger.info(f"Preparing to send order {order.id} to IIKO.")

    # Fetch dynamic IIKO data, including fuzzy-matched city and street
    iiko_address_metadata = _get_iiko_essential_data(iiko_token, client_payment_method, client_street_name, client_city_name)

    # Combine metadata
    iiko_metadata = {**iiko_address_metadata}

    organization_id = iiko_metadata["organization_id"]
    terminal_group_id = iiko_metadata["terminal_group_id"]
    selected_iiko_payment_type = iiko_metadata["selected_iiko_payment_type"]
    selected_city_id = iiko_metadata["selected_city_id"]
    selected_city_name = iiko_metadata["selected_city_name"]
    selected_street_id = iiko_metadata["selected_street_id"]
    selected_street_name = iiko_metadata["selected_street_name"]

    iiko_order_items = []
    # Loop through order items to build IIKO payload items
    for item in order.items:
        product_obj = item.product
        item_unit_price_for_iiko = Decimal('0.00')
        product_name = None
        product_id_for_iiko = None

        if product_obj:
            item_unit_price_for_iiko += Decimal(str(product_obj.price))
            product_name = product_obj.name
            product_id_for_iiko = product_obj.iiko_product_id
        elif item.custom_wok_data:
            item_unit_price_for_iiko += Decimal(str(item.custom_price)) if item.custom_price else Decimal('0.00')
            product_name = item.custom_name if item.custom_name else "Custom Wok"
            product_id_for_iiko = WOK_PRODUCT_CONSTRUCTOR_ID
        else:
            current_app.logger.warning(f"Order item {item.id} has no product or custom wok data. Skipping for IIKO payload.")
            continue

        iiko_modifiers = []
        # Fetch addons using the IDs and quantities stored in `selected_addons_data`
        for addon_data in item.selected_addons_data:
            addon = Addon.query.get(addon_data['id']) # Query Addon object by ID
            if addon:
                addon_quantity = addon_data['quantity'] # Get specific quantity for this addon
                item_unit_price_for_iiko += Decimal(str(addon.price)) * addon_quantity # Add addon price multiplied by its quantity
                iiko_modifiers.append({
                    "productId": addon.iiko_addon_id,
                    "type": "Product",
                    "amount": addon_quantity,  # Corrected: Use the specific addon quantity
                    "name": addon.name,
                    "price": float(addon.price) # Price of the modifier itself (per unit)
                })
            else:
                current_app.logger.warning(f"Addon with ID {addon_data['id']} not found for order item {item.id}.")

        # Fetch recommendations using the IDs and quantities stored in `selected_recommendation_data`
        for rec_data in item.selected_recommendation_data:
            recommendation = Recommendation.query.get(rec_data['id']) # Query Recommendation object by ID
            if recommendation and recommendation.price:
                rec_quantity = rec_data['quantity'] # Get specific quantity for this recommendation
                item_unit_price_for_iiko += Decimal(str(recommendation.price)) * rec_quantity # Add recommendation price multiplied by its quantity
                iiko_modifiers.append({
                    "productId": recommendation.iiko_recommendation_id,
                    "type": "Product",
                    "amount": rec_quantity,  # Corrected: Use the specific recommendation quantity
                    "name": recommendation.name,
                    "price": float(recommendation.price) # Price of the modifier itself (per unit)
                })
            else:
                current_app.logger.warning(f"Recommendation with ID {rec_data['id']} not found for order item {item.id}.")

        iiko_order_items.append({
            "type": "Product",
            "productId": product_id_for_iiko,
            "productCode": product_id_for_iiko, # Often same as productId for simple products
            "name": product_name,
            "amount": item.quantity,
            "price": float(item_unit_price_for_iiko), # Unit price of the item including its selected modifiers (total for one parent item)
            "modifiers": iiko_modifiers,
            "comboId": None,
            "positionId": str(uuid.uuid4()) # Unique for each position in IIKO
        })

    # Add Delivery Product as an item
    delivery_item_id = DELIVERY_PRODUCT_IDS[delivery_area_number]
    delivery_product = Product.query.get(delivery_item_id)
    if delivery_product and not is_free_delivery:
        iiko_order_items.append({
            "type": "Product",
            "productId": delivery_product.iiko_product_id,
            "productCode": delivery_product.iiko_product_id,
            "name": delivery_product.name,
            "amount": 1,
            "price": float(delivery_product.price),
            "modifiers": [],
            "comboId": None,
            "positionId": str(uuid.uuid4())
        })
    elif not delivery_product:
        current_app.logger.warning(f"Delivery product with ID {delivery_item_id} not found. Delivery item not added to IIKO payload.")


    # --- NEW / MODIFIED LOGIC FOR HOUSE, BUILDING, AND INDEX ---
    iiko_house_final = ""
    iiko_building = ""
    
    # 1. Parse house and building from Nominatim's house_number
    if nominatim_house_number:
        house_parts = nominatim_house_number.split('/')
        iiko_house_final = house_parts[0]
        if len(house_parts) > 1:
            iiko_building = house_parts[1]
    
    # 2. Append apartment from client's input to the 'house' field
    # Assuming order.delivery_info.apartment contains just the apartment number
    if order.delivery_info.apartment:
        # As per request: "construct house as f"{house_number}, кв. {house_parsed}""
        # where house_parsed previously came from client_apartment_input.split('/')[0]
        # Here, order.delivery_info.apartment is the source of that 'house_parsed' part.
        client_apartment_part_for_display = order.delivery_info.apartment.split('/')[0] # Take first part if slash exists
        if iiko_house_final: # If a house number exists from Nominatim
            iiko_house_final = f"{iiko_house_final}, кв. {client_apartment_part_for_display}"
        else: # If no house number from Nominatim, just use the apartment as house
            iiko_house_final = f"кв. {client_apartment_part_for_display}"

    iiko_order_uuid = integer_to_uuid_like_string(order.id)

    iiko_order_data_for_payload = {
        #"id": iiko_order_uuid, # don't send ID to IIKO
        "externalNumber": f"WEB-{str(order.id)}",
        "orderServiceType": "DeliveryByCourier",
        "phone": order.delivery_info.phone,
        "items": iiko_order_items,
        "deliveryPoint": {
            "address": {
                "street": {
                    "id": selected_street_id, # Dynamically fetched and fuzzy matched
                    "name": selected_street_name # Dynamically fetched and fuzzy matched
                },
                "city": {
                    "id": selected_city_id, # Dynamically fetched
                    "name": selected_city_name # Dynamically fetched
                },
                "house": iiko_house_final,  # UPDATED
                "building": iiko_building,  # UPDATED
                "entrance": "1", # Defaulting to 1 as per original code
                "index": nominatim_postcode, # UPDATED: Use Nominatim postcode
                "line1": order.delivery_info.comment, # Using comment for line1 as per original code
            },
            "coordinates": {
                "latitude": order.delivery_info.latitude,
                "longitude": order.delivery_info.longitude,
            }
        },
        "payments": [
            {
                "sum": float(order.total) if not USING_MOCK else 0.0, # Use actual total, or 0.0 for mock
                "paymentTypeKind": selected_iiko_payment_type.get('paymentTypeKind'),
                "paymentTypeId": selected_iiko_payment_type.get('id'),
                "isProcessedExternally": selected_iiko_payment_type.get('paymentProcessingType') == 'External',
                "isFiscalizedExternally": False,
                "isPrepay": (client_payment_method.lower() == 'online') # Set isPrepay based on online payment
            }
        ],
        "comment": f"Адрес: {order.delivery_info.address}. Комментарий: {order.delivery_info.comment}" if not USING_MOCK else f"ТЕСТОВЫЙ ЗАКАЗ. НЕ ОБРАБАТЫВАТЬ. Адрес: {order.delivery_info.address}. Комментарий: {order.delivery_info.comment}",
        "completeBefore": (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
    }

    current_app.logger.info(f"Sending order {iiko_order_uuid} to IIKO with payload (excluding full items for brevity): "
                            f"Org: {organization_id}, TermGroup: {terminal_group_id}, "
                            f"Phone: {iiko_order_data_for_payload['phone']}, "
                            f"Address: {iiko_order_data_for_payload['deliveryPoint']['address']['street']['name']}, "
                            f"House: '{iiko_order_data_for_payload['deliveryPoint']['address']['house']}', "
                            f"Building: '{iiko_order_data_for_payload['deliveryPoint']['address']['building']}', "
                            f"Index: '{iiko_order_data_for_payload['deliveryPoint']['address']['index']}', "
                            f"Items count: {len(iiko_order_data_for_payload['items'])}")

    iiko_response = iiko_service.create_delivery_order(
        organization_id=organization_id,
        terminal_group_id=terminal_group_id,
        order=iiko_order_data_for_payload,
        create_order_settings={"transportToFrontTimeout": 0}
    )

    # --- UPDATED LOGIC FOR CHECKING IIKO RESPONSE ---
    iiko_order_info = iiko_response.get('orderInfo', {})
    iiko_order_id_from_response = iiko_order_info.get('id')
    creation_status = iiko_order_info.get('creationStatus')
    error_info = iiko_order_info.get('errorInfo')

    if iiko_order_id_from_response and creation_status in ['InProgress', 'Success'] and error_info is None:
        current_app.logger.info(f"Order {order.id} successfully sent to IIKO. IIKO Order ID: {iiko_order_id_from_response}")
        return iiko_response
    else:
        # Log more specific error details if available
        error_message = f"IIKO API did not return a valid order ID or creation status. Status: {creation_status}, Error Info: {error_info}"
        if iiko_response and 'error' in iiko_response and iiko_response['error'] is not None: # Check for top-level 'error' key if IIKO changes response
            error_message = f"Failed to send order to IIKO: {iiko_response.get('error', 'Unknown error')}"
        
        current_app.logger.error(f"Failed to send order {order.id} to IIKO. Response: {iiko_response}")
        raise RuntimeError(error_message)
    
# --- End IIKO internal ---

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
    # FIX: Check if custom_wok_data is a dictionary, not just truthy.
    is_custom_wok_data_dict = isinstance(custom_wok_data, dict)

    if not is_custom_wok_data_dict:
        for rec_id in selected_recommendations_data:
            rec = Recommendation.query.get(rec_id)
            if rec:
                item_price += Decimal(str(rec.price))

    # Add custom Wok component prices if it's a custom Wok (overrides product price)
    # FIX APPLIED HERE: Only proceed if custom_wok_data is a dictionary
    if is_custom_wok_data_dict:
        if 'baseId' in custom_wok_data:
            base = WokBase.query.get(custom_wok_data['baseId'])
            if base:
                item_price += Decimal(str(base.price))

        # This is where the error originally occurred. The .get() call is now safe.
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
        ADD_TO_THE_END_PREFIXES = [DRINKS_CATEGORY_NAME]

        # Fetch all categories from the database, ordered by display_order
        all_categories = MainCategory.query.order_by(MainCategory.display_order).all()

        # Filter the categories based on the excluded prefixes
        filtered_categories = []
        for category in all_categories:
            # Check if the category name starts with any of the excluded prefixes
            if not any(category.name.find(prefix) >= 0 for prefix in (EXCLUDED_PREFIXES + ADD_TO_THE_END_PREFIXES)):
                filtered_categories.append(category)

        for category in all_categories:
            if any(category.name.find(prefix) >= 0 for prefix in ADD_TO_THE_END_PREFIXES):
                filtered_categories.append(category)

        marshaled_categories = api.marshal(filtered_categories, main_category_model)
        return jsonify(marshaled_categories)

import re
from sqlalchemy import or_
from collections import defaultdict

## /products Endpoint
# ----------------------------------------------------------------------
@api.route('/products')
class ProductList(Resource):
    # The @api.marshal_with is not used here because of the Wok reordering logic and manual marshal below
    @api.param('categoryId', 'Filter products by category ID')
    def get(self):
        """Get all products, optionally filtered by category"""
        category_id = api.parser().add_argument('categoryId', type=str, location='args').parse_args()['categoryId']

        # 1. Eager load main_category and ORIGINAL category
        query = Product.query.filter_by(is_hidden=False).options(
            # FIX 1: Change Product.category to Product.original_category
            joinedload(Product.original_category),
            joinedload(Product.main_category), # Eager load MainCategory
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).order_by(Product.categoryId)

        if category_id:
            query = query.filter_by(main_category_id=category_id)

        products = query.all()

        # --- OPTIMIZATION: PRE-FETCH ALL POTENTIAL ADDON PRODUCTS ONCE ---
        # FIX (List Unpacking): Convert list of tuples/rows to list of strings
        main_category_names = [name for name, in db.session.query(MainCategory.name).all()]
        like_clauses = [Category.name.like(f"%{category_name}%Добавки%") for category_name in main_category_names]

        target_category_ids = [
            str(c.id) for c in Category.query.filter(or_(*like_clauses)).all()
        ]
        current_app.logger.info(f"target_category_ids = {target_category_ids}")

        addon_products_by_category = {}
        if target_category_ids:
            # Fetch all non-hidden products from the target categories, ensuring original_category is loaded
            all_potential_addons = Product.query.options(
                # FIX 2: Change Product.category to Product.original_category
                joinedload(Product.original_category)
            ).filter(
                Product.categoryId.in_(target_category_ids), # Use categoryId for original category lookup
                Product.is_hidden == False
            ).all()
            current_app.logger.info(f"all_potential_addons = {all_potential_addons}")

            # Group them by categoryId (the original IIKO category) for O(1) lookup inside the loop
            addon_products_by_category = defaultdict(list)
            for prod in all_potential_addons:
                addon_products_by_category[str(prod.categoryId)].append(prod)

        # --- WOK REORDERING LOGIC (Unchanged) ---
        try:
            wok_category = MainCategory.query.filter_by(name=WOK_CATEGORY_NAME).first()
        except NameError:
            wok_category = None
            current_app.logger.error("WOK_CATEGORY_NAME is not defined, skipping Wok reordering.")

        if wok_category and category_id == str(wok_category.id):
            wok_constructor_product = None
            other_products = []

            for product in products:
                try:
                    is_constructor = str(product.id) == WOK_PRODUCT_CONSTRUCTOR_ID
                except NameError:
                    is_constructor = False

                if is_constructor:
                    wok_constructor_product = product
                else:
                    other_products.append(product)

            if wok_constructor_product:
                products = [wok_constructor_product] + other_products
            else:
                current_app.logger.warning(f"Wok constructor product not found.")
                products = other_products
        # --- END WOK REORDERING LOGIC ---

        marshaled_products = []
        for product in products:
            # --- Standard Data Processing (Unchanged) ---
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

            # Start with existing addons from the database relationship
            marshaled_available_addons = [
                api.marshal(pa.addon, addon_model)
                for pa in product.available_addons if pa.addon
            ]

            # --- CUSTOM ADDON LOGIC (Fixed) ---
            # FIX 3: Change 'product.category.name' to 'product.original_category.name'
            # Use main_category for the top-level check
            category_name = product.original_category.name if product.original_category else None

            # FIX (One-line and TypeError): Convert list of tuples/rows to list of strings
            main_category_names = [name for name, in db.session.query(MainCategory.name).all()]

            # The line being fixed from the prompt:
            #current_app.logger.info(f"any(cat in category_name for cat in main_category_names) = {any(cat in category_name for cat in main_category_names)}, category_name={category_name}")

            if any(cat in category_name for cat in main_category_names):
                # Get the pre-fetched list of addon products for this category
                category_id = None
                # FIX 4: Use product.main_category.name, as this is more likely the intended logic
                category = Category.query.filter(Category.name.like(f"%{product.main_category.name}%Добавки%")).first()

                if category:
                    category_id = str(category.id)
                addon_prods = addon_products_by_category.get(category_id, [])
                #current_app.logger.info(f"cat addon_products_by_category (lookup for {category_id}) -> {len(addon_prods)} products")

                for addon_prod in addon_prods:
                    manual_addon = {
                        'id': str(addon_prod.id),
                        'group_name': 'Добавки',
                        'name': addon_prod.name,
                        'price': float(addon_prod.price) if isinstance(addon_prod.price, Decimal) else addon_prod.price,
                        'image': addon_prod.image
                    }

                    marshaled_addon = api.marshal(manual_addon, addon_model)
                    marshaled_available_addons.append(marshaled_addon)

            # --- END CUSTOM ADDON LOGIC ---

            # Assemble final product dictionary for marshalling
            product_for_marshal = {
                'id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
                'image': product.image,
                'categoryId': str(product.main_category_id) if product.main_category_id else str(product.categoryId), # MainCategory ID
                'iikoCategoryId': str(product.categoryId), # IIKO category id
                'nutrition': nutrition_data_for_marshal,
                'ingredients': cleaned_ingredients,
                'availableAddons': marshaled_available_addons, # Contains both DB and manual addons
                'recommendations': marshaled_recommendations,
                'isCustomizable': product.is_customizable
            }
            # Final marshal using the defined model
            marshaled_products.append(api.marshal(product_for_marshal, product_model))

        return marshaled_products

## /products/<string:product_id> Endpoint
# ----------------------------------------------------------------------
@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, product_id):
        """Get a single product by ID"""
        # Load the product and necessary relationships
        product = Product.query.options(
            # FIX 5: Eager load the original category
            joinedload(Product.original_category),
            # Eager load the main category to check the name
            joinedload(Product.main_category),
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get_or_404(product_id)

        if product.is_hidden:
            api.abort(404, "Product not found or is hidden.")

        # --- Standard Data Processing for Marshalling (Unchanged) ---

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

        # Start with existing addons from the database relationship
        marshaled_available_addons = [
            api.marshal(pa.addon, addon_model)
            for pa in product.available_addons if pa.addon
        ]

        # --- Custom Addon Logic (Fixed) ---

        category_name = product.original_category.name if product.original_category else None

        # FIX (One-line and TypeError): Convert list of tuples/rows to list of strings
        main_category_names = [name for name, in db.session.query(MainCategory.name).all()]

        # The line being fixed from the prompt:
        # current_app.logger.info(f"any(cat in category_name for cat in main_category_names) = {any(cat in category_name for cat in main_category_names)}, category_name={category_name}")

        if any(cat in category_name for cat in main_category_names):
            try:
                # FIX 7: Fix the or_ expression using list unpacking on db.session.query and use original_category.name for the like clause
                addon_products = Product.query.options(
                    joinedload(Product.main_category),
                    # FIX 6: Eager load the original category for consistency
                    joinedload(Product.original_category)
                ).filter(
                    or_(
                        Product.original_category.name.like(f"%{name}%Добавки%")
                        for name in main_category_names
                    ),
                    Product.is_hidden == False # Ensure we only fetch available addons
                ).all()
                #current_app.logger.info(f"addon_products = {addon_products}")

                for addon_prod in addon_products:
                    # addon_category_name = addon_prod.category.name if addon_prod.category else None # Removed old category ref
                    # current_app.logger.info(f"addon_category_name = {addon_category_name}, category_name = {category_name}")

                    # Construct the addon dictionary from the matched product data
                    manual_addon = {
                        'id': str(addon_prod.id),
                        'group_name': 'Добавки',
                        'name': addon_prod.name, # Name is extracted from the category path match
                        # FIX: Robust Decimal to float conversion
                        'price': float(addon_prod.price) if isinstance(addon_prod.price, Decimal) else addon_prod.price,
                        'image': addon_prod.image
                    }

                    # Apply marshalling for consistency and append to the list
                    marshaled_addon = api.marshal(manual_addon, addon_model)
                    marshaled_available_addons.append(marshaled_addon)

            except Exception as e:
                # Log an error if the custom addon logic fails
                current_app.logger.error(f"Error processing manual addons for product {product.id}: {e}")

        # --- Continue Standard Marshalling (Unchanged) ---

        marshaled_recommendations = [
            api.marshal(pr.recommendation, recommendation_model)
            for pr in product.recommendations if pr.recommendation
        ]

        product_for_marshal = {
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
            'image': product.image,
            'categoryId': str(product.main_category_id) if product.main_category_id else str(product.categoryId),
            'iikoCategoryId': str(product.categoryId),
            'nutrition': nutrition_data_for_marshal,
            'ingredients': cleaned_ingredients,
            'availableAddons': marshaled_available_addons, # List now includes both DB and manual addons
            'recommendations': marshaled_recommendations,
            'isCustomizable': product.is_customizable
        }
        return product_for_marshal


## Order Endpoints

@api.route('/orders')
class OrderList(Resource):
    @api.marshal_with(order_model, as_list=True) # Use marshal_list_with for lists of orders
    def get(self):
        """Get all orders for a specific Telegram user and then hide them (set display_status=False)."""
        user_id = get_telegram_user_id() # MANDATORY HEADER

        # Retrieve orders for the given telegram_user_id and display_status=True
        # We fetch them first to serialize them before updating their display_status
        orders_to_display = Order.query.filter_by(user_id=user_id).options(
            joinedload(Order.items)
            .joinedload(OrderItem.product) # Load the main product for the order item
        ).order_by(
            desc(Order.created_at) # ADDED: Sort by created_at in descending order
        ).all()

        serialized_orders = []
        for order in orders_to_display: # Iterate through the fetched orders for serialization
            items_data = []
            for item in order.items:
                product_obj = item.product

                # Handle custom wok items where product_obj might be None
                if product_obj is None and item.custom_wok_data:
                    marshaled_product_in_order_item = None # No product to marshal for custom wok
                else:
                    # Marshal product details
                    product_marshaled_data = {
                        'id': str(product_obj.id),
                        'name': product_obj.name,
                        'description': product_obj.description,
                        'price': float(product_obj.price) if isinstance(product_obj.price, Decimal) else product_obj.price,
                        'image': product_obj.image,
                        'categoryId': str(product_obj.main_category_id),
                        'iikoCategoryId': str(product_obj.categoryId),
                        'nutrition': product_obj.nutrition,
                        'ingredients': product_obj.ingredients,
                        'availableAddons': [api.marshal(pa.addon, addon_model) for pa in product_obj.available_addons if pa.addon],
                        'recommendations': [api.marshal(pr.recommendation, recommendation_model) for pr in product_obj.recommendations if pr.recommendation],
                        'isCustomizable': product_obj.is_customizable
                    }
                    marshaled_product_in_order_item = api.marshal(product_marshaled_data, product_model)

                fetched_addons_with_quantity = []
                if item.selected_addons_data:
                    # Extract IDs to query addons efficiently in a single batch
                    addon_ids = [data['id'] for data in item.selected_addons_data]
                    if addon_ids:
                        addons_from_db = Addon.query.filter(Addon.id.in_(tuple(addon_ids))).all()
                        addon_map = {addon.id: addon for addon in addons_from_db} # Map for quick lookup

                        for addon_data in item.selected_addons_data:
                            addon_obj = addon_map.get(addon_data['id'])
                            if addon_obj:
                                fetched_addons_with_quantity.append(api.marshal({
                                    'addon': addon_obj,
                                    'quantity': addon_data['quantity']
                                }, selected_addon_with_quantity_model))

                fetched_recommendations_with_quantity = []
                if item.selected_recommendation_data:
                    # Extract IDs to query recommendations efficiently in a single batch
                    rec_ids = [data['id'] for data in item.selected_recommendation_data]
                    if rec_ids:
                        recs_from_db = Recommendation.query.filter(Recommendation.id.in_(tuple(rec_ids))).all()
                        rec_map = {rec.id: rec for rec in recs_from_db} # Map for quick lookup

                        for rec_data in item.selected_recommendation_data:
                            rec_obj = rec_map.get(rec_data['id'])
                            if rec_obj:
                                fetched_recommendations_with_quantity.append(api.marshal({
                                    'recommendation': rec_obj,
                                    'quantity': rec_data['quantity']
                                }, selected_recommendation_with_quantity_model))

                items_data.append({
                    'product': marshaled_product_in_order_item,
                    'quantity': item.quantity,
                    'selectedAddons': fetched_addons_with_quantity,
                    'selectedRecommendations': fetched_recommendations_with_quantity,
                    'customWokData': item.custom_wok_data,
                    'customPrice': float(item.custom_price) if item.custom_price is not None else None,
                    'customName': item.custom_name,
                })

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
                    'longitude': delivery_info_obj.longitude,
                    'postcode': delivery_info_obj.postcode,
                    'city_name': delivery_info_obj.city_name,
                    'street_name': delivery_info_obj.street_name,
                    'house_number': delivery_info_obj.house_number,
                    'delivery_price': float(delivery_info_obj.delivery_price) if delivery_info_obj.delivery_price is not None else None,
                }, delivery_info_model_new)


            serialized_orders.append({
                'id': str(order.id),
                'userId': order.user_id, # Changed 'telegramUserId' to 'userId' for consistency with model
                'items': items_data,
                'total': float(order.total) if isinstance(order.total, Decimal) else order.total,
                'deliveryInfo': delivery_info_for_response,
                'status': order.status,
                'createdAt': order.created_at.isoformat(),
                'estimatedDelivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                'paymentUrl': order.confirmation_url, # Mapped to paymentUrl
                'yookassaPaymentId': order.yookassa_payment_id, # Mapped to yookassaPaymentId
                'displayStatus': order.display_status
            })

        # --- NEW LOGIC: Set display_status = False for all orders of this user ---
        try:
            # Update all orders for the current user to set display_status to False
            # We do this after retrieving them to ensure the current request returns the 'True' ones.
            # If you want it to return 'False' immediately, this update should happen before fetching.
            # However, typically, you'd show them and then hide them for subsequent fetches.
            db.session.query(Order).filter_by(user_id=user_id, display_status=True).update({"display_status": False})
            db.session.commit()
            current_app.logger.info(f"All orders for Telegram user {user_id} set to display_status=False after retrieval.")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error setting display_status=False for user {user_id} orders: {e}", exc_info=True)
            # You might choose to abort here or just log and continue, depending on criticality.
            # For now, we'll just log and return the fetched (old status) orders.

        return serialized_orders

    @api.expect(request_order_payload_model)
    @api.marshal_with(order_model, code=201)
    def post(self):
        """Create a new order and send it to IIKO."""
        user_id = get_telegram_user_id()
        data = api.payload

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not latitude or not longitude:
            current_app.logger.error('Latitude and Longitude are required for delivery.')
            api.abort(400, "Latitude and Longitude are required for delivery.")

        point = Point(longitude, latitude)
        delivery_area_number = get_delivery_area_by_point(point)

        try:
            delivery_data = _get_delivery_data()
            delivery_price_mapping = delivery_data.get('DELIVERY_PRICE_MAPPING', {})
            free_delivery_threshold_mapping = delivery_data.get('FREE_DELIVERY_THRESHOLD_MAPPING', {})
            delivery_price_exceptions_mapping = delivery_data.get('DELIVERY_PRICE_EXCEPTIONS_MAPPING', {})
        except RuntimeError as e:
            current_app.logger.error(f"Failed to load delivery data: {e}")
            api.abort(503, "Failed to load delivery data. Please try again later.")

        # --- ИСПРАВЛЕНИЕ: Убираем 404 и выставляем MOCK параметры для внешних зон ---
        if delivery_area_number is None:
            current_app.logger.warning(f"Coordinates {latitude}, {longitude} are outside a valid delivery area. Applying MOCK fallback parameters.")

            delivery_price_base = Decimal('300.00')          # Mock сумма доставки (поменяй на любую удобную)
            free_delivery_threshold = Decimal('2000.00')      # Mock порог бесплатной доставки
            delivery_price_exceptions = {}
            delivery_area_number = 10                # Заменяем None строкой для предотвращения ошибок в IIKO
        else:
            delivery_price_base = Decimal(str(delivery_price_mapping.get(delivery_area_number, 0)))
            free_delivery_threshold = Decimal(str(free_delivery_threshold_mapping.get(delivery_area_number, 0)))
            delivery_price_exceptions = delivery_price_exceptions_mapping.get(delivery_area_number, {})

        nominatim_response = get_address_from_coordinates(latitude, longitude)

        street_name_from_coords = nominatim_response.get('address', {}).get('road') or ""
        nominatim_house_number = nominatim_response.get('address', {}).get('house_number')
        nominatim_postcode = nominatim_response.get('address', {}).get('postcode')
        nominatim_city = nominatim_response.get('address', {}).get('city') or nominatim_response.get('address', {}).get('town') or nominatim_response.get('address', {}).get('village')

        current_app.logger.info(f"Nominatim details: Road='{street_name_from_coords}', HouseNumber='{nominatim_house_number}', Postcode='{nominatim_postcode}', City='{nominatim_city}'")

        if nominatim_city:
            exception_price = delivery_price_exceptions.get(nominatim_city)
            if exception_price is not None:
                delivery_price_base = Decimal(str(exception_price))
                current_app.logger.info(f"Applying delivery price exception for city '{nominatim_city}': {delivery_price_base}")

        delivery_cost = Decimal('0.00')
        calculated_total = Decimal('0.00')

        cart_with_items = db.session.query(Cart).filter_by(user_id=user_id).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.selected_addons).joinedload(CartAddon.addon),
            joinedload(Cart.items).joinedload(CartItem.selected_recommendations).joinedload(CartRecommendation.recommendation)
        ).first()

        if not cart_with_items or not cart_with_items.items:
            current_app.logger.error(f'Cart user_id={user_id} is empty or could not load cart items.')
            api.abort(400, "Cart is empty or could not load cart items.")

        # Create the new Order and its relationships.
        delivery_info_obj = DeliveryInfo(
            address=data['address'],
            apartment=data.get('apartment'),
            floor=data.get('floor'),
            phone=data['phone'] if not USING_MOCK else '+79999999999',
            payment_method=data['paymentMethod'],
            comment=data.get('comment') if not USING_MOCK else "ТЕСТОВЫЙ ЗАКАЗ. НЕ ОБРАБАТЫВАТЬ.",
            latitude=data['latitude'],
            longitude=data['longitude'],
            postcode=nominatim_postcode,
            city_name=nominatim_city,
            street_name=street_name_from_coords,
            house_number=nominatim_house_number,
            delivery_price=delivery_cost
        )

        new_order = Order(
            user_id=user_id,
            total=Decimal('0.00'),  # Initialize to 0, will be updated after calculating items
            status='pending',
            created_at=datetime.now(timezone.utc),
            display_status=True,
            delivery_info=delivery_info_obj,
            items=[] # Start with an empty list for the relationship
        )
        db.session.add(new_order)

        for cart_item in cart_with_items.items:
            item_price = Decimal('0.00')
            product = None

            if cart_item.product_id:
                product = cart_item.product
                if not product:
                    current_app.logger.warning(f"Product with ID {cart_item.product_id} not found for cart item {cart_item.id}. Skipping.")
                    continue
                item_price += Decimal(str(product.price))
            elif cart_item.custom_wok_data:
                item_price += Decimal(str(cart_item.custom_price)) if cart_item.custom_price else Decimal('0.00')
            else:
                current_app.logger.warning(f"Cart item {cart_item.id} has no product or custom wok data. Skipping.")
                continue

            addon_list_for_order = []
            for cart_addon in cart_item.selected_addons:
                addon = cart_addon.addon
                if addon:
                    addon_quantity = cart_addon.quantity
                    item_price += Decimal(str(addon.price)) * addon_quantity
                    addon_list_for_order.append({"id": addon.id, "quantity": addon_quantity})

            rec_list_for_order = []
            for cart_rec in cart_item.selected_recommendations:
                recommendation = cart_rec.recommendation
                if recommendation:
                    rec_quantity = cart_rec.quantity
                    item_price += Decimal(str(recommendation.price)) * rec_quantity
                    rec_list_for_order.append({"id": recommendation.id, "quantity": rec_quantity})

            calculated_total += item_price * Decimal(str(cart_item.quantity))

            # Create OrderItem and append to the relationship
            new_order.items.append(OrderItem(
                product=product,
                quantity=cart_item.quantity,
                selected_addons_data=addon_list_for_order,
                selected_recommendation_data=rec_list_for_order,
                custom_wok_data=cart_item.custom_wok_data,
                custom_price=cart_item.custom_price,
                custom_name=cart_item.custom_name
            ))

        # Finalize calculations and update the new_order object
        if calculated_total < free_delivery_threshold:
            delivery_cost = delivery_price_base
        new_order.total = calculated_total + delivery_cost
        new_order.delivery_info.delivery_price = delivery_cost

        is_delivery_free = (delivery_cost == 0)
        current_app.logger.info(f"Order calculated total (without delivery): {calculated_total}, delivery cost: {delivery_cost}, final total: {new_order.total}")

        # Now, you can safely flush the session to get the new_order.id
        db.session.flush()

        iiko_token = iiko_service.get_iiko_token()
        if not iiko_token:
            current_app.logger.error("Failed to get IIKO access token for order creation.")
            db.session.rollback()
            api.abort(500, "Failed to connect to external ordering system (IIKO).")

        try:
            _get_iiko_essential_data(iiko_token, data['paymentMethod'], street_name_from_coords, nominatim_city)
        except RuntimeError as e:
            current_app.logger.error(f"IIKO address validation failed for order {new_order.id}: {e}", exc_info=True)
            db.session.rollback()
            api.abort(500, f"Delivery to the specified address is not possible: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error during IIKO address validation for order {new_order.id}: {e}", exc_info=True)
            db.session.rollback()
            api.abort(500, f"Internal error during address validation: {str(e)}")

        if data['paymentMethod'].lower() == 'online':
            if not yookassa_service:
                db.session.rollback()
                api.abort(500, "Сервис ЮKassa не настроен.")

            frontend_return_url = current_app.config.get('FRONTEND_ORDER_RETURN_URL', 'https://your-frontend-domain.com/order-status')
            payment_description = f"Заказ #{new_order.id} из {new_order.delivery_info.address}"

            yookassa_response = yookassa_service.create_payment(
                amount=new_order.total,
                description=payment_description,
                order_id=new_order.id,
                return_url=frontend_return_url,
                user_full_name=data.get("client_name", "client_name"),
                user_phone_number=phone,
                user_email=data.get("email", "customer@example.ru")
            )

            if yookassa_response and yookassa_response.get('confirmation', {}).get('confirmation_url'):
                new_order.yookassa_payment_id = yookassa_response['id']
                new_order.confirmation_url = yookassa_response['confirmation']['confirmation_url']
                new_order.status = 'pending_payment'
                current_app.logger.info(f"YuKassa payment initiated for order {new_order.id}. Confirmation URL: {new_order.confirmation_url}")
            else:
                new_order.status = 'payment_initiation_failed'
                current_app.logger.error(f"Failed to get confirmation_url from YuKassa for order {new_order.id}. Response: {yookassa_response}")
                db.session.rollback()
                api.abort(500, "Failed to initiate card payment.")

        else:
            order_to_send = db.session.query(Order).filter_by(id=new_order.id).options(
                joinedload(Order.delivery_info),
                joinedload(Order.items).joinedload(OrderItem.product)
            ).first()

            if not order_to_send:
                current_app.logger.error(f"Failed to load new_order {new_order.id} for IIKO sending after initial creation.")
                db.session.rollback()
                api.abort(500, "Internal error: Could not load order for external system integration.")

            _send_order_to_iiko_internal(
                order_to_send,
                iiko_token,
                data['paymentMethod'],
                street_name_from_coords,
                nominatim_postcode,
                nominatim_house_number,
                nominatim_city,
                delivery_area_number,
                is_delivery_free
            )
            new_order.status = 'sent_to_iiko'

        db.session.delete(cart_with_items)
        db.session.commit()

        created_order = db.session.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.delivery_info)
        ).get(new_order.id)

        # ------------ ИНТЕГРАЦИЯ С МИКРОСЕРВИСОМ АНАЛИТИКИ ------------
        try:
            analytics_payload = api.marshal(created_order, order_model)
            analytics_url = "http://analytics_service:5002/api/analytics/orders"
            requests.post(analytics_url, json=analytics_payload, timeout=1.5)
            current_app.logger.info(f"Successfully pushed order {created_order.id} to analytics microservice.")
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Analytics microservice is unavailable, order not pushed. Error: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error while sending data to analytics: {e}")
        # --------------------------------------------------------------

        return created_order, 201

    @api.expect(order_display_status_update_model)
    @api.marshal_with(order_model)
    def put(self):
        """Update the display status of an order for a specific Telegram user."""
        user_id = get_telegram_user_id() # MANDATORY HEADER
        data = api.payload
        order_id = data.get('orderId')
        display_status = data.get('displayStatus')

        if order_id is None or display_status is None:
            api.abort(400, "Both 'orderId' and 'displayStatus' are required.")

        order = Order.query.filter_by(id=order_id, user_id=user_id).first()

        if not order:
            api.abort(404, f"Order with ID '{order_id}' not found for the current user.")

        try:
            order.display_status = display_status
            db.session.commit()
            current_app.logger.info(f"Order {order_id} display status updated to {display_status} for user {user_id}.")
            
            # Load the updated order with relations for marshalling
            updated_order = db.session.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.delivery_info)
            ).get(order.id)
            return updated_order, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating display status for order {order_id}: {e}", exc_info=True)
            api.abort(500, "Failed to update order display status.")

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

    @api.marshal_with(cart_response_model)
    def get(self):
        """Get the current user's cart"""
        user_id = get_telegram_user_id()
        current_app.logger.info(f"/cart user_id={user_id}")

        # NOTE: The first call to get_or_create_cart(user_id) is redundant
        # as it's immediately overwritten by the explicit query below,
        # but kept to match the original logic flow.
        cart = get_or_create_cart(user_id)

        # Eager load related data for cart items
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
                    # FIX APPLIED HERE: Check if custom_wok_data is a dict
                    if isinstance(item.custom_wok_data, dict):
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
                    else:
                        current_app.logger.warning(f"CartItem ID {item.id} has invalid custom_wok_data type: {type(item.custom_wok_data)}")
                        item_description = "Custom Wok (Data Error)" # Fallback description


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

            try:
                if item.manual_addons_data:
                    manual_addons = item.manual_addons_data.get(item.product.id, [])

                    for ma in manual_addons:
                        addon_product = db.session.query(Product).filter(Product.id == ma["id"]).first()
                        addon_quantity = ma["qty"]
                        current_item_total_price += addon_product.price * addon_quantity
                        marshaled_selected_addons.append({
                            'id': str(ma["id"]),
                            'group_name': addon_product.original_category.name,
                            'name': addon_product.name,
                            'price': addon_product.price,
                            'image': ma["image"],
                            'quantity': addon_quantity
                        })
            except:
                raise

            marshaled_selected_recommendations = []
            for cr in item.selected_recommendations:
                if cr.recommendation:
                    rec_price = Decimal(str(cr.recommendation.price)) if cr.recommendation.price is not None else Decimal('0.0')
                    current_item_total_price += rec_price
                    # NOTE: Assuming recommendation_model is defined elsewhere
                    marshaled_selected_recommendations.append(api.marshal(cr.recommendation, recommendation_model))

            # Handle custom Wok details
            custom_wok_details = None
            if item.custom_wok_data:
                # ⭐ FIX APPLIED HERE: Check if custom_wok_data is a dict
                if isinstance(item.custom_wok_data, dict):
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
                'quantity': item.quantity,
                'priceTotal': float(current_item_total_price), # Use the calculated total price for this item
                'selectedAddons': marshaled_selected_addons,
                'selectedRecommendations': marshaled_selected_recommendations,
                # The commented out fields are kept as they were in the original user code
                #'customWok': custom_wok_details,
            })

        update_cart_total(cart) # Ensure cart.total is updated

        # When using @api.marshal_with, you return the data structure directly.
        # The original code's `jsonify(api.marshal(...))` is often simplified to
        # just returning the dict/object when using marshal_with, but here,
        # we'll use the original structure's return value to be safe.
        # NOTE: If you are using Flask-RestX properly, the jsonify and api.marshal
        # inside the return is usually not needed when using @api.marshal_with
        # but is kept to reflect the original code's return style.

        total = 0.0
        for item in marshaled_items:
            total += item["priceTotal"]

        return {
            'items': marshaled_items,
            'total': total
        }



@api.route('/cart/add')
class AddToCartResource(Resource):
    @api.expect(add_to_cart_request)
    @api.marshal_with(cart_response_model, code=201)
    def post(self):
        """Add an item to the cart, separating 'addons' into linked CartAddons and new CartItems (Products)."""
        user_id = get_telegram_user_id()
        current_app.logger.info(f"/cart/add user_id={user_id}")
        data = api.payload

        product_id = data.get('productId')
        quantity_to_add = data.get('quantity', 1)

        addons_data_from_frontend = data.get('addons', []) # [{'id': 'addon_or_product_id', 'quantity': 1}]
        recommendation_ids_from_frontend = data.get('recommendations', [])

        custom_wok_data = data.get('customWok')
        custom_name = data.get('customName')
        custom_description = data.get('customDescription')
        custom_price = data.get('customPrice')

        current_app.logger.debug(f"Received add to cart request: {data}")

        cart = get_or_create_cart(user_id)

        # List of items to eventually create/update in the cart.
        # This will hold the main product and any manual addon products.
        products_to_add = []
        separate_products_from_addons = [] # For new CartItem (Product model)

        # --- WOK PROCESSING ---
        if product_id == WOK_BUILDER_PRODUCT_ID:
            is_custom_item = True
            main_product_id = WOK_PRODUCT_CONSTRUCTOR_ID

            # Wok component conversion (Unchanged)
            converted_wok_addons = []
            if custom_wok_data:
                # Logic to convert Wok components to addon format
                base_id = custom_wok_data.get('baseId')
                if base_id: converted_wok_addons.append({'id': base_id, 'quantity': 1})
                for meat_id in custom_wok_data.get('meatIds', []): converted_wok_addons.append({'id': meat_id, 'quantity': 1})
                for topping_id in custom_wok_data.get('toppingIds', []): converted_wok_addons.append({'id': topping_id, 'quantity': 1})
                for sauce_id in custom_wok_data.get('sauceIds', []): converted_wok_addons.append({'id': sauce_id, 'quantity': 1})

            # For Wok, all 'addons' are treated as linked components (CartAddons)
            addons_to_process = addons_data_from_frontend + converted_wok_addons

            products_to_add.append({
                'id': main_product_id,
                'qty': quantity_to_add,
                'is_custom': True,
                'linked_addons': addons_to_process, # Linked for Wok
                'recs': recommendation_ids_from_frontend,
                'custom_wok_data': custom_wok_data,
                'custom_name': custom_name,
                'custom_description': custom_description,
                'custom_price': custom_price,
                'image': None
            })

        # --- REGULAR PRODUCT PROCESSING (Main Logic Fix) ---
        else:
            main_product = Product.query.get(product_id)
            if not main_product:
                api.abort(404, "Main Product not found.")

            # Step 1: Separate the IDs in the 'addons' payload
            linked_addons_to_create = []       # For CartAddon (real Addon model)

            for addon_data in addons_data_from_frontend:
                item_id = addon_data['id']
                item_quantity = addon_data.get('quantity', 1)

                # Try to find it as a real Addon first (linked to the main product)
                addon_obj = Addon.query.get(item_id)
                if addon_obj:
                    linked_addons_to_create.append(addon_data)
                    current_app.logger.debug(f"ID {item_id} identified as linked Addon.")
                    continue

                # If not a real Addon, try to find it as a Product (separate item)
                product_obj = Product.query.get(item_id)
                if product_obj:
                    separate_products_from_addons.append({
                        'id': item_id,
                        'qty': item_quantity,
                        'is_custom': False,
                        'linked_addons': [], # Manual addon products do not have linked addons
                        'recs': [],          # Manual addon products do not have linked recs
                        'image': product_obj.image
                    })
                    current_app.logger.debug(f"ID {item_id} identified as separate Product.")
                else:
                    current_app.logger.warning(f"ID {item_id} in 'addons' payload not found as either Addon or Product. Skipping.")


            # Step 2: Assemble the products_to_add list

            # A. The Main Product (with its *only* linked addons/recs)
            products_to_add.append({
                'id': product_id,
                'qty': quantity_to_add,
                'is_custom': False,
                'linked_addons': linked_addons_to_create,
                'recs': recommendation_ids_from_frontend,
                'image': main_product.image
            })

            # B. The separate Manual Addon Products
            #products_to_add.extend(separate_products_from_addons)

        # --- ITEM MATCHING AND CREATION LOOP ---

        for item_data in products_to_add:
            item_product_id = item_data['id']
            item_quantity = item_data['qty']
            is_custom_item = item_data['is_custom']

            existing_item = None

            # Standardizing linked data for comparison
            request_addons = sorted([{'id': a['id'], 'quantity': a.get('quantity', 1)} for a in item_data.get('linked_addons', [])], key=lambda x: x['id'])
            request_recs = sorted(item_data.get('recs', []))

            # Matching Logic
            for item in cart.items:
                if is_custom_item and item.custom_wok_data is not None:
                    # Match logic for Custom Wok (Unchanged)
                    if item.custom_wok_data == item_data['custom_wok_data'] and \
                       item.custom_name == item_data.get('custom_name') and \
                       item.custom_description == item_data.get('custom_description') and \
                       item.custom_price == (Decimal(str(item_data['custom_price'])) if item_data.get('custom_price') is not None else None):
                        existing_item = item
                        break

                elif not is_custom_item and item.product_id == item_product_id and item.custom_wok_data is None:
                    # Match logic for Regular Product (Now includes linked addons/recs)

                    # Check linked addons
                    current_addons = sorted([{'id': ca.addon_id, 'quantity': ca.quantity} for ca in item.selected_addons], key=lambda x: x['id'])
                    addons_match = (current_addons == request_addons)

                    # Check linked recommendations
                    current_recs = sorted([cr.recommendation_id for cr in item.selected_recommendations])
                    recs_match = (current_recs == request_recs)

                    if addons_match and recs_match:
                        existing_item = item
                        break

            # --- ITEM CREATION/UPDATE LOGIC ---
            if existing_item:
                existing_item.quantity += item_quantity
            else:
                new_cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=item_product_id,
                    quantity=item_quantity,

                    # Custom fields are ONLY stored for Custom Wok
                    custom_wok_data=item_data.get('custom_wok_data'),
                    custom_name=item_data.get('custom_name'),
                    custom_description=item_data.get('custom_description'),
                    custom_price=Decimal(str(item_data['custom_price'])) if item_data.get('custom_price') is not None else None,
                    custom_image=item_data.get('image'),
                    manual_addons_data={product_id: separate_products_from_addons}
                )
                db.session.add(new_cart_item)
                db.session.flush() # Flush to get new_cart_item.id

                # Process linked addons/recommendations
                # This applies to Wok (is_custom_item=True) AND the main regular product
                # if it has real addons attached (is_custom_item=False, but item_data['linked_addons'] is not empty).
                if item_data.get('linked_addons'):
                    # Process linked addons (Wok components or regular product addons)
                    for addon_data in item_data['linked_addons']:
                        addon_obj = Addon.query.get(addon_data['id'])
                        if addon_obj:
                            cart_addon = CartAddon(
                                cart_item_id=new_cart_item.id,
                                addon_id=addon_obj.id,
                                quantity=addon_data.get('quantity', 1)
                            )
                            db.session.add(cart_addon)
                        else:
                            current_app.logger.warning(f"Linked Addon with ID {addon_data['id']} not found in Addon model during item creation. This should not happen.")

                # Process recommendations (only linked to the main item, not manual addon products)
                for rec_id in item_data.get('recs', []):
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

        updated_cart_data = CartResource().get()
        return api.marshal(updated_cart_data, cart_response_model), 201

@api.route('/cart/update')
class UpdateCartItemResource(Resource):
    @api.expect(update_cart_item_request)
    @api.marshal_with(cart_response_model)
    def put(self):
        """Update the quantity of a specific item in the cart."""
        user_id = get_telegram_user_id()
        current_app.logger.info(f"/cart/update user_id={user_id}")
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
        current_app.logger.info(f"/cart/remove user_id={user_id}")
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
        current_app.logger.info(f"/cart/clear user_id={user_id}")
        cart = get_or_create_cart(user_id)
        # Delete all cart items associated with this cart
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
        update_cart_total(cart) # This will set total to 0
        
        # Corrected line: Instantiate CartResource and call its get method
        updated_cart_data = CartResource().get() 
        return api.marshal(updated_cart_data, cart_response_model)

# --- Configuration ---
DELIVERY_COST_MOCK = 100

# IMPORTANT: User-Agent for Nominatim API
# Replace 'YourDeliveryApp/1.0 (your.email@example.com)' with your actual app name and email.
NOMINATIM_USER_AGENT = "MyDeliveryApp/1.0 (delivery-support@my-delivery-app.ru)"

# Store loaded polygons globally
VALID_DELIVERY_AREAS = []

# --- MODIFIED get_address_from_coordinates function ---
# Структурированная заглушка, соответствующая формату Nominatim
MOCK_ADDRESS = {
    "place_id": 0,
    "licence": "Mock Data",
    "display_name": "Тестовый адрес (Сервис геокодирования недоступен)",
    "address": {
        "road": "Неизвестная улица",
        "house_number": "0",
        "city": "Город",
        "town": "Город",  # Добавлено, так как Nominatim часто присылает 'town' вместо 'city'
        "country": "Россия",
        "country_code": "ru"
    }
}

def get_address_from_coordinates(latitude, longitude):
    """
    Retrieves the full Nominatim response for given latitude and longitude coordinates.
    Returns a mock address if the request fails or returns an empty response.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict: The full JSON response dictionary from Nominatim if successful,
              otherwise MOCK_ADDRESS.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": latitude,
        "lon": longitude,
        "zoom": 18,
        "addressdetails": 1
    }

    # Передаем рабочий User-Agent и просим ответ на русском языке
    headers = {
        "User-Agent": NOMINATIM_USER_AGENT,
        "Accept-Language": "ru"
    }

    try:
        # Добавлен timeout=5 секунд, чтобы внешняя сеть не вешала ваш API-поток
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data:
            return data
        else:
            current_app.logger.warning(f"Empty response from Nominatim for coordinates: {latitude}, {longitude}")
            return MOCK_ADDRESS

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error making request to Nominatim: {e}")
        return MOCK_ADDRESS
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON response: {e}")
        try:
            current_app.logger.error(f"Raw response content: {response.text}")
        except NameError:
            pass
        return MOCK_ADDRESS

# --- Delivery Data Loading and Caching ---
_delivery_areas_cache = {}
_last_geojson_hash = None

def load_geojson_polygon(geojson_geometry):
    """
    Converts a GeoJSON geometry object into a Shapely Polygon.
    This assumes a closed loop of coordinates even for LineString.
    """
    if geojson_geometry['type'] == 'LineString' or geojson_geometry['type'] == 'Polygon':
        coords = geojson_geometry['coordinates']
        if geojson_geometry['type'] == 'Polygon':
            coords = coords[0]
            
        return Polygon([(coord[0], coord[1]) for coord in coords])
    return None

def _parse_delivery_description(description):
    """
    Parses a product description string to extract delivery-related information.
    The values are returned as integers.
    """
    # Initialize defaults
    threshold = None
    price_base = None
    exceptions = {}

    # Regex for threshold and base price: "от {threshold} рублей; доставка {price} рублей"
    base_match = re.search(r"от (\d+) рублей; доставка (\d+) рублей", description)
    if base_match:
        threshold = int(base_match.group(1))
        price_base = int(base_match.group(2))

    # Regex for exceptions, which may contain a comma-separated list of locations
    exceptions_match = re.search(r"\*Исключение: (.+)", description)
    if exceptions_match:
        exceptions_str = exceptions_match.group(1)
        # This new regex captures the comma-separated locations and the single price for them
        list_exception_match = re.search(r"(.+?)\s*-\s*доставка\s*(\d+)\s*рублей", exceptions_str)
        if list_exception_match:
            locations_str = list_exception_match.group(1)
            exception_price = int(list_exception_match.group(2))
            
            # Split the locations by comma and add each one to the dictionary
            for location in locations_str.split(','):
                location_name = location.strip()
                if location_name:
                    exceptions[location_name] = exception_price

    return {
        'free_delivery_threshold': threshold,
        'delivery_price_base': price_base,
        'delivery_price_exceptions': exceptions
    }

def _get_delivery_data():
    """
    Loads delivery areas, prices, and thresholds from the GeoJSON data and product descriptions,
    using a cache with hashing to avoid re-processing if the data hasn't changed.
    """
    global _delivery_areas_cache, _last_geojson_hash

    geojson_data = get_geojson_data()
    current_geojson_hash = hash(json.dumps(geojson_data, sort_keys=True))

    if _last_geojson_hash == current_geojson_hash:
        current_app.logger.debug("Delivery data hash unchanged, using cached data.")
        return _delivery_areas_cache

    current_app.logger.info("Delivery data hash changed or cache is empty. Reloading delivery data.")

    try:
        new_delivery_areas = []
        delivery_price_mapping = {}
        free_delivery_threshold_mapping = {}
        delivery_price_exceptions_mapping = {}

        for feature in geojson_data['features']:
            properties = feature.get('properties', {})
            geojson_geometry = feature.get('geometry')
            
            area_number = properties.get('area_number')

            if area_number is None:
                continue

            # --- START: NEW LOGIC TO RETRIEVE DATA FROM PRODUCT DESCRIPTION ---
            delivery_item_id = DELIVERY_PRODUCT_IDS.get(area_number)
            if not delivery_item_id:
                current_app.logger.warning(f"No product ID found for delivery area {area_number}. Skipping.")
                continue

            delivery_product = Product.query.get(delivery_item_id)
            if not delivery_product or not delivery_product.description:
                current_app.logger.warning(f"Product {delivery_item_id} or its description is missing. Skipping area {area_number}.")
                continue
            
            parsed_data = _parse_delivery_description(delivery_product.description)

            delivery_price_base = parsed_data['delivery_price_base']
            free_delivery_threshold = parsed_data['free_delivery_threshold']
            delivery_price_exceptions = parsed_data['delivery_price_exceptions']

            if not all([delivery_price_base, free_delivery_threshold]):
                 current_app.logger.warning(f"Could not parse delivery details from product description for area {area_number}. Skipping.")
                 continue
            # --- END: NEW LOGIC ---

            if geojson_geometry:
                polygon = load_geojson_polygon(geojson_geometry)
                if polygon and polygon.is_valid:
                    new_delivery_areas.append({
                        'polygon': polygon,
                        'area_number': area_number,
                        'delivery_price_base': delivery_price_base,
                        'free_delivery_threshold': free_delivery_threshold,
                        'delivery_price_exceptions': delivery_price_exceptions
                    })
                    # Populate the mappings for easy lookup
                    delivery_price_mapping[area_number] = delivery_price_base
                    free_delivery_threshold_mapping[area_number] = free_delivery_threshold
                    delivery_price_exceptions_mapping[area_number] = delivery_price_exceptions

        _delivery_areas_cache = {
            'DELIVERY_AREAS': new_delivery_areas,
            'DELIVERY_PRICE_MAPPING': delivery_price_mapping,
            'FREE_DELIVERY_THRESHOLD_MAPPING': free_delivery_threshold_mapping,
            'DELIVERY_PRICE_EXCEPTIONS_MAPPING': delivery_price_exceptions_mapping
        }
        _last_geojson_hash = current_geojson_hash
        current_app.logger.info(f"Delivery data reloaded successfully. {len(new_delivery_areas)} areas loaded.")

    except Exception as e:
        current_app.logger.error(f"Error loading delivery data: {e}")
        _delivery_areas_cache = {}
        _last_geojson_hash = None
        raise RuntimeError(f"Error loading delivery data: {e}")

    return _delivery_areas_cache

def get_delivery_area_by_point(point):
    """
    Finds the delivery area number for a given point.
    
    Args:
        point (shapely.geometry.Point): The point to check.
        
    Returns:
        int or None: The area_number if the point is within a polygon, otherwise None.
    """
    delivery_data = _get_delivery_data()
    DELIVERY_AREAS = delivery_data.get('DELIVERY_AREAS', [])
    
    for area in DELIVERY_AREAS:
        if area['polygon'].contains(point):
            return area['area_number']
            
    return None

# Define the model for the detailed address components (nested inside Nominatim response)
address_details_model = api.model('AddressDetails', {
    'house_number': fields.String(description='House number', required=False),
    'road': fields.String(description='Street name', required=False),
    'residential': fields.String(description='Residential area (e.g., neighborhood)', required=False),
    'suburb': fields.String(description='Suburb or district', required=False),
    'city': fields.String(description='City', required=False),
    'county': fields.String(description='County', required=False),
    'state': fields.String(description='State or province', required=False),
    'postcode': fields.String(description='Postal code', required=False),
    'country': fields.String(description='Country', required=False),
    'country_code': fields.String(description='Two-letter country code', required=False),
    # Add any other specific address details you expect from Nominatim's 'address' object
    'building': fields.String(description='Building name', required=False),
    'amenity': fields.String(description='Amenity type (e.g., restaurant, park)', required=False),
    'tourism': fields.String(description='Tourism object (e.g., monument)', required=False),
})


# Define the model for the FULL Nominatim response
nominatim_response_model = api.model('NominatimResponse', {
    'place_id': fields.Integer(description='Unique ID of the Nominatim entry', required=False),
    'licence': fields.String(description='Nominatim usage licence', required=False),
    'osm_type': fields.String(description='OpenStreetMap object type', required=False),
    'osm_id': fields.Integer(description='OpenStreetMap object ID', required=False),
    'lat': fields.String(description='Latitude of the found object', required=False), # Nominatim sends as string
    'lon': fields.String(description='Longitude of the found object', required=False), # Nominatim sends as string
    'display_name': fields.String(description='Full formatted address string', required=False),
    'address': fields.Nested(address_details_model, description='Detailed address breakdown', required=False, skip_none=True),
    'boundingbox': fields.List(fields.String, description='Bounding box coordinates', required=False),
    # You can add other top-level fields from Nominatim response if you need them documented,
    # e.g., 'namedetails', 'extratags', etc.
})

# Define the output model for the /map endpoint
map_output_model = api.model('MapResponse', {
    'nominatim_details': fields.Nested(nominatim_response_model, description='Full structured Nominatim API response', skip_none=True),
    'delivery_cost': fields.Float(description='Cost of delivery for the area', example=5.00, required=False),
    'message': fields.String(description='Additional message (e.g., why delivery is not available)', required=False),
})

# Define a request parser for query parameters
map_query_parser = reqparse.RequestParser()
map_query_parser.add_argument('latitude', type=float, help='Latitude of the location', required=True, location='args')
map_query_parser.add_argument('longitude', type=float, help='Longitude of the location', required=True, location='args')

@api.route('/map')
class MapResource(Resource):
    @api.expect(map_query_parser)
    @api.marshal_with(map_output_model)
    def get(self):
        """
        Safely checks delivery area and cost.
        Never throws 500, uses mock fallbacks if frontend data is missing.
        """
        # Инициализируем парсер. Даже если он настроен строго, берем данные через .get()
        args = map_query_parser.parse_args()

        # --- БЕЗОПАСНЫЙ СБОР ДАННЫХ ИЗ ФРОНТЕНДА ---
        # Если фронтенд не прислал координаты, берем тестовую точку (Черноголовка)
        latitude = args.get('latitude') or 56.0167
        longitude = args.get('longitude') or 38.3833

        # ФИКС KEYERROR: используем .get() вместо прямых скобок []
        raw_order_price = args.get('order_price')
        if raw_order_price is not None:
            order_price = Decimal(str(raw_order_price))
        else:
            current_app.logger.warning("Frontend missed 'order_price'. Using mock fallback: 0.00")
            order_price = Decimal('0.00')

        # --- ОБРАБОТКА ЗОНЫ ДОСТАВКИ ---
        point = Point(longitude, latitude)
        delivery_area_number = get_delivery_area_by_point(point)

        # Если точка вне зоны, вместо ошибки 404 или падения, подставляем mock-зону №1
        if delivery_area_number is None:
            current_app.logger.warning(f"Coordinates {latitude}, {longitude} are outside areas. Forcing mock area '1'.")
            delivery_area_number = 1
            is_mock_area = True
        else:
            is_mock_area = False

        # --- БЕЗОПАСНАЯ ЗАГРУЗКА КОНФИГУРАЦИИ ДОСТАВКИ ---
        try:
            delivery_data = _get_delivery_data()
        except Exception as e:
            # Если база данных или конфиг IIKO легли — не падаем, создаем пустой mock-конфиг
            current_app.logger.error(f"Critical: Failed to load delivery data ({e}). Using empty mock dict.")
            delivery_data = {}

        delivery_price_mapping = delivery_data.get('DELIVERY_PRICE_MAPPING', {})
        free_delivery_threshold_mapping = delivery_data.get('FREE_DELIVERY_THRESHOLD_MAPPING', {})
        delivery_price_exceptions_mapping = delivery_data.get('DELIVERY_PRICE_EXCEPTIONS_MAPPING', {})

        # Безопасно вытаскиваем настройки для текущей зоны (с дефолтами 0)
        delivery_price_base = Decimal(str(delivery_price_mapping.get(delivery_area_number, 0)))
        free_delivery_threshold = Decimal(str(free_delivery_threshold_mapping.get(delivery_area_number, 0)))
        delivery_price_exceptions = delivery_price_exceptions_mapping.get(delivery_area_number, {})

        time.sleep(0.5)

        # --- ГЕОКОДИРОВАНИЕ (NOMINATIM) ---
        full_nominatim_response = get_address_from_coordinates(latitude, longitude)

        # Двойная подстраховка: если функция вернула None, принудительно берем глобальный MOCK_ADDRESS
        if not full_nominatim_response:
            full_nominatim_response = MOCK_ADDRESS

        # Безопасно парсим город из ответа
        address_dict = full_nominatim_response.get('address', {})
        nominatim_city = (
            address_dict.get('city') or
            address_dict.get('town') or
            address_dict.get('village')
        )

        # Проверяем исключения по городам
        if nominatim_city:
            exception_price = delivery_price_exceptions.get(nominatim_city)
            if exception_price is not None:
                delivery_price_base = Decimal(str(exception_price))

        # --- РАСЧЕТ ИТОГОВОЙ СТОИМОСТИ ДОСТАВКИ ---
        final_delivery_cost = Decimal('0.00')
        if order_price < free_delivery_threshold:
            final_delivery_cost = delivery_price_base

        delivery_area_name = f"Area {delivery_area_number}"

        # --- ФОРМИРОВАНИЕ УСПЕШНОГО ОТВЕТА (ВСЕГДА 200 OK) ---
        if full_nominatim_response.get("place_id") == 0 or is_mock_area:
            message = f"Warning: Backend is running in mock/fallback mode for area '{delivery_area_name}'."
        else:
            message = f"Success: Coordinates are in the '{delivery_area_name}' delivery area."

        return {
            "nominatim_details": full_nominatim_response,
            "delivery_cost": float(final_delivery_cost),
            "message": message
        }, 200

# Define response models if you want to explicitly document the output structure
# For simplicity, we'll return raw JSON, but it's good practice to define models
city_model = api.model('City', {
    'id': fields.String(description='City ID'),
    'name': fields.String(description='City Name'),
    'externalId': fields.String(description='External ID (if any)', required=False),
})

city_list_model = api.model('CityList', {
    'organizationId': fields.String(description='Organization ID'),
    'items': fields.List(fields.Nested(city_model), description='List of cities for the organization')
})

street_model = api.model('Street', {
    'id': fields.String(description='Street ID'),
    'name': fields.String(description='Street Name'),
    'externalId': fields.String(description='External ID (if any)', required=False),
    'classifierId': fields.String(description='Classifier ID (if any)', required=False),
})

# --- /api/cities endpoint ---
@api.route('/cities')
class CitiesResource(Resource):
    @api.doc('get_cities')
    @api.marshal_list_with(city_list_model) # Marshal as a list of organization city lists
    def get(self):
        """
        Returns a list of cities from IIKO for all available organizations.
        """
        current_app.logger.info("API call: /api/cities")
        try:
            iiko_token = iiko_service.get_iiko_token()
            if not iiko_token:
                api.abort(500, "Failed to obtain IIKO token.")

            # Get all organization IDs to fetch cities for them
            organizations = iiko_service.get_organizations(iiko_token)
            organization_ids = [org['id'] for org in organizations if 'id' in org]

            if not organization_ids:
                return [], 200 # No organizations found

            # Call the cached get_cities function
            cities_data = iiko_service.get_cities(organization_ids)

            return cities_data, 200
        except Exception as e:
            current_app.logger.error(f"Error fetching cities: {e}", exc_info=True)
            api.abort(500, f"Error fetching cities from IIKO: {e}")

# --- /api/streets endpoint ---
@api.route('/streets')
class StreetsResource(Resource):
    @api.doc('get_streets')
    @api.marshal_list_with(street_model) # Marshal as a list of streets
    def get(self):
        """
        Returns a list of streets for a specific city ("Черноголовка") from IIKO.
        """
        current_app.logger.info("API call: /api/streets for 'Черноголовка'")
        try:
            iiko_token = iiko_service.get_iiko_token()
            if not iiko_token:
                api.abort(500, "Failed to obtain IIKO token.")

            # 1. Find the organization ID (assuming you have one primary organization)
            organizations = iiko_service.get_organizations(iiko_token)
            if not organizations:
                api.abort(500, "No organizations found from IIKO API.")
            
            organization_id = organizations[0]['id'] # Use the first organization ID

            # 2. Find the city ID for "Черноголовка"
            cities_for_org = iiko_service.get_cities([organization_id])
            chernogolovka_city_id = None
            for org_cities in cities_for_org:
                if org_cities.get('organizationId') == organization_id:
                    for city in org_cities.get('items', []):
                        if city.get('name') == "Черноголовка":
                            chernogolovka_city_id = city['id']
                            break
                if chernogolovka_city_id:
                    break

            if not chernogolovka_city_id:
                api.abort(404, "City 'Черноголовка' not found in IIKO for the primary organization.")

            # 3. Get streets by the found city ID and organization ID
            streets_data = iiko_service.get_streets_by_city(organization_id, chernogolovka_city_id)

            return streets_data, 200
        except Exception as e:
            current_app.logger.error(f"Error fetching streets: {e}", exc_info=True)
            api.abort(500, f"Error fetching streets from IIKO: {e}")

import traceback

# Error handling for the API blueprint
@api_bp.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        # Handle known HTTP exceptions
        response = jsonify({
            'message': e.description,
            'status': e.code,
            'error_type': e.__class__.__name__
        })
        response.status_code = e.code
        return response
    
    # Handle all other, unexpected exceptions
    # Capture the full backtrace as a string
    backtrace_str = traceback.format_exc()
    
    # Log the error for internal records (even if you can't access them directly)
    current_app.logger.error(
        f"An unhandled error occurred: {e}",
        exc_info=True
    )
    
    response = jsonify({
        'message': 'An unexpected error occurred. Please try again later.',
        'status': InternalServerError.code,
        'error_type': 'InternalServerError',
        'details': backtrace_str  # This is the key change
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

import ipaddress # For IP address checking

# --- Configuration for Yookassa IP Whitelist ---
# These are the IP ranges provided by Yookassa
YOOKASSA_IP_WHITELIST = [
    ipaddress.ip_network('185.71.76.0/27'),
    ipaddress.ip_network('185.71.77.0/27'),
    ipaddress.ip_network('77.75.153.0/25'),
    ipaddress.ip_network('77.75.156.11'), # Single IP, represented as a /32 network
    ipaddress.ip_network('77.75.156.35'), # Single IP, represented as a /32 network
    ipaddress.ip_network('77.75.154.128/25'),
    ipaddress.ip_network('2a02:5180::/32')
]

@payment_webhook_ns.route('/callback')
class PaymentCallback(Resource):
    @api.doc(responses={200: 'Success', 400: 'Invalid Request', 403: 'Forbidden'})
    def post(self):
        """Обработка вебхуков платежей ЮKassa с проверкой подлинности."""
        current_app.logger.info("Получен вебхук ЮKassa.")

        # Log all received headers for debugging
        current_app.logger.info("Полученные заголовки:")
        for header, value in request.headers.items():
            current_app.logger.info(f"  {header}: {value}")

        # --- 1. IP Address Check (Second level of security) ---
        client_ip = request.remote_addr
        if not client_ip:
            current_app.logger.warning("Не удалось получить IP-адрес клиента для вебхука ЮKassa.")
            return {"message": "Forbidden: Unable to determine client IP"}, 403

        is_trusted_ip = False
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            for trusted_network in YOOKASSA_IP_WHITELIST:
                if client_ip_obj in trusted_network:
                    is_trusted_ip = True
                    break
        except ValueError:
            current_app.logger.error(f"Некорректный формат IP-адреса: {client_ip}")
            return {"message": "Forbidden: Invalid IP address format"}, 403

        if (not is_trusted_ip) and (not current_app.config.get('DEV_NO_IP_ADDRESS_CHECK_FAIL', False)):
            current_app.logger.warning(f"Вебхук ЮKassa получен с неизвестного IP-адреса: {client_ip}")
            return {"message": "Forbidden: Untrusted IP address"}, 403
            
        current_app.logger.info(f"Вебхук ЮKassa получен с доверенного IP-адреса: {client_ip}")

        # --- Continue processing payload ---
        try:
            payload = request.json
            if not payload:
                current_app.logger.error("Вебхук ЮKassa: JSON-payload не получен.")
                return {'message': 'No JSON payload'}, 400
                
            current_app.logger.info(f"Содержимое вебхука ЮKassa: {json.dumps(payload, indent=2, ensure_ascii=False)}")

            event = payload.get('event')
            payment_object = payload.get('object')

            if not event or not payment_object:
                current_app.logger.error(f"Вебхук ЮKassa: Отсутствуют 'event' или 'object' в payload: {payload}")
                return {'message': 'Invalid webhook payload structure'}, 400

            payment_id = payment_object.get('id')
            webhook_status = payment_object.get('status') # Status from webhook
            order_id = payment_object.get('metadata', {}).get('order_id') # Our internal order ID

            if not payment_id or not webhook_status or not order_id:
                current_app.logger.error(f"Вебхук ЮKassa: Отсутствуют важные поля (id, status, или metadata.order_id): {payload}")
                return {'message': 'Missing vital payment details'}, 400

            current_app.logger.info(f"Получен вебхук ЮKassa для платежа {payment_id} (Заказ {order_id}), событие: {event}, статус (из вебхука): {webhook_status}")

            # --- 2. Object Status Check (Main security level) ---
            if yookassa_service is None:
                current_app.logger.error("Yookassa Service не инициализирован. Невозможно проверить статус платежа.")
                return {'message': 'Yookassa service not configured'}, 500

            try:
                actual_payment_details = yookassa_service.get_payment_status(payment_id)
                
                if not actual_payment_details:
                    current_app.logger.error(f"Не удалось получить актуальные детали платежа {payment_id} от ЮKassa API.")
                    return {'message': 'Failed to retrieve payment details from Yookassa'}, 500

                actual_status = actual_payment_details.get('status')
                current_app.logger.info(f"Актуальный статус платежа {payment_id} по API ЮKassa: {actual_status}")

                # Compare webhook status with actual API status
                if actual_status != webhook_status:
                    current_app.logger.warning(f"Несоответствие статусов для платежа {payment_id}. Вебхук: {webhook_status}, API: {actual_status}.")
                    # Strict approach: reject if statuses don't match
                    return {'message': 'Forbidden: Status mismatch with Yookassa API'}, 403 
                else:
                    current_app.logger.info(f"Статус платежа {payment_id} подтвержден по API ЮKassa.")

            except Exception as e:
                current_app.logger.error(f"Ошибка при проверке статуса платежа {payment_id} через API ЮKassa: {e}", exc_info=True)
                # If status verification fails, it's a serious security concern.
                return {'message': 'Payment status verification failed'}, 500


            # Load the order with its delivery_info and product for OrderItems.
            # No change needed here for addons/recommendations as they are now parsed from JSON fields
            # within _send_order_to_iiko_internal
            order = db.session.query(Order).filter_by(id=order_id).options(
                joinedload(Order.delivery_info),
                joinedload(Order.items).joinedload(OrderItem.product)
            ).first()

            if not order:
                current_app.logger.error(f"Вебхук ЮKassa: Заказ {order_id} не найден в БД для платежа {payment_id}.")
                return {'message': 'Order not found'}, 404

            # Update order's yookassa_payment_id if not already set
            if not order.yookassa_payment_id:
                order.yookassa_payment_id = payment_id
                db.session.add(order)

            if event == 'payment.succeeded':
                # Only process if order is in a state expecting payment
                if order.status == 'pending_payment' or order.status == 'payment_initiation_failed': 
                    current_app.logger.info(f"Платеж успешно завершен для заказа {order_id}. Попытка отправить в IIKO.")

                    try:
                        iiko_token = iiko_service.get_iiko_token()
                        if not iiko_token:
                            current_app.logger.error(f"Вебхук: Не удалось получить токен IIKO для заказа {order.id}.")
                            order.status = 'iiko_send_failed_no_token'
                            db.session.commit()
                            return {'message': 'IIKO token unavailable'}, 500

                        # Pass the necessary parameters from DeliveryInfo
                        # Ensure DeliveryInfo has 'street_name' and 'house_number' fields.
                        _send_order_to_iiko_internal(
                            order,
                            iiko_token,
                            'online', # For successful Yookassa payment, it's always online
                            str(order.delivery_info.street_name), # NEW: Pass street_name from DB
                            order.delivery_info.postcode,         # NEW: Pass postcode from DB
                            order.delivery_info.house_number, # NEW: Pass house_number from DB
                            str(order.delivery_info.city_name),
                            get_delivery_area_by_point(Point(order.delivery_info.longitude, order.delivery_info.latitude)),
                            order.delivery_info.delivery_price == 0
                        )
                        order.status = 'sent_to_iiko'
                        current_app.logger.info(f"Заказ {order.id} успешно отправлен в IIKO через вебхук.")

                    except RuntimeError as e: # Catch custom RuntimeErrors from _send_order_to_iiko_internal
                        order.status = 'iiko_send_failed'
                        current_app.logger.error(f"Failed to send order {order.id} to IIKO via webhook: {e}")
                        db.session.rollback()
                        return {'message': f'IIKO integration failed after payment success: {str(e)}'}, 500
                    except Exception as e:
                        current_app.logger.error(f"Error sending order {order.id} to IIKO after YuKassa success: {e}", exc_info=True)
                        order.status = 'iiko_send_failed_exception'
                        db.session.rollback()
                        return {'message': f'Internal server error during IIKO integration: {str(e)}'}, 500
                else:
                    current_app.logger.info(f"Вебхук ЮKassa: Платеж {payment_id} успешно завершен для заказа {order_id}, но статус заказа уже был '{order.status}'. Никаких действий не требуется.")

            elif event == 'payment.canceled':
                order.status = 'payment_canceled'
                current_app.logger.warning(f"Вебхук ЮKassa: Платеж {payment_id} отменен для заказа {order_id}.")
            elif event == 'payment.waiting_for_capture':
                order.status = 'waiting_for_capture'
                current_app.logger.info(f"Вебхук ЮKassa: Платеж {payment_id} ожидает захвата для заказа {order_id}.")
            else:
                current_app.logger.warning(f"Вебхук ЮKassa: Необработанное событие '{event}' для платежа {payment_id}.")

            db.session.commit() # Save changes to order status
            return {'message': 'Webhook processed successfully'}, 200

        except json.JSONDecodeError:
            current_app.logger.error("Некорректное JSON-тело запроса.")
            return {"message": "Invalid JSON payload"}, 400
        except Exception as e:
            db.session.rollback() # Rollback transaction in case of any unexpected error
            current_app.logger.error(f"Ошибка при обработке вебхука ЮKassa: {e}", exc_info=True)
            return {'message': f'Internal server error: {str(e)}'}, 500
