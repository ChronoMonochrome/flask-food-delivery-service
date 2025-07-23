# app/api.py

import traceback
from flask import Blueprint, jsonify, current_app, request
from flask_restx import Api, Namespace, Resource, fields, reqparse
from werkzeug.exceptions import HTTPException, InternalServerError
from app.models import (
    db, DeliveryInfo, MainCategory, Category, Product, ProductAddon, Addon, Recommendation,
    Order, OrderItem, ProductRecommendation, Cart, CartItem, CartAddon, CartRecommendation,
    WokBase, WokMeat, WokTopping, WokSauce, WOK_PRODUCT_CONSTRUCTOR_ID, WOK_BUILDER_PRODUCT_ID,
    WOK_CATEGORY_NAME, DELIVERY_100_PRODUCT_ID
)
from app import iiko_service # Assuming this is your IIKO integration service
from app.iiko_service import USING_MOCK
from sqlalchemy import distinct # Import distinct for unique values
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
    'longitude': fields.Float(required=True, description='Longitude for delivery'),
    'postcode': fields.String(description='Postal code', allow_null=True), # Existing new field
    'street_name': fields.String(description='Street name from geocoding', allow_null=True), # NEW FIELD
    'house_number': fields.String(description='House number from geocoding', allow_null=True) # NEW FIELD
})

order_item_model = api.model('OrderItem', {
    'product': fields.Nested(product_model, description='Product details'),
    'quantity': fields.Integer(required=True, description='Quantity of the product'),
    'selectedAddons': fields.List(fields.Nested(addon_model), description='Selected addons for this product item', default=[]),
    'selectedRecommendations': fields.List(fields.Nested(recommendation_model), description='Selected recommendations for this product item', default=[])
})

order_model = api.model('Order', {
    'id': fields.String(required=True, description='Order ID'),
    'userId': fields.String(required=True, description='Telegram User ID'),
    'items': fields.List(fields.Nested(order_item_model), description='List of items in the order'),
    'total': fields.Float(required=True, description='Total price of the order'),
    'deliveryInfo': fields.Nested(delivery_info_model_new, required=True, description='Delivery information'),
    'status': fields.String(required=True, description='Current status of the order'),
    'createdAt': fields.DateTime(dt_format='iso8601', description='Timestamp of order creation'),
    'estimatedDelivery': fields.DateTime(dt_format='iso8601', description='Estimated delivery time', allow_null=True),
    'paymentUrl': fields.String(description='URL for online payment confirmation', attribute='confirmation_url', allow_null=True),
    'yookassaPaymentId': fields.String(description='Yookassa payment ID for online payments', allow_null=True),
    'displayStatus': fields.Boolean(required=True, description='Boolean flag to control if the order is displayed to the user')
})

# Model for updating order display status
order_display_status_update_model = api.model('OrderDisplayStatusUpdate', {
    'orderId': fields.String(required=True, description='ID of the order to update'),
    'displayStatus': fields.Boolean(required=True, description='New display status for the order (true to display, false to hide)')
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

# --- IIKO internal ----
MATCH_THRESHOLD = 90

def _get_iiko_essential_data(iiko_token: str, client_payment_method: str, client_street_name: str):
    """
    Helper to fetch essential IIKO dynamic data: organization, terminal group,
    selected payment type, and default city/street (first available, with fuzzy street matching).
    Raises an error if critical data cannot be fetched or street matching fails.
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
    iiko_payment_types = iiko_service.get_payment_types([organization_id], iiko_token)
    if not iiko_payment_types:
        current_app.logger.error(f"No payment types found for organization {organization_id} from IIKO API.")
        raise RuntimeError("Could not determine payment types for external order.")

    # Logic to select payment type (as per your OrderList.post)
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
            # For online payments, prefer 'Card' kind, but any could work if configured
            if pt_kind == "card" or pt_code == "bank":
                selected_iiko_payment_type = pt
                break
            # Fallback for generic online (if no 'Card' kind is explicitly found for online)
            selected_iiko_payment_type = pt # Take the first one if specific logic fails
            break

    if not selected_iiko_payment_type:
        current_app.logger.warning(f"Could not find a specific IIKO payment type for client method '{client_payment_method_lower}'. Using the first available payment type as fallback.")
        selected_iiko_payment_type = iiko_payment_types[0] # Fallback to first available

    current_app.logger.info(f"Using IIKO Payment Type: ID='{selected_iiko_payment_type.get('id')}', Name='{selected_iiko_payment_type.get('name')}', Kind='{selected_iiko_payment_type.get('paymentTypeKind')}', Code='{selected_iiko_payment_type.get('code')}'")

    # 4. Fetch City and Street with Fuzzy Matching
    cities_data = iiko_service.get_cities([organization_id])
    if cities_data:
        org_cities_list = next((org_data.get('items') for org_data in cities_data if org_data.get('organizationId') == organization_id), [])
        if org_cities_list:
            # --- Prioritize "Черноголовка" city ---
            found_chernogolovka = False
            for city in org_cities_list:
                if city.get('name') == "Черноголовка":
                    selected_city_id = city['id']
                    selected_city_name = city['name']
                    current_app.logger.info(f"Prioritizing IIKO City: ID={selected_city_id}, Name='{selected_city_name}' (explicitly 'Черноголовка')")
                    found_chernogolovka = True
                    break

            if not found_chernogolovka:
                # Fallback to original logic: use the first city if "Черноголовка" is not found
                selected_city_id = org_cities_list[0]['id']
                selected_city_name = org_cities_list[0]['name']
                current_app.logger.warning(
                    f"City 'Черноголовка' not found for organization {organization_id}. "
                    f"Falling back to first available city: ID={selected_city_id}, Name='{selected_city_name}'"
                )
            
            # The rest of the street matching logic now uses the determined selected_city_id/name
            streets_data = iiko_service.get_streets_by_city(organization_id, selected_city_id)
            if streets_data:
                # --- Fuzzy Matching Logic for Street with Name Variations ---
                
                # Generate client street name variations for matching
                client_name_lower = client_street_name.lower()
                client_name_variations = [client_name_lower]
                
                if " улица" in client_name_lower:
                    client_name_variations.append(client_name_lower.replace(" улица", ""))
                # Also check for "улица " at the beginning (e.g., "улица Ленина")
                if client_name_lower.startswith("улица "):
                    # Use replace with count=1 to only remove the first occurrence
                    client_name_variations.append(client_name_lower.replace("улица ", "", 1))
                
                # Use a dictionary to store the best match for each unique IIKO street.
                # This prevents a single IIKO street from being added multiple times
                # if different client_name_variations match it well.
                best_matches_for_iiko_street = {} 
                exact_match_found = None # Reset for street matching scope

                for street in streets_data:
                    iiko_street_name_lower = street['name'].lower()
                    best_score_for_current_iiko_street = 0

                    for client_var in client_name_variations:
                        score = fuzz.ratio(client_var, iiko_street_name_lower)
                        if score > best_score_for_current_iiko_street:
                            best_score_for_current_iiko_street = score
                            # If we find a 100% match for ANY variation, we can prioritize it
                            if score == 100:
                                exact_match_found = street
                                # Since we found a 100% match, no need to check other variations for this street
                                break 
                    
                    # If this IIKO street's best score (across all client variations) meets the threshold, store it.
                    # Only add if it's new or better than a previously found score for the same IIKO street.
                    if best_score_for_current_iiko_street >= MATCH_THRESHOLD:
                        current_entry = best_matches_for_iiko_street.get(street['id'])
                        if not current_entry or best_score_for_current_iiko_street > current_entry['score']:
                            best_matches_for_iiko_street[street['id']] = {
                                "score": best_score_for_current_iiko_street,
                                "street": street
                            }
                
                # Convert the dictionary values back to a list for consistent processing
                matched_streets = list(best_matches_for_iiko_street.values())

                # --- Prioritize Exact Street Match (overall best across all variations) ---
                if exact_match_found:
                    selected_street_id = exact_match_found['id']
                    selected_street_name = exact_match_found['name']
                    current_app.logger.info(
                        f"Exact IIKO street match found for '{client_street_name}' "
                        f"(checked variations: {', '.join(client_name_variations)}). "
                        f"Selected street: ID={selected_street_id}, Name='{selected_street_name}' (100% similarity)."
                    )
                    # No error raised, proceed to the final return statement
                else:
                    # --- Logic for no match or multiple non-exact matches ---
                    if not matched_streets:
                        current_app.logger.error(
                            f"No IIKO street matched '{client_street_name}' (tried variations: {', '.join(client_name_variations)}) "
                            f"with over {MATCH_THRESHOLD}% similarity for organization {organization_id}, city {selected_city_name}."
                        )
                        raise RuntimeError(
                            f"Could not match street '{client_street_name}' to any known IIKO streets (no match > {MATCH_THRESHOLD}%)."
                        )
                    elif len(matched_streets) > 1:
                        # Multiple non-exact matches found. Log the error and raise exception.
                        top_matches = sorted(matched_streets, key=lambda x: x['score'], reverse=True)[:3]

                        formatted_match_list = []
                        for m in top_matches:
                            formatted_match_list.append(f"{m['street']['name']} ({m['score']}%)")

                        top_matches_str = ", ".join(formatted_match_list)

                        log_message = (
                            f"Multiple IIKO streets matched '{client_street_name}' (tried variations: {', '.join(client_name_variations)}) "
                            f"with over {MATCH_THRESHOLD}% similarity for organization {organization_id}, city {selected_city_name}. "
                            f"Top matches: [{top_matches_str}]."
                        )

                        current_app.logger.error(log_message)
                        raise RuntimeError(f"Multiple highly similar street names found for '{client_street_name}'. Please provide a more precise address.")
                    else: # Exactly one non-exact match
                        best_match_street = matched_streets[0]['street']
                        selected_street_id = best_match_street['id']
                        selected_street_name = best_match_street['name']
                        current_app.logger.info(
                            f"Matched client street '{client_street_name}' to IIKO street: "
                            f"ID={selected_street_id}, Name='{selected_street_name}' (Score: {matched_streets[0]['score']}%) "
                            f"(matched using variations: {', '.join(client_name_variations)})"
                        )
            else:
                current_app.logger.error(f"No streets found for city '{selected_city_name}' from IIKO API. Cannot match street for order.")
                raise RuntimeError("No streets found for the selected city in IIKO. Cannot create order.")
        else:
            current_app.logger.error("No cities found for selected organization. Cannot determine address for order.")
            raise RuntimeError("No cities found for organization in IIKO. Cannot create order.")
    else:
        current_app.logger.error("No cities data returned from IIKO. Cannot determine address for order.")
        raise RuntimeError("No cities data returned from IIKO. Cannot create order.")

    return {
        "organization_id": organization_id,
        "terminal_group_id": terminal_group_id,
        "selected_iiko_payment_type": selected_iiko_payment_type,
        "selected_city_id": selected_city_id,
        "selected_city_name": selected_city_name,
        "selected_street_id": selected_street_id,
        "selected_street_name": selected_street_name
    }

def _send_order_to_iiko_internal(order: Order, iiko_token: str, client_payment_method: str, 
                                 client_street_name: str, nominatim_postcode: str, nominatim_house_number: str):
    """
    Constructs the IIKO payload and sends the order to IIKO.
    This function consolidates the common logic from OrderList.post and PaymentCallback.post.
    
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
                                 
    Returns:
        dict: The response from the IIKO /deliveries/create API.
        
    Raises:
        RuntimeError: If essential IIKO data cannot be fetched or if IIKO API call fails.
    """
    current_app.logger.info(f"Preparing to send order {order.id} to IIKO.")

    # Fetch dynamic IIKO data, now passing the client_street_name
    iiko_metadata = _get_iiko_essential_data(iiko_token, client_payment_method, client_street_name)
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
        # Fetch addons using the IDs stored in `selected_addons_ids`
        # Query Addon object
        for addon_id in item.selected_addons_ids:
            addon = Addon(addon_id, f"Addon {addon_id}", 10.0, f"iiko_addon_{addon_id}") # Dummy Addon
            # addon = Addon.query.get(addon_id)
            if addon:
                item_unit_price_for_iiko += Decimal(str(addon.price)) # Add addon price to unit price
                iiko_modifiers.append({
                    "productId": addon.iiko_addon_id, # This field is for IIKO's specific product ID for the addon
                    "type": "Product",
                    "amount": item.quantity, # Modifier amount should reflect the quantity of the parent item
                    "name": addon.name,
                    "price": float(addon.price) # Price of the modifier itself
                })
            else:
                current_app.logger.warning(f"Addon with ID {addon_id} not found for order item {item.id}.")

        # Fetch recommendations using the IDs stored in `selected_recommendation_ids`
        # Query Recommendation object
        for rec_id in item.selected_recommendation_ids:
            recommendation = Recommendation(rec_id, f"Rec {rec_id}", 5.0, f"iiko_rec_{rec_id}") # Dummy Rec
            # recommendation = Recommendation.query.get(rec_id)
            if recommendation and recommendation.price:
                item_unit_price_for_iiko += Decimal(str(recommendation.price)) # Add recommendation price to unit price
                iiko_modifiers.append({
                    "productId": recommendation.iiko_recommendation_id,
                    "type": "Product",
                    "amount": item.quantity, # Assuming recommendation amount reflects parent item quantity
                    "name": recommendation.name,
                    "price": float(recommendation.price)
                })
            else:
                current_app.logger.warning(f"Recommendation with ID {rec_id} not found for order item {item.id}.")

        iiko_order_items.append({
            "type": "Product",
            "productId": product_id_for_iiko,
            "productCode": product_id_for_iiko, # Often same as productId for simple products
            "name": product_name,
            "amount": item.quantity,
            "price": float(item_unit_price_for_iiko), # Unit price of the item including its selected modifiers
            "modifiers": iiko_modifiers,
            "comboId": None,
            "positionId": str(uuid.uuid4()) # Unique for each position in IIKO
        })

    # Add Delivery Product as an item
    delivery_product = Product.query.get(DELIVERY_100_PRODUCT_ID)
    if delivery_product:
        iiko_order_items.append({
            "type": "Product",
            "productId": delivery_product.iiko_product_id,
            "productCode": delivery_product.iiko_product_id,
            "name": delivery_product.name,
            "amount": 1,
            "price": float(delivery_product.price), # Using price from product table
            "modifiers": [],
            "comboId": None,
            "positionId": str(uuid.uuid4())
        })
    else:
        current_app.logger.warning(f"Delivery product with ID {DELIVERY_100_PRODUCT_ID} not found. Delivery item not added to IIKO payload.")


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


    iiko_order_data_for_payload = {
        "id": str(order.id), # Ensure UUID is string
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
                "house": iiko_house_final,   # UPDATED
                "building": iiko_building,   # UPDATED
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
        "comment": order.delivery_info.comment if not USING_MOCK else "ТЕСТОВЫЙ ЗАКАЗ. НЕ ОБРАБАТЫВАТЬ.",
        "completeBefore": (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
    }

    current_app.logger.info(f"Sending order {order.id} to IIKO with payload (excluding full items for brevity): "
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
        """Get all orders for a specific Telegram user and then hide them (set display_status=False)."""
        user_id = get_telegram_user_id() # MANDATORY HEADER

        # Retrieve orders for the given telegram_user_id and display_status=True
        # We fetch them first to serialize them before updating their display_status
        orders_to_display = Order.query.filter_by(user_id=user_id).options(
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.available_addons)
            .joinedload(ProductAddon.addon), 
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.recommendations)
            .joinedload(ProductRecommendation.recommendation), 
            joinedload(Order.delivery_info) 
        ).all()

        serialized_orders = []
        for order in orders_to_display: # Iterate through the fetched orders for serialization
            items_data = []
            for item in order.items:
                product_obj = item.product

                fetched_addons = []
                if item.selected_addons_ids:
                    addons_from_db = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                    fetched_addons = [api.marshal(addon, addon_model) for addon in addons_from_db]

                fetched_recommendations = []
                if item.selected_recommendation_ids:
                    recs_from_db = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
                    fetched_recommendations = [api.marshal(rec, recommendation_model) for rec in recs_from_db]

                product_marshaled = {
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
                marshaled_product_in_order_item = api.marshal(product_marshaled, product_model)

                items_data.append({
                    'product': marshaled_product_in_order_item,
                    'quantity': item.quantity,
                    'selectedAddons': fetched_addons,
                    'selectedRecommendations': fetched_recommendations
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
                    'longitude': delivery_info_obj.longitude
                }, delivery_info_model_new)


            serialized_orders.append({
                'id': str(order.id),
                'userId': order.user_id,
                'items': items_data,
                'total': float(order.total) if isinstance(order.total, Decimal) else order.total,
                'deliveryInfo': delivery_info_for_response, 
                'status': order.status,
                'createdAt': order.created_at.isoformat(),
                'estimatedDelivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                'displayStatus': order.display_status
            })
        
        # --- NEW LOGIC: Set display_status = False for all orders of this user ---
        try:
            # Update all orders for the current user to set display_status to False
            # We do this after retrieving them to ensure the current request returns the 'True' ones.
            # If you want it to return 'False' immediately, this update should happen before fetching.
            # However, typically, you'd show them and then hide them for subsequent fetches.
            Order.query.filter_by(user_id=user_id).update({"display_status": False})
            db.session.commit()
            current_app.logger.info(f"All orders for Telegram user {user_id} set to display_status=False after retrieval.")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error setting display_status=False for user {user_id} orders: {e}", exc_info=True)
            # You might choose to abort here or just log and continue, depending on criticality.
            # For now, we'll just log and return the fetched (old status) orders.

        return serialized_orders
    @api.expect(request_order_payload_model) # <-- Use the FLAT request model for input
    @api.marshal_with(order_model, code=201) # <-- Still marshal output with the NESTED order_model
    def post(self):
        """Create a new order and send it to IIKO."""
        user_id = get_telegram_user_id() # MANDATORY HEADER
        data = api.payload # This contains the flat delivery fields from the frontend

        # --- Validate delivery coordinates and get delivery cost ---
        load_delivery_areas() # Ensure areas are loaded
        global VALID_DELIVERY_AREAS, DELIVERY_COST_MOCK

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not latitude or not longitude:
            api.abort(400, "Latitude and Longitude are required for delivery.")

        # Get structured address from Nominatim
        nominatim_response = get_address_from_coordinates(latitude, longitude)
        if not nominatim_response:
            current_app.logger.error(f"Could not get address details from Nominatim for coordinates: {latitude}, {longitude}")
            api.abort(500, "Could not determine detailed address from provided coordinates.")
            
        # Extract the street name (Nominatim uses 'road')
        street_name_from_coords = nominatim_response.get('address', {}).get('road')
        # NEW: Extract house_number from Nominatim
        nominatim_house_number = nominatim_response.get('address', {}).get('house_number')

        if not street_name_from_coords:
            current_app.logger.error(f"No 'road' (street name) found in Nominatim response for {latitude}, {longitude}. Full response: {nominatim_response}")
            api.abort(400, "Could not extract street name from provided coordinates. Please ensure the location is valid.")

        # --- NEW: Extract postcode from Nominatim ---
        nominatim_postcode = nominatim_response.get('address', {}).get('postcode')
        
        current_app.logger.info(f"Nominatim details: Road='{street_name_from_coords}', HouseNumber='{nominatim_house_number}', Postcode='{nominatim_postcode}'")

        point = Point(longitude, latitude)
        is_in_delivery_area = False
        for area_polygon in VALID_DELIVERY_AREAS:
            if area_polygon.contains(point):
                is_in_delivery_area = True
                break

        if not is_in_delivery_area:
            api.abort(404, "The provided coordinates are outside our valid delivery areas.")

        delivery_cost = DELIVERY_COST_MOCK # Use the mock delivery cost

        # --- Retrieve items from the user's cart ---
        cart = get_or_create_cart(user_id) # Assuming get_or_create_cart is defined
        if not cart.items:
            api.abort(400, "Cart is empty. Please add items before creating an order.")

        # Eager load cart items and their related products/addons/recommendations
        cart_with_items = db.session.query(Cart).filter_by(user_id=user_id).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.selected_addons).joinedload(CartAddon.addon),
            joinedload(Cart.items).joinedload(CartItem.selected_recommendations).joinedload(CartRecommendation.recommendation)
        ).first()

        if not cart_with_items or not cart_with_items.items:
            api.abort(400, "Cart is empty or could not load cart items.")

        calculated_total = Decimal('0.00')
        order_items_to_add = [] # For DB persistence

        for cart_item in cart_with_items.items:
            item_price = Decimal('0.00')
            product = None

            if cart_item.product_id:
                product = cart_item.product # Already loaded by joinedload
                if not product:
                    current_app.logger.warning(f"Product with ID {cart_item.product_id} not found for cart item {cart_item.id}. Skipping.")
                    continue
                item_price += Decimal(str(product.price))
            elif cart_item.custom_wok_data:
                item_price += Decimal(str(cart_item.custom_price)) if cart_item.custom_price else Decimal('0.00')
            else:
                current_app.logger.warning(f"Cart item {cart_item.id} has no product or custom wok data. Skipping.")
                continue

            selected_addons_ids_for_order_item = []
            for cart_addon in cart_item.selected_addons:
                addon = cart_addon.addon # Already loaded by joinedload
                if addon:
                    item_price += Decimal(str(addon.price)) * cart_addon.quantity
                    selected_addons_ids_for_order_item.append(addon.id)
                else:
                    current_app.logger.warning(f"Selected addon with ID {cart_addon.addon_id} not found for cart item {cart_item.id}.")

            selected_recommendation_ids_for_order_item = []
            for cart_rec in cart_item.selected_recommendations:
                recommendation = cart_rec.recommendation # Already loaded by joinedload
                if recommendation:
                    item_price += Decimal(str(recommendation.price))
                    selected_recommendation_ids_for_order_item.append(recommendation.id)
                else:
                    current_app.logger.warning(f"Selected recommendation with ID {cart_rec.recommendation_id} not found for cart item {cart_item.id}.")

            calculated_total += item_price * Decimal(str(cart_item.quantity))

            order_items_to_add.append(OrderItem(
                product=product,
                quantity=cart_item.quantity,
                selected_addons_ids=selected_addons_ids_for_order_item,
                selected_recommendation_ids=selected_recommendation_ids_for_order_item
            ))

        # Add delivery cost to the total
        final_total = calculated_total + delivery_cost
        current_app.logger.info(f"Order calculated total (without delivery): {calculated_total}, with delivery: {final_total}")

        # Determine phone and comment based on mock setting
        phone = data['phone'] if not USING_MOCK else '+79999999999'
        comment = data.get('comment') if not USING_MOCK else "ТЕСТОВЫЙ ЗАКАЗ. НЕ ОБРАБАТЫВАТЬ."

        # Create DeliveryInfo object from the flat incoming data
        delivery_info_obj = DeliveryInfo(
            address=data['address'], # This address could be less precise than Nominatim's street name
            apartment=data.get('apartment'),
            floor=data.get('floor'),
            phone=phone,
            payment_method=data['paymentMethod'],
            comment=comment,
            latitude=data['latitude'],
            longitude=data['longitude'],
            postcode=nominatim_postcode, # NEW: Save Nominatim postcode to DB
            street_name=street_name_from_coords, # NEW: Save Nominatim street name to DB
            house_number=nominatim_house_number # NEW: Save Nominatim house number to DB
        )

        # Store new order in DB
        new_order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            total=final_total,
            status='pending',
            created_at=datetime.now(timezone.utc),
            display_status=True,
            delivery_info=delivery_info_obj
        )
        db.session.add(new_order)
        db.session.flush()

        for item in order_items_to_add:
            item.order_id = new_order.id
            db.session.add(item)

        try:
            if data['paymentMethod'].lower() == 'online':
                # --- ЮKassa Integration ---
                if not yookassa_service:
                    api.abort(500, "Сервис ЮKassa не настроен.")

                frontend_return_url = current_app.config.get('FRONTEND_ORDER_RETURN_URL', 'https://your-frontend-domain.com/order-status')

                payment_description = f"Заказ #{new_order.id} из {new_order.delivery_info.address}"
                yookassa_response = yookassa_service.create_payment(
                    amount=new_order.total,
                    description=payment_description,
                    order_id=new_order.id,
                    return_url=frontend_return_url
                )

                if yookassa_response and yookassa_response.get('confirmation', {}).get('confirmation_url'):
                    new_order.yookassa_payment_id = yookassa_response['id']
                    new_order.confirmation_url = yookassa_response['confirmation']['confirmation_url']
                    new_order.status = 'pending_payment'
                    current_app.logger.info(f"YuKassa payment initiated for order {new_order.id}. Confirmation URL: {new_order.confirmation_url}")
                else:
                    new_order.status = 'payment_initiation_failed'
                    current_app.logger.error(f"Failed to get confirmation_url from YuKassa for order {new_order.id}. Response: {yookassa_response}")
                    api.abort(500, "Failed to initiate card payment.")
                    
            else:
                # --- IIKO Integration for non-online payments ---
                order_to_send = db.session.query(Order).filter_by(id=new_order.id).options(
                    joinedload(Order.delivery_info),
                    joinedload(Order.items).joinedload(OrderItem.product)
                ).first()

                if not order_to_send:
                    current_app.logger.error(f"Failed to load new_order {new_order.id} for IIKO sending.")
                    api.abort(500, "Internal error: Could not load order for external system integration.")
                    
                iiko_token = iiko_service.get_iiko_token()
                if not iiko_token:
                    current_app.logger.error("Failed to get IIKO access token for order creation.")
                    api.abort(500, "Failed to connect to external ordering system (IIKO).")

                # Pass the extracted street name, postcode, and house_number for fuzzy matching and payload construction
                _send_order_to_iiko_internal(
                    order=order_to_send,
                    iiko_token=iiko_token,
                    client_payment_method=data['paymentMethod'], 
                    street_name=street_name_from_coords,
                    postcode=nominatim_postcode,
                    house_number=nominatim_house_number
                )
                new_order.status = 'sent_to_iiko'

            # Clear cart after successful order creation/payment initiation
            db.session.delete(cart_with_items)

        except RuntimeError as re: # Catch specific RuntimeErrors from IIKO integration
            db.session.rollback()
            current_app.logger.error(f"IIKO integration specific error for order {new_order.id}: {re}", exc_info=True)
            api.abort(500, f"Failed to integrate with IIKO: {str(re)}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"General error during payment processing/IIKO integration for order {new_order.id}: {e}", exc_info=True)
            api.abort(500, f"Order created internally, but payment or external integration failed: {str(e)}")

        db.session.commit()

        # Load the created order with all relations for marshalling
        created_order = db.session.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.delivery_info)
        ).get(new_order.id)

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
        
        # Original addon/recommendation data from frontend
        addons_data_from_frontend = data.get('addons', []) # [{'id': 'addon_id', 'quantity': 1}]
        recommendation_ids_from_frontend = data.get('recommendations', [])

        custom_wok_data = data.get('customWok')
        custom_name = data.get('customName')
        custom_description = data.get('customDescription')
        custom_price = data.get('customPrice')

        current_app.logger.debug(f"Received add to cart request: {data}")

        cart = get_or_create_cart(user_id)

        product = None
        # Handle the "wok-builder" special product ID
        if product_id == WOK_BUILDER_PRODUCT_ID:
            is_custom_item = True
            # For a custom Wok, the product_id for the CartItem should be WOK_PRODUCT_CONSTRUCTOR_ID,
            # as its details are in custom_wok_data.
            product_id = WOK_PRODUCT_CONSTRUCTOR_ID 

            # --- Convert customWok components into the 'addons_data' format ---
            converted_wok_addons = []
            
            if custom_wok_data:
                # Add Wok Base as an addon
                base_id = custom_wok_data.get('baseId')
                if base_id:
                    converted_wok_addons.append({'id': base_id, 'quantity': 1})

                # Add Wok Meats as addons
                for meat_id in custom_wok_data.get('meatIds', []):
                    converted_wok_addons.append({'id': meat_id, 'quantity': 1})

                # Add Wok Toppings as addons
                for topping_id in custom_wok_data.get('toppingIds', []):
                    converted_wok_addons.append({'id': topping_id, 'quantity': 1})

                # Add Wok Sauces as addons
                for sauce_id in custom_wok_data.get('sauceIds', []):
                    converted_wok_addons.append({'id': sauce_id, 'quantity': 1})
            
            # Combine frontend's addons with converted wok components
            addons_to_process = addons_data_from_frontend + converted_wok_addons
            recommendation_ids_to_process = recommendation_ids_from_frontend

        else:
            # It's a regular product
            product = Product.query.get(product_id)
            if not product:
                api.abort(404, "Product not found.")
            is_custom_item = False
            addons_to_process = addons_data_from_frontend
            recommendation_ids_to_process = recommendation_ids_from_frontend

        existing_item = None
        for item in cart.items:
            # Check for existing regular product item with same addons/recs
            if not is_custom_item and item.product_id == product_id:
                current_addons = sorted([{'id': ca.addon_id, 'quantity': ca.quantity} for ca in item.selected_addons], key=lambda x: x['id'])
                request_addons = sorted(addons_to_process, key=lambda x: x['id']) # Use processed addons
                addons_match = (current_addons == request_addons)

                current_recs = sorted([cr.recommendation_id for cr in item.selected_recommendations])
                request_recs = sorted(recommendation_ids_to_process) # Use processed recommendations
                recs_match = (current_recs == request_recs)

                if addons_match and recs_match and item.custom_wok_data is None:
                    existing_item = item
                    break
            # Check for existing custom Wok item with same custom_wok_data and other custom fields
            elif is_custom_item and item.custom_wok_data is not None:
                # Compare custom_wok_data directly
                if item.custom_wok_data == custom_wok_data:
                    # Also compare other custom fields for exact match for incrementing quantity
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
                # product_id is None for custom Wok items, otherwise the actual product ID
                product_id=product_id, 
                quantity=quantity_to_add,
                custom_wok_data=custom_wok_data if is_custom_item else None, # Store custom wok data only if it's a custom item
                custom_name=custom_name if is_custom_item else None,
                custom_description=custom_description if is_custom_item else None,
                custom_price=Decimal(str(custom_price)) if is_custom_item and custom_price is not None else None,
                custom_image=None if is_custom_item else (product.image if product else None)
            )
            db.session.add(new_cart_item)
            db.session.flush() # Flush to get new_cart_item.id

            # Process addons (now includes converted Wok components)
            for addon_data in addons_to_process:
                addon_obj = Addon.query.get(addon_data['id'])
                # Also check Wok component tables if addon_obj is not found directly in Addon
                # This depends on how you store IIKO IDs for Wok components.
                # Assuming WokBase, WokMeat, WokTopping, WokSauce models also have a relationship
                # to their respective Addon entry, or directly contain the addon's data.
                # For simplicity, if these IDs are truly `addon_ids`, querying Addon table is correct.
                
                # If your Wok component IDs are *not* directly `addon.id`s
                # then you'd need logic here like:
                # wok_component = None
                # if not addon_obj:
                #     wok_component = WokBase.query.get(addon_data['id']) or \
                #                     WokMeat.query.get(addon_data['id']) or \
                #                     WokTopping.query.get(addon_data['id']) or \
                #                     WokSauce.query.get(addon_data['id'])
                # if wok_component:
                #     # Create a dummy addon_obj or find a corresponding Addon
                #     addon_obj = Addon.query.filter_by(name=wok_component.name).first() # Or by some other IIKO ID mapping

                if addon_obj:
                    cart_addon = CartAddon(
                        cart_item_id=new_cart_item.id,
                        addon_id=addon_obj.id,
                        quantity=addon_data.get('quantity', 1)
                    )
                    db.session.add(cart_addon)
                else:
                    current_app.logger.warning(f"Addon/Wok component with ID {addon_data['id']} not found.")

            # Process recommendations
            for rec_id in recommendation_ids_to_process:
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
DELIVERY_COST_MOCK = 100

# IMPORTANT: User-Agent for Nominatim API
# Replace 'YourDeliveryApp/1.0 (your.email@example.com)' with your actual app name and email.
NOMINATIM_USER_AGENT = "MyDeliveryApp/1.0 (my.email@example.com)"

# Store loaded polygons globally
VALID_DELIVERY_AREAS = []

# --- MODIFIED get_address_from_coordinates function ---
def get_address_from_coordinates(latitude, longitude):
    """
    Retrieves the full Nominatim response for given latitude and longitude coordinates.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict or None: The full JSON response dictionary from Nominatim if successful,
                      otherwise None.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",        # Request a JSON response
        "lat": latitude,
        "lon": longitude,
        "zoom": 18,              # Adjust zoom level for more detailed address
        "addressdetails": 1      # IMPORTANT: Include detailed address breakdown
    }
    headers = {
        "User-Agent": NOMINATIM_USER_AGENT
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Return the entire data dictionary
        if data:
            return data
        else:
            print(f"Empty response from Nominatim for coordinates: {latitude}, {longitude}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Nominatim: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        try:
            print(f"Raw response content: {response.text}")
        except NameError: # response might not be defined if request failed before assignment
            print("No response content available.")
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
    @api.expect(map_query_parser) # Document input parameters
    @api.marshal_with(map_output_model) # Define an output model for successful responses
    def get(self):
        load_delivery_areas()
        global VALID_DELIVERY_AREAS, DELIVERY_COST_MOCK

        args = map_query_parser.parse_args(request)
        latitude = args['latitude']
        longitude = args['longitude']

        point = Point(longitude, latitude)

        if not VALID_DELIVERY_AREAS:
            api.abort(503, "Delivery areas not loaded. Please try again later.")

        is_in_delivery_area = False
        for area_polygon in VALID_DELIVERY_AREAS:
            if area_polygon.contains(point):
                is_in_delivery_area = True
                break

        if not is_in_delivery_area:
            # For a 404, we provide a message and no nominatim_details or cost
            return {
                "nominatim_details": None,
                "delivery_cost": None,
                "message": "Coordinates are outside our valid delivery areas."
            }, 404

        # Delay to respect Nominatim usage policy if this is part of a real system
        time.sleep(0.5) # Minimum recommended delay between requests

        # Call the function to get the full Nominatim response
        full_nominatim_response = get_address_from_coordinates(latitude, longitude)

        if full_nominatim_response:
            return {
                "nominatim_details": full_nominatim_response, # This will be marshaled by nominatim_response_model
                "delivery_cost": DELIVERY_COST_MOCK
            }, 200
        else:
            api.abort(500, "Coordinates are within a valid delivery area, but Nominatim lookup failed.")

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
                            order=order,
                            iiko_token=iiko_token,
                            client_payment_method='online', # For successful Yookassa payment, it's always online
                            street_name=order.delivery_info.street_name, # NEW: Pass street_name from DB
                            postcode=order.delivery_info.postcode,       # NEW: Pass postcode from DB
                            house_number=order.delivery_info.house_number # NEW: Pass house_number from DB
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
