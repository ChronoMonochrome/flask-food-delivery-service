from flask import Flask, request, jsonify
import json
from uuid import uuid4
from datetime import datetime
import logging
import re # For UUID validation regex

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Helper function to validate UUIDs
def is_valid_uuid(uuid_string):
    if not isinstance(uuid_string, str):
        return False
    # Regex for UUID v4
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.IGNORECASE)
    return bool(uuid_regex.match(uuid_string))

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

    # --- Validate UUID formats for IDs ---
    if not isinstance(organization_id, str) or not is_valid_uuid(organization_id):
        app.logger.error(f"Mock IIKO Delivery: Invalid organizationId format: {organization_id}")
        return jsonify({"error": "Invalid organizationId format (expected UUID)"}), 400
    # terminalGroupId returned by IIKO appears not to be a valid UUID, ignoring this
    if terminal_group_id is not None and (not isinstance(terminal_group_id, str)): # or not is_valid_uuid(terminal_group_id)):
        app.logger.error(f"Mock IIKO Delivery: Invalid terminalGroupId format: {terminal_group_id}")
        return jsonify({"error": "Invalid terminalGroupId format (expected UUID or null)"}), 400

    # --- Order Object Checks ---
    if not isinstance(order_payload, dict):
        app.logger.error("Mock IIKO Delivery: 'order' field must be an object.")
        return jsonify({"error": "'order' field must be an object"}), 400

    # Note: Removed 'externalNumber' from required here as per original client sample,
    # but the client code was updated to send it. Make sure this mock is aligned.
    required_order_fields = ['id', 'phone', 'items', 'deliveryPoint', 'payments'] # externalNumber is optional in this mock
    for field in required_order_fields:
        if field not in order_payload:
            app.logger.error(f"Mock IIKO Delivery: Missing required 'order' field: {field}")
            return jsonify({"error": f"Missing required 'order' field: {field}"}), 400

    order_id = order_payload.get('id')
    external_number = order_payload.get('externalNumber') # Optional in this mock's strict check
    phone = order_payload.get('phone')
    items = order_payload.get('items')
    delivery_point = order_payload.get('deliveryPoint')
    payments = order_payload.get('payments')
    complete_before = order_payload.get('completeBefore')
    order_service_type = order_payload.get('orderServiceType')

    # Validate Order ID and External Number (if present)
    if not isinstance(order_id, str) or not is_valid_uuid(order_id):
        app.logger.error(f"Mock IIKO Delivery: Invalid order.id format: {order_id}")
        return jsonify({"error": "Invalid order.id format (expected UUID)"}), 400
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
    if 'address' not in delivery_point or not isinstance(delivery_point['address'], dict):
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address' is missing or invalid.")
        return jsonify({"error": "'order.deliveryPoint.address' is missing or invalid"}), 400
    if 'street' not in delivery_point['address'] or not isinstance(delivery_point['address']['street'], str):
        app.logger.error("Mock IIKO Delivery: 'order.deliveryPoint.address.street' is missing or invalid.")
        return jsonify({"error": "'order.deliveryPoint.address.street' is missing or invalid"}), 400
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
    allowed_service_types = ["DeliveryByCourier", "DeliveryByClient"]
    if order_service_type and order_service_type not in allowed_service_types:
        app.logger.error(f"Mock IIKO Delivery: Invalid order.orderServiceType: {order_service_type}. Allowed: {allowed_service_types}")
        return jsonify({"error": f"Invalid order.orderServiceType: {order_service_type}"}), 400

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
        if not is_valid_uuid(item.get('productId', '')):
            app.logger.error(f"Mock IIKO Delivery: Invalid productId format for item at index {idx}.")
            return jsonify({"error": f"Invalid productId format for item at index {idx}"}), 400
        if not isinstance(item.get('amount'), (int, float)) or item.get('amount') <= 0:
            app.logger.error(f"Mock IIKO Delivery: Invalid amount for item at index {idx}.")
            return jsonify({"error": f"Invalid amount for item at index {idx}"}), 400
        if not is_valid_uuid(item.get('positionId', '')):
            app.logger.error(f"Mock IIKO Delivery: Invalid positionId format for item at index {idx}.")
            return jsonify({"error": f"Invalid positionId format for item at index {idx}"}), 400

        # Modifiers check
        if 'modifiers' in item:
            if not isinstance(item['modifiers'], list):
                app.logger.error(f"Mock IIKO Delivery: Modifiers for item at index {idx} must be a list.")
                return jsonify({"error": f"Modifiers for item at index {idx} must be a list"}), 400
            for mod_idx, modifier in enumerate(item['modifiers']):
                if not isinstance(modifier, dict) or 'id' not in modifier or 'type' not in modifier or 'amount' not in modifier:
                    app.logger.error(f"Mock IIKO Delivery: Malformed modifier at index {mod_idx} for item {idx}.")
                    return jsonify({"error": f"Malformed modifier at index {mod_idx} for item {idx}"}), 400
                if not is_valid_uuid(modifier.get('id', '')):
                    app.logger.error(f"Mock IIKO Delivery: Invalid modifier ID format at index {mod_idx} for item {idx}.")
                    return jsonify({"error": f"Invalid modifier ID format at index {mod_idx} for item {idx}"}), 400
                if modifier.get('type') != 'Product': # Or other allowed types
                    app.logger.warning(f"Mock IIKO Delivery: Unexpected modifier type '{modifier.get('type')}' at index {mod_idx} for item {idx}.")


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
        allowed_payment_kinds = ["Cash", "Card", "LoyaltyCard", "Credit"] # Add other kinds as needed
        if payment.get('paymentTypeKind') not in allowed_payment_kinds:
            app.logger.error(f"Mock IIKO Delivery: Invalid paymentTypeKind '{payment.get('paymentTypeKind')}' at index {idx}.")
            return jsonify({"error": f"Invalid paymentTypeKind at index {idx}"}), 400

        # paymentTypeId appears to be a non-valid UUID, ignoring this
        #if not is_valid_uuid(payment.get('paymentTypeId', '')):
        #    app.logger.error(f"Mock IIKO Delivery: Invalid paymentTypeId format for payment at index {idx}.")
        #    return jsonify({"error": f"Invalid paymentTypeId format for payment at index {idx}"}), 400
        
        # Check optional boolean fields if they are present and not bool
        for bool_field in ['isProcessedExternally', 'isFiscalizedExternally', 'isPrepay']:
            if bool_field in payment and not isinstance(payment.get(bool_field), bool):
                app.logger.error(f"Mock IIKO Delivery: Invalid type for '{bool_field}' for payment at index {idx} (expected boolean).")
                return jsonify({"error": f"Invalid type for '{bool_field}' for payment at index {idx} (expected boolean)."}), 400


    # If all checks pass, generate a successful response
    mock_order_id = str(uuid4())
    response_data = {
        "correlationId": str(uuid4()),
        "orderId": mock_order_id,
        "orderStatus": "OnDelivery",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "error": None
    }
    app.logger.info(f"Mock IIKO Delivery: Successfully created mock delivery order with ID: {mock_order_id}")
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

    for org_id in data['organizationIds']:
        if not is_valid_uuid(org_id):
            app.logger.error(f"Mock IIKO Payment Types: Invalid organizationId format: {org_id}")
            return jsonify({"error": f"Invalid organizationId format: {org_id}"}), 400

    # --- Sample Mock Payment Types ---
    # These UUIDs should be stable for your mock testing
    mock_cash_payment_id = "5a7e6c9b-d8f0-4a1b-8c7e-1e9d2f0a3b4c" # Example UUID for Cash
    mock_card_payment_id = "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e" # Example UUID for Card

    # Customize these mock payment types as needed
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
                    "id": str(uuid4()), # Mock Terminal Group ID, should match client's if specific
                    "organizationId": data['organizationIds'][0] if data['organizationIds'] else str(uuid4()),
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
                    "id": str(uuid4()),
                    "organizationId": data['organizationIds'][0] if data['organizationIds'] else str(uuid4()),
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

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    app.run(host='0.0.0.0', port=5000, debug=True)
