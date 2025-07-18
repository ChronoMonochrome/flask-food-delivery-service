import requests
import json
import uuid
from datetime import datetime

# --- Configuration ---
BASE_URL = "https://mytestapp001.ru/api"  # Replace with your actual base URL
TELEGRAM_USER_ID = "mock_user_123" # The X-Telegram-User-ID to use for testing

# --- Helper function to send POST requests ---
def post_request(endpoint, payload, headers=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"\nSending POST request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {headers}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
    return None

# --- Main Test Script ---
def test_order_creation():
    headers = {
        "X-Telegram-User-ID": TELEGRAM_USER_ID,
        "Content-Type": "application/json"
    }

    #55.99359738232752, 38.38600724002853}

    order_payload = {
        "address": "ул. Ленина, 10, кв. 5, г. Москва, 123456",
        "apartment": "5",
        "floor": "3",
        "phone": "+79123456789",
        "paymentMethod": "cash",
        "comment": "Позвоните за 10 минут до приезда.",
        "latitude": 55.99359738232752,
        "longitude": 38.38600724002853
    }

    create_order_response = post_request("/orders", order_payload, headers)

    if create_order_response:
        print("\nOrder creation test completed.")
        print(f"Order ID: {create_order_response.get('id')}")
        print(f"Order Total: {create_order_response.get('total')}")
        print(f"Order Status: {create_order_response.get('status')}")
    else:
        print("\nOrder creation failed.")

if __name__ == "__main__":
    test_order_creation()
