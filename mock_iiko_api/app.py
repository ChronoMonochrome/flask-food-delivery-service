# mock_iiko_api/app.py
from flask import Flask, request, jsonify
import logging
import os
from uuid import uuid4
from datetime import datetime
import json # Import json for pretty printing payload

app = Flask(__name__)

# Basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/api/1/access_token', methods=['POST'])
def access_token():
    """Mocks iiko /api/1/access_token endpoint."""
    data = request.json
    api_login = data.get('apiLogin')
    app.logger.info(f"Mock IIKO: Received access_token request with apiLogin: {api_login}")
    if api_login == os.getenv("IIKO_API_TOKEN"):
        return jsonify({"token": "mock-iiko-token-12345"}), 200
    return jsonify({"message": "Invalid API Login"}), 401

@app.route('/api/1/organizations', methods=['POST'])
def organizations():
    """Mocks iiko /api/1/organizations endpoint."""
    data = request.json
    headers = request.headers
    # Use ensure_ascii=False for proper display of Cyrillic characters in logs
    app.logger.info(f"Mock IIKO: Received organizations request. Payload: {json.dumps(data, indent=2, ensure_ascii=False)}. Headers: {headers}")
    # Dummy organization data with Cyrillic names
    orgs = [
        {"id": "mock-org-1", "name": "Тестовая Организация 1", "inn": "1234567890"},
        {"id": "mock-org-2", "name": "Вторая Организация", "inn": "0987654321"}
    ]
    return jsonify({"organizations": orgs}), 200

@app.route('/api/1/terminal_groups', methods=['POST'])
def terminal_groups():
    """Mocks iiko /api/1/terminal_groups endpoint."""
    data = request.json
    headers = request.headers
    # Use ensure_ascii=False for proper display of Cyrillic characters in logs
    app.logger.info(f"Mock IIKO: Received terminal_groups request for orgs: {json.dumps(data.get('organizationIds'), indent=2, ensure_ascii=False)}. Headers: {headers}")

    requested_org_ids = data.get('organizationIds', [])
    include_disabled = data.get('includeDisabled', False)

    # Dummy terminal group data - link them to organization IDs with Cyrillic names
    all_tgs = [
        {"id": "mock-tg-alpha", "organizationId": "mock-org-1", "name": "Главная Группа Терминалов", "isOnlineOrder": True},
        {"id": "mock-tg-beta", "organizationId": "mock-org-1", "name": "Вторичная Группа Терминалов", "isOnlineOrder": False},
        {"id": "mock-tg-gamma", "organizationId": "mock-org-2", "name": "Группа Терминалов Гамма", "isOnlineOrder": True},
    ]

    # Filter by requested organization IDs
    filtered_tgs = [
        tg for tg in all_tgs
        if not requested_org_ids or tg["organizationId"] in requested_org_ids
    ]

    response_structure = []
    for org_id in set(tg["organizationId"] for tg in filtered_tgs):
        org_tgs = [tg for tg in filtered_tgs if tg["organizationId"] == org_id]
        response_structure.append({
            "organizationId": org_id,
            "items": org_tgs
        })

    return jsonify({"terminalGroups": response_structure}), 200

@app.route('/api/1/order/create', methods=['POST'])
def create_order():
    """Mocks iiko /api/1/order/create endpoint."""
    data = request.json
    headers = request.headers
    # Use ensure_ascii=False for proper display of Cyrillic characters in logs
    app.logger.info(f"Mock IIKO: Received create_order request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    organization_id = data.get('organizationId')
    terminal_group_id = data.get('terminalGroupId')
    table_ids = data.get('tableIds')
    order = data.get('order')

    if not all([organization_id, terminal_group_id, table_ids, order]):
        return jsonify({"message": "Missing required fields"}), 400

    mock_order_id = str(uuid4())
    response_data = {
        "correlationId": str(uuid4()),
        "orderId": mock_order_id,
        "orderStatus": "InProgress",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "error": None
    }
    app.logger.info(f"Mock IIKO: Successfully created mock order with ID: {mock_order_id}")
    return jsonify(response_data), 200

@app.route('/api/1/deliveries/create', methods=['POST'])
def create_delivery():
    """Mocks iiko /api/1/deliveries/create endpoint."""
    data = request.json
    headers = request.headers
    # Use ensure_ascii=False for proper display of Cyrillic characters in logs
    app.logger.info(f"Mock IIKO Delivery: Received create_delivery request. Headers: {headers}, Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    organization_id = data.get('organizationId')
    terminal_group_id = data.get('terminalGroupId')
    order = data.get('order')

    if not all([organization_id, terminal_group_id, order]):
        return jsonify({"message": "Missing required fields for delivery order"}), 400

    mock_delivery_id = str(uuid4())
    response_data = {
        "correlationId": str(uuid4()),
        "orderId": mock_delivery_id,
        "orderStatus": "OnDelivery",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "error": None
    }
    app.logger.info(f"Mock IIKO Delivery: Successfully created mock delivery order with ID: {mock_delivery_id}")
    return jsonify(response_data), 200

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    app.run(host='0.0.0.0', port=5000, debug=True)
