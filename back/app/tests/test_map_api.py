import requests
import json

BASE_URL = "https://mandarin.dev.routeam.ru/api/map"
DELIVERY_COST_MOCK = 100 # Assuming this is the mock delivery cost

# Mock get_address_from_coordinates for testing purposes
# This should ideally mimic the behavior of your actual get_address_from_coordinates
def get_address_from_coordinates_mock(latitude, longitude):
    if (latitude, longitude) == (55.99359738232752, 38.38600724002853):
        return "Берёзовая улица, Черноголовка, городской округ Черноголовка, Московская область, Центральный федеральный округ, 142432, Россия"
    elif latitude == 52.5200 and longitude == 13.4050:
        return "Alexanderplatz 1, 10178 Berlin, Germany"
    elif latitude == 48.8566 and longitude == 2.3522:
        return "Eiffel Tower, Champ de Mars, 75007 Paris, France"
    else:
        return f"Mock Address for Lat: {latitude}, Lon: {longitude}"


def run_test_case(test_name, params, expected_status=200):
    print(f"\n--- {test_name} ---")
    print(f"Testing endpoint: {BASE_URL}")
    print(f"Sending parameters: {params}")

    try:
        response = requests.get(BASE_URL, params=params)
        
        print(f"\nResponse Status Code: {response.status_code}")

        # Check if the response has JSON content
        if response.headers.get('Content-Type') == 'application/json':
            response_json = response.json()
            print("Response JSON:")
            # Use json.dumps with ensure_ascii=False for proper UTF-8 display
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        else:
            print("Response Content (not JSON):")
            print(response.text)

        # Basic assertion for status code
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, but got {response.status_code}"

        # Add more specific assertions based on your test cases
        if expected_status == 200:
            if response.headers.get('Content-Type') == 'application/json':
                assert "address" in response_json
                assert "delivery_cost" in response_json
                if "address" in response_json and params.get('latitude') == 55.99359738232752 and params.get('longitude') == 38.38600724002853:
                    assert response_json["address"] == get_address_from_coordinates_mock(params['latitude'], params['longitude'])
                    assert response_json["delivery_cost"] == DELIVERY_COST_MOCK
            else:
                print("Warning: Expected JSON response for 200 status, but got non-JSON.")
        elif expected_status == 404:
            if response.headers.get('Content-Type') == 'application/json':
                assert "message" in response_json
                assert "Coordinates are outside our valid delivery areas." in response_json["message"]
            else:
                print("Warning: Expected JSON response for 404 status, but got non-JSON.")
        elif expected_status == 400:
            if response.headers.get('Content-Type') == 'application/json':
                assert "message" in response_json
            else:
                print("Warning: Expected JSON response for 400 status, but got non-JSON.")
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except AssertionError as e:
        print(f"Assertion failed: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response.")

# --- Test Cases ---

# 1. Valid coordinates within a delivery area (example: Russian address for precision test)
run_test_case(
    "Test Case 1: Valid coordinates within a delivery area (Russian Address)",
    {'latitude': 55.99359738232752, 'longitude': 38.38600724002853}
)

# 2. Valid coordinates within a delivery area (another example)
run_test_case(
    "Test Case 2: Valid coordinates within a delivery area (Berlin)",
    {'latitude': 52.5200, 'longitude': 13.4050}
)

# 3. Valid coordinates within a delivery area (yet another example)
run_test_case(
    "Test Case 3: Valid coordinates within a delivery area (Paris)",
    {'latitude': 48.8566, 'longitude': 2.3522}
)

# 4. Coordinates outside all defined areas
run_test_case(
    "Test Case 4: Outside all defined areas (far north)",
    {'latitude': 57.0, 'longitude': 38.0},
    expected_status=404
)

# 5. Missing latitude
run_test_case(
    "Test Case 5: Missing latitude",
    {'longitude': 38.38600724002853},
    expected_status=400
)

# 6. Missing longitude
run_test_case(
    "Test Case 6: Missing longitude",
    {'latitude': 55.99359738232752},
    expected_status=400
)

# 7. Invalid latitude format
run_test_case(
    "Test Case 7: Invalid latitude format",
    {'latitude': 'abc', 'longitude': 38.38600724002853},
    expected_status=400
)

# 8. Invalid longitude format
run_test_case(
    "Test Case 8: Invalid longitude format",
    {'latitude': 55.99359738232752, 'longitude': 'xyz'},
    expected_status=400
)

# 9. Test with a point that's genuinely outside your defined areas based on your geojson_data
# You'll need to pick coordinates clearly outside any polygon in your actual geojson_data
run_test_case(
    "Test Case 9: Clearly outside any specific polygon (example from prompt)",
    {'latitude': 56.5, 'longitude': 37.0}, # Adjust based on your geojson_data's extent
    expected_status=404
)

# 10. Test for internal server error (if get_address_from_coordinates fails but is in area)
# This requires a way to mock get_address_from_coordinates to return None within an area
# For this example, we'll just show the structure, but it might be harder to trigger in a live setup without patching.
# In a real test, you might use `unittest.mock.patch` to simulate this.
# For now, we'll simulate by ensuring our mock returns None for a specific coordinate
def get_address_from_coordinates_failing_mock(latitude, longitude):
    if (latitude, longitude) == (55.99359738232752, 38.38600724002853):
        return None # Simulate failure for this specific point
    return get_address_from_coordinates_mock(latitude, longitude) # Use original mock for others

# Temporarily replace the mock function for this test case
original_get_address_mock = get_address_from_coordinates_mock
# This part won't work directly because `get_address_from_coordinates` is used in the Flask app context.
# To properly test this, you'd mock the function within the Flask app's execution environment,
# typically using a testing client and patching utilities like `unittest.mock.patch`.
# For the purpose of just fixing the test script's output, we'll keep it simple for now.

# print("\n--- Test Case 10: Simulate address lookup failure within delivery area ---")
# # This test case won't work as expected with simple function overriding here,
# # as the server's `get_address_from_coordinates` is a separate instance.
# # It's included to show the *intention* of such a test.
# # If you want to test this, you need to use a Flask testing client and patch the actual function.
# run_test_case(
#     "Test Case 10: Address lookup fails within delivery area (requires mocking in app)",
#     {'latitude': 55.99359738232752, 'longitude': 38.38600724002853}, # Pick a coord in a valid area
#     expected_status=500
# )
# get_address_from_coordinates_mock = original_get_address_mock # Restore

print("\nAll test cases executed.")