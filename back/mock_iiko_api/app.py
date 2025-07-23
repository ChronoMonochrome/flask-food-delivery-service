from flask import Flask, request, jsonify
import json
from uuid import uuid4
from datetime import datetime, timedelta
import logging
import re # For UUID validation regex
import os # For environment variables

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Configuration for mock data
# Use environment variables for sensitive info, or define constants for mock
IIKO_API_TOKEN = os.getenv('IIKO_API_TOKEN', 'iiko_api_token')

# Stable UUIDs for consistent testing across runs
MOCK_ORGANIZATION_ID = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
MOCK_TERMINAL_GROUP_ID = "09876543-210f-edcb-a987-654321fedcba"

# Product IDs for specific items used in sync logic
MOCK_WOK_PRODUCT_CONSTRUCTOR_ID = "c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0"
MOCK_SAUCES_CATEGORY_ID = "s0s0s0s0-s0s0-s0s0-s0s0-s0s0s0s0s0s0" # Example ID for 'Sauces' category
MOCK_RECOMMENDATION_CATEGORY_ID = "r0r0r0r0-r0r0-r0r0-r0r0-r0r0r0r0r0r0"

# Helper function to validate UUIDs
def is_valid_uuid(uuid_string):
    if not isinstance(uuid_string, str):
        return False
    # Regex for UUID v4
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$', re.IGNORECASE)
    return bool(uuid_regex.match(uuid_string))


@app.route('/api/1/access_token', methods=['POST'])
def get_access_token_mock():
    """Mocks iiko /api/1/access_token endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Auth: Received access_token request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Validate basic request payload
    if not data or 'apiLogin' not in data:
        app.logger.error("Mock IIKO Auth: Missing 'apiLogin' in request payload.")
        return jsonify({"error": "Missing 'apiLogin'"}), 400

    api_login = data.get('apiLogin')

    # Simulate authentication success/failure
    # Generate a mock token that expires in 30 minutes
    expires_in_seconds = 1800 # 30 minutes
    mock_token = str(uuid4()) # A simple UUID can serve as a mock token

    response_data = {
        "token": mock_token,
        "expiresInSeconds": expires_in_seconds
    }
    app.logger.info(f"Mock IIKO Auth: Successfully issued access token for API login '{api_login}'.")
    return jsonify(response_data), 200

@app.route('/api/1/cities', methods=['POST'])
def get_cities():
    """Mocks iiko /api/1/cities endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Cities: Received get_cities request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    if not data or 'organizationIds' not in data or not isinstance(data['organizationIds'], list):
        app.logger.error("Mock IIKO Cities: Missing or invalid 'organizationIds' in payload.")
        return jsonify({"error": "Missing or invalid 'organizationIds' (expected a list)"}), 400

    requested_org_ids = data['organizationIds']
    response_cities = []
    
    for org_id in requested_org_ids:
        # if not is_valid_uuid(org_id):
            # app.logger.warning(f"Mock IIKO Cities: Invalid organizationId format: {org_id}. Skipping.")
            # continue # Or return an error for individual invalid IDs if needed

        organization = MOCK_ORGANIZATIONS.get(org_id)
        if organization:
            response_cities.extend(organization['cities'])
        else:
            app.logger.warning(f"Mock IIKO Cities: Organization ID not found: {org_id}")

    # Remove duplicates if an organization is requested multiple times, or if cities are shared
    unique_cities = []
    seen_city_ids = set()
    for city in response_cities:
        if city['id'] not in seen_city_ids:
            unique_cities.append(city)
            seen_city_ids.add(city['id'])

    app.logger.info(f"Mock IIKO Cities: Responding with {len(unique_cities)} cities.")
    return jsonify({"cities": unique_cities}), 200

@app.route('/api/1/streets/by_city', methods=['POST'])
def get_streets_by_city():
    """Mocks iiko /api/1/streets/by_city endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Streets: Received get_streets_by_city request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    required_fields = ['organizationId', 'cityId']
    for field in required_fields:
        if field not in data:
            app.logger.error(f"Mock IIKO Streets: Missing required field: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400

    organization_id = data.get('organizationId')
    city_id = data.get('cityId')

    # if not is_valid_uuid(organization_id):
        # app.logger.error(f"Mock IIKO Streets: Invalid organizationId format: {organization_id}")
        # return jsonify({"error": "Invalid organizationId format (expected UUID)"}), 400
    # iiko's cityId might not always be a strict UUID, but we can validate if we expect it to be.
    # For this mock, we'll allow it if it's a string, as per the original comment.
    if not isinstance(city_id, str) or not city_id:
        app.logger.error(f"Mock IIKO Streets: Invalid cityId format: {city_id}")
        return jsonify({"error": "Invalid cityId format (expected non-empty string)"}), 400

    streets = MOCK_STREETS.get(city_id, [])

    if not streets:
        app.logger.warning(f"Mock IIKO Streets: No streets found for city ID: {city_id}")

    app.logger.info(f"Mock IIKO Streets: Responding with {len(streets)} streets for city {city_id}.")
    return jsonify({"streets": streets}), 200


@app.route('/api/1/deliveries/create', methods=['POST'])
def create_delivery():
    """Mocks iiko /api/1/deliveries/create endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Delivery: Received create_delivery request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # --- Basic Payload Structure Checks ---
    required_top_level_fields = ['organizationId', 'terminalGroupId', 'order']
    for field in required_top_level_fields:
        if field not in data:
            app.logger.error(f"Mock IIKO Delivery: Missing required top-level field: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400

    organization_id = data.get('organizationId')
    terminal_group_id = data.get('terminalGroupId')
    order_payload = data.get('order')

    # Removed UUID validation for organizationId as requested
    if not isinstance(organization_id, str) or not organization_id:
        app.logger.error(f"Mock IIKO Delivery: Invalid organizationId format: {organization_id}. Expected non-empty string.")
        return jsonify({"error": "Invalid organizationId format (expected non-empty string)"}), 400
    
    if terminal_group_id is not None and not isinstance(terminal_group_id, str):
        app.logger.error(f"Mock IIKO Delivery: Invalid terminalGroupId format: {terminal_group_id}")
        return jsonify({"error": "Invalid terminalGroupId format (expected string or null)"}), 400

    # --- Order Object Checks ---
    if not isinstance(order_payload, dict):
        app.logger.error("Mock IIKO Delivery: 'order' field must be an object.")
        return jsonify({"error": "'order' field must be an object"}), 400

    required_order_fields = ['id', 'phone', 'items', 'deliveryPoint', 'payments']
    for field in required_order_fields:
        if field not in order_payload:
            app.logger.error(f"Mock IIKO Delivery: Missing required 'order' field: {field}")
            return jsonify({"error": f"Missing required 'order' field: {field}"}), 400

    order_id = order_payload.get('id')
    external_number = order_payload.get('externalNumber') 
    phone = order_payload.get('phone')
    items = order_payload.get('items')
    delivery_point = order_payload.get('deliveryPoint')
    payments = order_payload.get('payments')
    complete_before = order_payload.get('completeBefore')
    order_service_type = order_payload.get('orderServiceType')
    customer = order_payload.get('customer')

    # Removed UUID validation for order.id as requested
    if not isinstance(order_id, str) or not order_id:
        app.logger.error(f"Mock IIKO Delivery: Invalid order.id format: {order_id}. Expected non-empty string.")
        return jsonify({"error": "Invalid order.id format (expected non-empty string)"}), 400
    if external_number is not None and (not isinstance(external_number, str) or not external_number):
            app.logger.error(f"Mock IIKO Delivery: Invalid order.externalNumber: {external_number}")
            return jsonify({"error": "Invalid order.externalNumber (expected non-empty string or null)"}), 400

    # Validate Phone Number
    if not isinstance(phone, str) or not (8 <= len(phone) <= 40) or not phone.startswith('+'):
        app.logger.error(f"Mock IIKO Delivery: Invalid order.phone format: {phone}")
        return jsonify({"error": "Invalid order.phone (must start with '+' and be 8-40 chars)"}), 400

    # Validate deliveryPoint
    if not isinstance(delivery_point, dict):
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint' must be an object.")
        return jsonify({"error": "'order.deliveryPoint' must be an object"}), 400

    # More detailed deliveryPoint.address validation
    if 'address' not in delivery_point or not isinstance(delivery_point['address'], dict):
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address' is missing or invalid.")
        return jsonify({"error": "'order.deliveryPoint.address' is missing or invalid"}), 400

    address = delivery_point['address']

    # Validate 'street' as an object with 'id' and 'name'
    if 'street' not in address or not isinstance(address['street'], dict):
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address.street' is missing or not an object.")
        return jsonify({"error": "'order.deliveryPoint.address.street' is missing or not an object"}), 400
    
    street_obj = address['street']
    # Removed UUID validation for street.id as requested
    if 'id' not in street_obj or not isinstance(street_obj['id'], str) or not street_obj['id']:
        app.logger.error(f"Mock IIKO Delivery: Invalid 'order.deliveryPoint.address.street.id' format: {street_obj.get('id')}. Expected non-empty string.")
        return jsonify({"error": "Invalid 'order.deliveryPoint.address.street.id' (expected non-empty string)"}), 400
    if 'name' not in street_obj or not isinstance(street_obj['name'], str) or not street_obj['name']:
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address.street.name' is missing, invalid, or empty.")
        return jsonify({"error": "'order.deliveryPoint.address.street.name' is missing, invalid, or empty"}), 400

    # Validate 'city' as an object with 'id' and 'name' (if present)
    if 'city' in address:
        if not isinstance(address['city'], dict):
            app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address.city' must be an object.")
            return jsonify({"error": "'order.deliveryPoint.address.city' must be an object"}), 400
        city_obj = address['city']
        # Removed UUID validation for city.id as requested
        if 'id' not in city_obj or not isinstance(city_obj['id'], str) or not city_obj['id']:
            app.logger.error(f"Mock IIKO Delivery: Invalid 'order.deliveryPoint.address.city.id' format: {city_obj.get('id')}. Expected non-empty string.")
            return jsonify({"error": "Invalid 'order.deliveryPoint.address.city.id' (expected non-empty string)"}), 400
        if 'name' not in city_obj or not isinstance(city_obj['name'], str) or not city_obj['name']:
            app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address.city.name' is missing, invalid, or empty.")
            return jsonify({"error": "'order.deliveryPoint.address.city.name' is missing, invalid, or empty"}), 400

    # Required simple string address fields
    required_simple_address_fields = ['house'] 
    for field in required_simple_address_fields:
        if field not in address or not isinstance(address[field], str) or not address[field]:
            app.logger.error(f"Mock IIKO Delivery: 'order.deliveryPoint.address.{field}' is missing, invalid, or empty.")
            return jsonify({"error": f"'order.deliveryPoint.address.{field}' is missing, invalid, or empty"}), 400

    # Validate optional string fields in address (if present, must be string)
    optional_string_address_fields = ['building', 'flat', 'entrance', 'floor', 'doorphone', 'comment', 'index', 'line1']
    for field in optional_string_address_fields:
        if field in address and not isinstance(address[field], str):
            app.logger.error(f"Mock IIKO Delivery: Invalid type for 'order.deliveryPoint.address.{field}' (expected string).")
            return jsonify({"error": f"Invalid type for 'order.deliveryPoint.address.{field}' (expected string)."}), 400


    if 'coordinates' in delivery_point and (not isinstance(delivery_point['coordinates'], dict) or 'latitude' not in delivery_point['coordinates'] or 'longitude' not in delivery_point['coordinates']):
        app.logger.warning("Mock IIKO Delivery: 'order.deliveryPoint.coordinates' is present but malformed.")
    
    # Validate completeBefore date format (optional but good to check if present)
    if complete_before:
        try:
            # Example format: 2025-07-09 01:03:14.051
            datetime.strptime(complete_before, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            app.logger.error(f"Mock IIKO Delivery: Invalid order.completeBefore format: {complete_before}. Expected YYYY-MM-DD HH:MM:SS.FFF")
            return jsonify({"error": "Invalid order.completeBefore format"}), 400

    # Validate orderServiceType
    allowed_service_types = ["DeliveryByCourier", "DeliveryByClient", "Common"]
    if order_service_type and order_service_type not in allowed_service_types:
        app.logger.error(f"Mock IIKO Delivery: Invalid order.orderServiceType: {order_service_type}. Allowed: {allowed_service_types}")
        return jsonify({"error": f"Invalid order.orderServiceType: {order_service_type}"}), 400

    # Validate Customer (new field)
    if customer:
        if not isinstance(customer, dict):
            app.logger.error("Mock IIKO Delivery: 'order.customer' must be an object if present.")
            return jsonify({"error": "'order.customer' must be an object"}), 400
        # Basic customer fields check
        # Removed UUID validation for customer.id as requested
        if 'id' in customer and (not isinstance(customer['id'], str) or not customer['id']):
            app.logger.error(f"Mock IIKO Delivery: Invalid order.customer.id format: {customer.get('id')}. Expected non-empty string.")
            return jsonify({"error": "Invalid order.customer.id format (expected non-empty string)"}), 400
        if 'name' in customer and not isinstance(customer['name'], str):
            app.logger.error("Mock IIKO Delivery: 'order.customer.name' must be a string.")
            return jsonify({"error": "'order.customer.name' must be a string"}), 400
        if 'phone' in customer and (not isinstance(customer['phone'], str) or not (8 <= len(customer['phone']) <= 40) or not customer['phone'].startswith('+')):
            app.logger.error(f"Mock IIKO Delivery: Invalid order.customer.phone format: {customer['phone']}")
            return jsonify({"error": "Invalid order.customer.phone (must start with '+' and be 8-40 chars)"}), 400


    # --- Items Checks ---
    if not isinstance(items, list) or not items:
        app.logger.error("Mock IIKO Delivery: 'order.items' must be a non-empty list.")
        return jsonify({"error": "'order.items' must be a non-empty list"}), 400

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            app.logger.error(f"Mock IIKO Delivery: Item at index {idx} is not an object.")
            return jsonify({"error": f"Item at index {idx} is not an object"}), 400
        
        required_item_fields = ['productId', 'amount', 'positionId']
        for field in required_item_fields:
            if field not in item:
                app.logger.error(f"Mock IIKO Delivery: Missing required item field '{field}' at index {idx}.")
                return jsonify({"error": f"Missing required item field '{field}' at index {idx}"}), 400
        
        # Removed UUID validation for productId and positionId as requested
        if not isinstance(item.get('productId'), str) or not item.get('productId'):
            app.logger.error(f"Mock IIKO Delivery: Invalid productId format for item at index {idx}. Expected non-empty string.")
            return jsonify({"error": f"Invalid productId format for item at index {idx} (expected non-empty string)"}), 400
        if not isinstance(item.get('amount'), (int, float)) or item.get('amount') <= 0:
            app.logger.error(f"Mock IIKO Delivery: Invalid amount for item at index {idx}.")
            return jsonify({"error": f"Invalid amount for item at index {idx}"}), 400
        if not isinstance(item.get('positionId'), str) or not item.get('positionId'):
            app.logger.error(f"Mock IIKO Delivery: Invalid positionId format for item at index {idx}. Expected non-empty string.")
            return jsonify({"error": f"Invalid positionId format for item at index {idx} (expected non-empty string)"}), 400

        # Validate optional string fields in item
        optional_item_strings = ['type', 'productCode', 'name', 'comboId']
        for field in optional_item_strings:
            if field in item and not (isinstance(item[field], str) or item[field] is None): # Allow None for comboId
                app.logger.error(f"Mock IIKO Delivery: Invalid type for item field '{field}' at index {idx} (expected string or null).")
                return jsonify({"error": f"Invalid type for item field '{field}' at index {idx} (expected string or null)."}), 400
        
        # Validate optional price field in item
        if 'price' in item and not isinstance(item['price'], (int, float)):
            app.logger.error(f"Mock IIKO Delivery: Invalid type for item field 'price' at index {idx} (expected number).")
            return jsonify({"error": f"Invalid type for item field 'price' at index {idx} (expected number)."}), 400


        # Modifiers check
        if 'modifiers' in item:
            if not isinstance(item['modifiers'], list):
                app.logger.error(f"Mock IIKO Delivery: Modifiers for item at index {idx} must be a list.")
                return jsonify({"error": f"Modifiers for item at index {idx} must be a list"}), 400
            for mod_idx, modifier in enumerate(item['modifiers']):
                if not isinstance(modifier, dict):
                    app.logger.error(f"Mock IIKO Delivery: Modifier at index {mod_idx} for item {idx} is not an object.")
                    return jsonify({"error": f"Modifier at index {mod_idx} for item {idx} is not an object"}), 400

                required_modifier_fields = ['productId', 'type', 'amount']
                for field in required_modifier_fields:
                    if field not in modifier:
                        app.logger.error(f"Mock IIKO Delivery: Missing required modifier field '{field}' at index {mod_idx} for item {idx}.")
                        return jsonify({"error": f"Missing required modifier field '{field}' at index {mod_idx} for item {idx}"}), 400

                # Removed UUID validation for modifier.productId as requested
                if not isinstance(modifier.get('productId'), str) or not modifier.get('productId'):
                    app.logger.error(f"Mock IIKO Delivery: Invalid modifier productId format at index {mod_idx} for item {idx}. Expected non-empty string.")
                    return jsonify({"error": f"Invalid modifier productId format at index {mod_idx} for item {idx} (expected non-empty string)"}), 400
                
                allowed_modifier_types = ["Product", "Compound"]
                if modifier.get('type') not in allowed_modifier_types:
                    app.logger.warning(f"Mock IIKO Delivery: Unexpected modifier type '{modifier.get('type')}' at index {mod_idx} for item {idx}. Allowed: {allowed_modifier_types}")
                if not isinstance(modifier.get('amount'), (int, float)) or modifier.get('amount') <= 0:
                    app.logger.error(f"Mock IIKO Delivery: Invalid amount for modifier at index {mod_idx} for item {idx}.")
                    return jsonify({"error": f"Invalid amount for modifier at index {mod_idx} for item {idx}"}), 400
                
                # Optional modifier fields (name, price)
                if 'name' in modifier and not isinstance(modifier['name'], str):
                    app.logger.error(f"Mock IIKO Delivery: Invalid type for modifier field 'name' at index {mod_idx} for item {idx} (expected string).")
                    return jsonify({"error": f"Invalid type for modifier field 'name' at index {mod_idx} for item {idx} (expected string)."}), 400
                if 'price' in modifier and not isinstance(modifier['price'], (int, float)):
                    app.logger.error(f"Mock IIKO Delivery: Invalid type for modifier field 'price' at index {mod_idx} for item {idx} (expected number).")
                    return jsonify({"error": f"Invalid type for modifier field 'price' at index {mod_idx} for item {idx} (expected number)."}), 400


    # --- Payments Checks ---
    if not isinstance(payments, list) or not payments:
        app.logger.error("Mock IIKO Delivery: 'order.payments' must be a non-empty list.")
        return jsonify({"error": "'order.payments' must be a non-empty list"}), 400

    for idx, payment in enumerate(payments):
        if not isinstance(payment, dict):
            app.logger.error(f"Mock IIKO Delivery: Payment at index {idx} is not an object.")
            return jsonify({"error": f"Payment at index {idx} is not an object"}), 400
        required_payment_fields = ['sum', 'paymentTypeKind', 'paymentTypeId']
        for field in required_payment_fields:
            if field not in payment:
                app.logger.error(f"Mock IIKO Delivery: Missing required payment field '{field}' at index {idx}.")
                return jsonify({"error": f"Missing required payment field '{field}' at index {idx}"}), 400
        if not isinstance(payment.get('sum'), (int, float)) or payment.get('sum') < 0:
            app.logger.error(f"Mock IIKO Delivery: Invalid sum for payment at index {idx}.")
            return jsonify({"error": f"Invalid sum for payment at index {idx}"}), 400
        allowed_payment_kinds = ["Cash", "Card", "LoyaltyCard", "Credit", "Writeoff", "Voucher", "External", "SmartSale", "Sberbank", "Trpos", "Unknown"]
        if payment.get('paymentTypeKind') not in allowed_payment_kinds:
            app.logger.error(f"Mock IIKO Delivery: Invalid paymentTypeKind '{payment.get('paymentTypeKind')}' at index {idx}. Allowed: {allowed_payment_kinds}")
            return jsonify({"error": f"Invalid paymentTypeKind at index {idx}"}), 400

        # paymentTypeId is now only checked for being a non-empty string.
        if not isinstance(payment.get('paymentTypeId'), str) or not payment.get('paymentTypeId'):
            app.logger.error(f"Mock IIKO Delivery: Invalid paymentTypeId format for payment at index {idx}. Expected non-empty string.")
            return jsonify({"error": f"Invalid paymentTypeId format for payment at index {idx} (expected non-empty string)"}), 400
            
        # Check optional boolean fields if they are present and not bool
        for bool_field in ['isProcessedExternally', 'isFiscalizedExternally', 'isPrepay']:
            if bool_field in payment and not isinstance(payment.get(bool_field), bool):
                app.logger.error(f"Mock IIKO Delivery: Invalid type for '{bool_field}' for payment at index {idx} (expected boolean).")
                return jsonify({"error": f"Invalid type for '{bool_field}' for payment at index {idx} (expected boolean)."}), 400

    # Add validation for 'createOrderSettings' if present
    create_order_settings = data.get('createOrderSettings')
    if create_order_settings:
        if not isinstance(create_order_settings, dict):
            app.logger.error("Mock IIKO Delivery: 'createOrderSettings' must be an object if present.")
            return jsonify({"error": "'createOrderSettings' must be an object"}), 400
        if 'transportToFrontTimeout' in create_order_settings and not isinstance(create_order_settings['transportToFrontTimeout'], (int, float)):
            app.logger.error("Mock IIKO Delivery: Invalid type for 'createOrderSettings.transportToFrontTimeout' (expected number).")
            return jsonify({"error": "Invalid type for 'createOrderSettings.transportToFrontTimeout' (expected number)."}), 400


    # If all checks pass, generate a successful response matching the real IIKO structure
    mock_order_id = str(uuid4()) # Still generate a valid UUID for the mock response
    mock_correlation_id = str(uuid4()) # Still generate a valid UUID for the mock response
    response_data = {
        "correlationId": mock_correlation_id,
        "orderInfo": {
            "id": mock_order_id,
            "posId": str(uuid4()), # Generate a mock posId as well
            "externalNumber": f"WEB-{mock_order_id}",
            "organizationId": organization_id, # Use the organizationId from the request
            "timestamp": int(datetime.now().timestamp() * 1000),
            "creationStatus": "InProgress", # Match the status from the real response
            "errorInfo": None,
            "order": None # This was null in the real response you provided
        }
    }
    app.logger.info(f"Mock IIKO Delivery: Successfully created mock delivery order with ID: {mock_order_id}, Correlation ID: {mock_correlation_id}")
    return jsonify(response_data), 200

@app.route('/api/1/organizations', methods=['POST'])
def get_organizations_mock():
    """Mocks iiko /api/1/organizations endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Organizations: Received request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Validate Authorization header
    auth_header = headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.error("Mock IIKO Organizations: Missing or malformed Authorization header.")
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(' ')[1]
    # In a real mock, you might check if the token is valid and not expired.
    # For simplicity here, we'll assume any token from our /access_token endpoint is valid.

    # Basic validation of the request payload (though often empty for this endpoint)
    if not data or 'returnAdditionalInfo' not in data:
        app.logger.warning("Mock IIKO Organizations: 'returnAdditionalInfo' missing, defaulting to false.")

    mock_organizations = [
        {
            "id": MOCK_ORGANIZATION_ID,
            "name": "Mock Main Restaurant",
            "country": "Germany",
            "phone": "+49123456789",
            "address": "Mock Street 123, 10115 Berlin",
            "timezone": "Europe/Berlin",
            "cultureInfo": "de-DE",
            "currencyIsoCode": "EUR",
            "isMain": True,
            "latitude": 52.5200,
            "longitude": 13.4050
        },
        {
            "id": str(uuid4()),
            "name": "Mock Secondary Branch",
            "country": "Germany",
            "phone": "+49987654321",
            "address": "Another Mock Str. 45, 20354 Hamburg",
            "timezone": "Europe/Berlin",
            "cultureInfo": "de-DE",
            "currencyIsoCode": "EUR",
            "isMain": False
        }
    ]

    response_data = {
        "correlationId": str(uuid4()),
        "organizations": mock_organizations
    }
    app.logger.info(f"Mock IIKO Organizations: Responding with {len(mock_organizations)} organizations.")
    return jsonify(response_data), 200

@app.route('/api/1/terminal_groups', methods=['POST'])
def get_terminal_groups_mock():
    """Mocks iiko /api/1/terminal_groups endpoint.
    Modified to return data in a nested 'items' structure as expected by the client's current parsing logic.
    """
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Terminal Groups: Received request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    auth_header = headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.error("Mock IIKO Terminal Groups: Missing or malformed Authorization header.")
        return jsonify({"error": "Unauthorized"}), 401

    # Always return these mock terminal groups, regardless of the organizationIds in the request
    # Adjusted to match the `terminal_groups[0]["items"][0].get("id")` expectation.
    mock_terminal_groups_data = [
        {
            "organizationId": MOCK_ORGANIZATION_ID,
            "name": "Main Mock Organization Terminal Groups",
            "items": [ # This is the "items" list your flask_app is looking for!
                {
                    "id": MOCK_TERMINAL_GROUP_ID,
                    "organizationId": MOCK_ORGANIZATION_ID,
                    "name": "Main Kitchen Terminal",
                    "address": "Mock Street 123",
                    "timeZone": "Europe/Berlin",
                    "externalData": []
                },
                {
                    "id": str(uuid4()), # A different, random ID for another terminal group
                    "organizationId": MOCK_ORGANIZATION_ID,
                    "name": "Delivery Terminal",
                    "address": "Mock Street 123",
                    "timeZone": "Europe/Berlin",
                    "externalData": []
                }
            ]
        }
        # You could add more organization-specific terminal group data here if needed,
        # each with its own 'organizationId' and 'items' array.
    ]

    response_data = {
        "correlationId": str(uuid4()),
        "terminalGroups": mock_terminal_groups_data
    }
    app.logger.info(f"Mock IIKO Terminal Groups: Responding with {len(mock_terminal_groups_data)} top-level terminal group entries.")
    return jsonify(response_data), 200

@app.route('/api/1/payment_types', methods=['POST'])
def get_payment_types_mock():
    """Mocks iiko /api/1/payment_types endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Payment Types: Received request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Basic validation of the request payload
    if not data or 'organizationIds' not in data or not isinstance(data['organizationIds'], list):
        app.logger.error("Mock IIKO Payment Types: Missing or invalid 'organizationIds' in request payload.")
        return jsonify({"error": "Missing or invalid 'organizationIds'"}), 400

    # --- Sample Mock Payment Types ---
    # These UUIDs should be stable for your mock testing
    mock_cash_payment_id = "5a7e6c9b-d8f0-4a1b-8c7e-1e9d2f0a3b4c" # Example UUID for Cash
    mock_card_payment_id = "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e" # Example UUID for Card

    # Customize these mock payment types as needed
    mock_payment_types = []
    if data['organizationIds'] and data['organizationIds'][0] == MOCK_ORGANIZATION_ID:
        mock_payment_types = [
            {
                "id": mock_cash_payment_id,
                "code": "CASH",
                "name": "Наличные",
                "comment": "Оплата наличными курьеру",
                "combinable": True,
                "externalRevision": 1,
                "applicableMarketingCampaigns": [],
                "isDeleted": False,
                "printCheque": True,
                "paymentProcessingType": "Cash",
                "paymentTypeKind": "Cash",
                "terminalGroups": [
                    {
                        "id": MOCK_TERMINAL_GROUP_ID, # Use stable TG ID
                        "organizationId": MOCK_ORGANIZATION_ID,
                        "name": "Основная Касса",
                        "address": "ул. Тестовая, 1",
                        "timeZone": "Europe/Moscow",
                        "externalData": []
                    }
                ]
            },
            {
                "id": mock_card_payment_id,
                "code": "CARD",
                "name": "Карта",
                "comment": "Оплата картой при получении",
                "combinable": True,
                "externalRevision": 1,
                "applicableMarketingCampaigns": [],
                "isDeleted": False,
                "printCheque": True,
                "paymentProcessingType": "External",
                "paymentTypeKind": "Card",
                "terminalGroups": [
                    {
                        "id": MOCK_TERMINAL_GROUP_ID, # Use stable TG ID
                        "organizationId": MOCK_ORGANIZATION_ID,
                        "name": "Основная Касса",
                        "address": "ул. Тестовая, 1",
                        "timeZone": "Europe/Moscow",
                        "externalData": []
                    }
                ]
            }
            # Add more mock payment types as needed
        ]

    response_data = {
        "correlationId": str(uuid4()),
        "paymentTypes": mock_payment_types
    }
    app.logger.info(f"Mock IIKO Payment Types: Responding with {len(mock_payment_types)} payment types.")
    return jsonify(response_data), 200

@app.route('/api/2/menu', methods=['POST'])
def get_menu_mock():
    """Mocks iiko /api/2/menu endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Menu: Received request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    auth_header = headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.error("Mock IIKO Menu: Missing or malformed Authorization header.")
        return jsonify({"error": "Unauthorized"}), 401

    if not data or 'organizationId' not in data:# or not is_valid_uuid(data['organizationId']):
        app.logger.error("Mock IIKO Menu: Missing or invalid 'organizationId' in request payload.")
        return jsonify({"error": "Missing or invalid 'organizationId'"}), 400

    organization_id = data['organizationId']

    if organization_id != MOCK_ORGANIZATION_ID:
        app.logger.warning(f"Mock IIKO Menu: Request for unknown organizationId: {organization_id}. Returning empty menu.")
        return jsonify({
            "correlationId": str(uuid4()),
            "itemCategories": [],
            "items": [],
            "modifierGroups": [],
            "outOfStock": []
        }), 200

    # --- Sample Mock Menu Data ---
    # This data structure must align with what your _fetch_and_prepare_iiko_data expects.
    # Specifically, itemCategories, items (standalone), and modifierGroups.

    # Example Item IDs (use stable UUIDs for predictable testing)
    mock_burger_id = "b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1"
    mock_fries_id = "f2f2f2f2-f2f2-f2f2-f2f2-f2f2f2f2f2f2"
    mock_coke_id = "c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3"
    mock_wok_base_id = MOCK_WOK_PRODUCT_CONSTRUCTOR_ID # Wok Constructor Product ID
    mock_wok_chicken_id = "w4w4w4w4-w4w4-w4w4-w4w4-w4w4w4w4w4w4" # Wok Addon
    mock_wok_veg_id = "v5v5v5v5-v5v5-v5v5-v5v5-v5v5v5v5v5v5" # Wok Addon

    # Sauces (as items within a category or standalone modifiers)
    mock_ketchup_sauce_id = "s6s6s6s6-s6s6-s6s6-s6s6-s6s6s6s6s6s6"
    mock_mayo_sauce_id = "s7s7s7s7-s7s7-s7s7-s7s7-s7s7s7s7s7s7"

    # Recommendation Product (needs to be an 'item' within the recommendation category)
    mock_recommended_dessert_id = "d8d8d8d8-d8d8-d8d8-d8d8-d8d8d8d8d8d8"

    # Modifier Group IDs
    mock_burger_addons_group_id = "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1"
    mock_wok_base_addons_group_id = "m2m2m2m2-m2m2-m2m2-m2m2-m2m2m2m2m2m2"

    mock_menu_data = {
        "correlationId": str(uuid4()),
        "timestamp": int(datetime.now().timestamp() * 1000),
        "itemCategories": [
            {
                "id": "cat1-burgers-id",
                "name": "Burgers",
                "description": "Delicious gourmet burgers",
                "buttonImageUrl": "https://example.com/images/burgers_cat.jpg",
                "headerImageUrl": "https://example.com/images/burgers_header.jpg",
                "isHidden": False,
                "order": 1,
                "items": [
                    {
                        "itemId": mock_burger_id,
                        "code": "B001",
                        "name": "Classic Cheeseburger",
                        "description": "Juicy beef patty, cheddar, lettuce, tomato, pickles.",
                        "type": "DISH",
                        "measureUnit": "pc",
                        "order": 1,
                        "modifierGroups": [ # Modifiers directly linked to this product
                            {
                                "id": mock_burger_addons_group_id,
                                "name": "Burger Addons",
                                "minAmount": 0,
                                "maxAmount": 2,
                                "childModifiers": [
                                    {
                                        "id": "bun-type-mod-group-id",
                                        "name": "Bun Type",
                                        "minAmount": 1,
                                        "maxAmount": 1,
                                        "childModifiers": [
                                            {
                                                "id": str(uuid4()),
                                                "type": "Product",
                                                "name": "Brioche Bun",
                                                "defaultAmount": 1,
                                                "price": 0.00
                                            },
                                            {
                                                "id": str(uuid4()),
                                                "type": "Product",
                                                "name": "Sesame Seed Bun",
                                                "defaultAmount": 0,
                                                "price": 0.00
                                            }
                                        ]
                                    },
                                    {
                                        "id": str(uuid4()), # extra cheese modifier
                                        "type": "Product",
                                        "name": "Extra Cheese",
                                        "defaultAmount": 0,
                                        "price": 1.50
                                    }
                                ]
                            }
                        ],
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Standard",
                                "prices": [{"price": 12.99, "organizationId": organization_id}],
                                "nutritionPerHundredGrams": {
                                    "energy": 250.5,
                                    "carbs": 25.0,
                                    "fats": 15.0,
                                    "proteins": 10.0
                                }
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/cheeseburger.jpg"}],
                        "picture": "https://example.com/images/cheeseburger_fallback.jpg",
                        "allergens": [{"id": str(uuid4()), "name": "Gluten"}, {"id": str(uuid4()), "name": "Dairy"}],
                        "tags": ["Popular", "New"],
                        "labels": ["Best Seller"]
                    }
                ]
            },
            {
                "id": "cat2-sides-id",
                "name": "Sides",
                "description": "Tasty additions to your meal",
                "buttonImageUrl": "https://example.com/images/sides_cat.jpg",
                "isHidden": False,
                "order": 2,
                "items": [
                    {
                        "itemId": mock_fries_id,
                        "code": "F001",
                        "name": "French Fries",
                        "description": "Crispy golden fries.",
                        "type": "DISH",
                        "measureUnit": "g",
                        "order": 1,
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Regular",
                                "prices": [{"price": 3.50, "organizationId": organization_id}],
                                "nutritionPerHundredGrams": {
                                    "energy": 150.0,
                                    "carbs": 20.0,
                                    "fats": 7.0,
                                    "proteins": 2.0
                                }
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/fries.jpg"}]
                    },
                    {
                        "itemId": mock_coke_id,
                        "code": "D001",
                        "name": "Coca-Cola (0.33L)",
                        "description": "Refreshing soft drink.",
                        "type": "GOODS", # Example of GOODS type
                        "measureUnit": "ml",
                        "order": 2,
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Can",
                                "prices": [{"price": 2.00, "organizationId": organization_id}],
                                "nutritionPerHundredGrams": {
                                    "energy": 42.0,
                                    "carbs": 10.6,
                                    "fats": 0.0,
                                    "proteins": 0.0
                                }
                            }
                        ],
                        "picture": "https://example.com/images/coke.jpg"
                    }
                ]
            },
            {
                "id": MOCK_SAUCES_CATEGORY_ID, # Sauces category ID
                "name": "Sauces",
                "description": "Add a flavor kick!",
                "buttonImageUrl": "https://example.com/images/sauces_cat.jpg",
                "isHidden": False,
                "order": 3,
                "items": [
                    {
                        "itemId": mock_ketchup_sauce_id,
                        "code": "S001",
                        "name": "Ketchup",
                        "description": "Classic tomato ketchup.",
                        "type": "DISH", # Could also be MODIFIER depending on iiko setup
                        "measureUnit": "g",
                        "order": 1,
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Standard",
                                "prices": [{"price": 0.50, "organizationId": organization_id}]
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/ketchup.jpg"}]
                    },
                    {
                        "itemId": mock_mayo_sauce_id,
                        "code": "S002",
                        "name": "Mayonnaise",
                        "description": "Creamy mayo.",
                        "type": "DISH",
                        "measureUnit": "g",
                        "order": 2,
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Standard",
                                "prices": [{"price": 0.75, "organizationId": organization_id}]
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/mayo.jpg"}]
                    }
                ]
            },
            {
                "id": MOCK_RECOMMENDATION_CATEGORY_ID, # Recommendation category ID
                "name": "Recommendations", # This name should match RECOMMENDATION_CATEGORY_NAME in your sync logic
                "description": "Our chef's specials!",
                "buttonImageUrl": "https://example.com/images/recommend_cat.jpg",
                "isHidden": False,
                "order": 4,
                "items": [
                    {
                        "itemId": mock_recommended_dessert_id,
                        "code": "R001",
                        "name": "Chocolate Lava Cake",
                        "description": "Warm chocolate cake with a molten center.",
                        "type": "DISH",
                        "measureUnit": "pc",
                        "order": 1,
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Standard",
                                "prices": [{"price": 6.50, "organizationId": organization_id}],
                                "nutritionPerHundredGrams": {
                                    "energy": 350.0,
                                    "carbs": 45.0,
                                    "fats": 18.0,
                                    "proteins": 5.0
                                }
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/lava_cake.jpg"}],
                        "tags": ["Dessert"]
                    }
                ]
            },
            {
                "id": "cat5-wok-id",
                "name": "Wok Constructor",
                "description": "Build your own wok!",
                "buttonImageUrl": "https://example.com/images/wok_cat.jpg",
                "isHidden": False,
                "order": 5,
                "items": [
                    {
                        "itemId": mock_wok_base_id, # Wok constructor product
                        "code": "WOK001",
                        "name": "Custom Wok",
                        "description": "Choose your base, protein, and veggies!",
                        "type": "DISH",
                        "measureUnit": "pc",
                        "order": 1,
                        "isPrepackaged": False, # Important for customizability
                        "modifierGroups": [
                            {
                                "id": mock_wok_base_addons_group_id, # Link to Wok Addons modifier group
                                "name": "Wok Ingredients",
                                "minAmount": 1,
                                "maxAmount": 5,
                                "childModifiers": [
                                    {
                                        "id": mock_wok_chicken_id,
                                        "type": "Product",
                                        "name": "Chicken",
                                        "defaultAmount": 1,
                                        "price": 3.00
                                    },
                                    {
                                        "id": mock_wok_veg_id,
                                        "type": "Product",
                                        "name": "Mixed Vegetables",
                                        "defaultAmount": 1,
                                        "price": 2.50
                                    }
                                ]
                            }
                        ],
                        "itemSizes": [
                            {
                                "id": str(uuid4()),
                                "name": "Standard",
                                "prices": [{"price": 8.00, "organizationId": organization_id}], # Base price
                                "nutritionPerHundredGrams": {
                                    "energy": 100.0,
                                    "carbs": 15.0,
                                    "fats": 2.0,
                                    "proteins": 3.0
                                }
                            }
                        ],
                        "images": [{"imageUrl": "https://example.com/images/wok_base.jpg"}]
                    }
                ]
            }
        ],
        "items": [ # Standalone items that might be modifiers or other special items
            # These might be modifiers that are not directly linked to a specific product
            # but are part of `modifierGroups` which are then linked to products.
            # Or they could be products not linked to a category directly (less common for menu items).
            {
                "itemId": str(uuid4()),
                "code": "MOD001",
                "name": "Spicy Sauce",
                "description": "Extra spicy kick.",
                "type": "MODIFIER",
                "measureUnit": "ml",
                "itemSizes": [
                    {
                        "id": str(uuid4()),
                        "name": "Standard",
                        "prices": [{"price": 0.75, "organizationId": organization_id}]
                    }
                ],
                "images": [{"imageUrl": "https://example.com/images/spicy_sauce.jpg"}]
            }
        ],
        "modifierGroups": [ # Modifier groups that can be referenced by items
            {
                "id": mock_burger_addons_group_id,
                "name": "Burger Toppings",
                "description": "Choose your toppings",
                "minAmount": 0,
                "maxAmount": 3,
                "childModifiers": [
                    {
                        "id": str(uuid4()),
                        "type": "Product", # Could be 'Product' or 'Modifier' depending on iiko setup
                        "name": "Bacon Strip",
                        "defaultAmount": 0,
                        "price": 2.00,
                        "image": "https://example.com/images/bacon.jpg"
                    },
                    {
                        "id": str(uuid4()),
                        "type": "Product",
                        "name": "Fried Egg",
                        "defaultAmount": 0,
                        "price": 1.00,
                        "image": "https://example.com/images/egg.jpg"
                    }
                ]
            },
            {
                "id": mock_wok_base_addons_group_id,
                "name": "Wok Proteins & Veggies",
                "description": "Select your wok ingredients",
                "minAmount": 1,
                "maxAmount": 5,
                "childModifiers": [
                    {
                        "id": mock_wok_chicken_id,
                        "type": "Product",
                        "name": "Chicken",
                        "defaultAmount": 1,
                        "price": 3.00,
                        "image": "https://example.com/images/chicken.jpg"
                    },
                    {
                        "id": mock_wok_veg_id,
                        "type": "Product",
                        "name": "Mixed Vegetables",
                        "defaultAmount": 1,
                        "price": 2.50,
                        "image": "https://example.com/images/veggies.jpg"
                    },
                    {
                        "id": str(uuid4()),
                        "type": "Product",
                        "name": "Tofu",
                        "defaultAmount": 0,
                        "price": 2.00,
                        "image": "https://example.com/images/tofu.jpg"
                    },
                    {
                        "id": str(uuid4()),
                        "type": "Product",
                        "name": "Shrimp",
                        "defaultAmount": 0,
                        "price": 4.00,
                        "image": "https://example.com/images/shrimp.jpg"
                    }
                ]
            }
        ],
        "outOfStock": [] # List of item IDs that are currently out of stock
    }

    app.logger.info(f"Mock IIKO Menu: Responding with menu data for organization {organization_id}.")
    return jsonify(mock_menu_data), 200


@app.route('/api/2/menu/by_id', methods=['POST'])
def get_menu_by_id_mock():
    """Mocks iiko /api/2/menu/by_id endpoint."""
    data = request.json
    headers = request.headers

    app.logger.info(f"Mock IIKO Menu by ID: Received request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    auth_header = headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.error("Mock IIKO Menu by ID: Missing or malformed Authorization header.")
        return jsonify({"error": "Unauthorized"}), 401

    if not data or 'organizationId' not in data or \
       'productIds' not in data or not isinstance(data['productIds'], list):
        app.logger.error("Mock IIKO Menu by ID: Missing or invalid 'organizationId' or 'productIds' in request payload.")
        return jsonify({"error": "Missing or invalid 'organizationId' or 'productIds'"}), 400

    organization_id = data['organizationId']
    product_ids_requested = data['productIds']

    # For a robust mock, you'd load the full menu (similar to /api/2/menu)
    # and then filter based on `product_ids_requested`.
    # For this example, we'll return a subset based on some known mock IDs.

    mock_items_by_id = {}
    # Populate this dict from a full mock menu if you have one, or define specific items
    # For now, let's just create a few on the fly that match previously defined stable IDs
    # and potential modifier IDs.

    # Example items (these should align with the full menu mock for consistency)
    if mock_burger_id in product_ids_requested:
        mock_items_by_id[mock_burger_id] = {
            "itemId": mock_burger_id,
            "code": "B001",
            "name": "Classic Cheeseburger",
            "description": "Juicy beef patty, cheddar, lettuce, tomato, pickles.",
            "type": "DISH",
            "measureUnit": "pc",
            "itemSizes": [
                {
                    "id": str(uuid4()),
                    "name": "Standard",
                    "prices": [{"price": 12.99, "organizationId": organization_id}],
                    "nutritionPerHundredGrams": {
                        "energy": 250.5, "carbs": 25.0, "fats": 15.0, "proteins": 10.0
                    }
                }
            ],
            "images": [{"imageUrl": "https://example.com/images/cheeseburger.jpg"}],
            "allergens": [{"id": str(uuid4()), "name": "Gluten"}, {"id": str(uuid4()), "name": "Dairy"}],
            "tags": ["Popular", "New"],
            "labels": ["Best Seller"],
            "modifierGroups": [ # Example of an inline modifier group definition
                {
                    "id": str(uuid4()), # Unique ID for this specific modifier group on this item
                    "name": "Sauces",
                    "minAmount": 0,
                    "maxAmount": 2,
                    "childModifiers": [
                        {"id": mock_ketchup_sauce_id, "type": "Product", "name": "Ketchup", "defaultAmount": 0, "price": 0.50},
                        {"id": mock_mayo_sauce_id, "type": "Product", "name": "Mayonnaise", "defaultAmount": 0, "price": 0.75},
                    ]
                }
            ]
        }

    if mock_ketchup_sauce_id in product_ids_requested:
        mock_items_by_id[mock_ketchup_sauce_id] = {
            "itemId": mock_ketchup_sauce_id,
            "code": "S001",
            "name": "Ketchup",
            "description": "Classic tomato ketchup.",
            "type": "MODIFIER", # It's common for addons to be type MODIFIER
            "measureUnit": "g",
            "itemSizes": [
                {
                    "id": str(uuid4()),
                    "name": "Standard",
                    "prices": [{"price": 0.50, "organizationId": organization_id}]
                }
            ],
            "images": [{"imageUrl": "https://example.com/images/ketchup.jpg"}]
        }

    if mock_wok_chicken_id in product_ids_requested:
        mock_items_by_id[mock_wok_chicken_id] = {
            "itemId": mock_wok_chicken_id,
            "code": "WCH001",
            "name": "Chicken (Wok Addon)",
            "description": "Grilled chicken strips for your wok.",
            "type": "MODIFIER", # Addons are often 'MODIFIER' type
            "measureUnit": "g",
            "itemSizes": [
                {
                    "id": str(uuid4()),
                    "name": "Standard",
                    "prices": [{"price": 3.00, "organizationId": organization_id}]
                }
            ],
            "images": [{"imageUrl": "https://example.com/images/chicken_addon.jpg"}]
        }
    # Add other items as needed for your specific test cases

    found_items = list(mock_items_by_id.values())

    response_data = {
        "correlationId": str(uuid4()),
        "items": found_items,
        "outOfStock": []
    }
    app.logger.info(f"Mock IIKO Menu by ID: Responding with {len(found_items)} items.")
    return jsonify(response_data), 200


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    app.run(host='0.0.0.0', port=5000, debug=True)
