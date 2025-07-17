import requests
import json

# Define the base URL of your API
BASE_URL = "https://mytestapp001.ru"
API_ENDPOINT = f"{BASE_URL}/api/map"

def test_map_endpoint(latitude, longitude):
    """
    Sends GET request with coordinates to the /api/map endpoint
    and prints the response.
    """
    params = {}
    # Only add parameters if they are not None, to test missing params
    if latitude is not None:
        params['latitude'] = latitude
    if longitude is not None:
        params['longitude'] = longitude

    print(f"Testing endpoint: {API_ENDPOINT}")
    print(f"Sending parameters: {params}")

    try:
        response = requests.get(API_ENDPOINT, params=params)

        print(f"\nResponse Status Code: {response.status_code}")
        
        # Try to parse response as JSON
        try:
            json_response = response.json()
            print("Response JSON:")
            print(json.dumps(json_response, indent=2))
        except json.JSONDecodeError:
            print("Response Content (not JSON):")
            print(response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"\nError: Could not connect to the server at {BASE_URL}. Is the server running and accessible?")
        print(f"Details: {e}")
    except requests.exceptions.Timeout as e:
        print(f"\nError: Request timed out.")
        print(f"Details: {e}")
    except requests.exceptions.RequestException as e:
        print(f"\nAn unexpected error occurred during the request.")
        print(f"Details: {e}")

if __name__ == "__main__":
    print("--- Test Case 1: Inside Area 1 (roughly central within the first LineString) ---")
    test_map_endpoint(56.000, 38.380) # lat, lon
    print("-" * 50)

    print("\n--- Test Case 2: Inside Area 2 (roughly central within the second LineString) ---")
    test_map_endpoint(56.000, 38.380) # Reusing similar coords if overlaps, or pick new
    print("-" * 50)
    
    print("\n--- Test Case 3: Inside Area 3 (within the third LineString) ---")
    test_map_endpoint(56.000, 38.380) # Again, adjust if areas are distinct
    print("-" * 50)

    print("\n--- Test Case 4: Inside Area 4 (within the fourth LineString) ---")
    test_map_endpoint(56.000, 38.380)
    print("-" * 50)
    
    print("\n--- Test Case 5: Inside Area 5 (within the fifth LineString) ---")
    test_map_endpoint(56.000, 38.380)
    print("-" * 50)

    print("\n--- Test Case 6: Very close to a boundary (may be inside or outside depending on precision) ---")
    # Using a point from the GeoJSON as an example of being near a boundary
    test_map_endpoint(55.99359738232752, 38.38600724002853)
    print("-" * 50)

    print("\n--- Test Case 7: Outside all defined areas (far north) ---")
    test_map_endpoint(57.000, 38.000) # Significantly outside the provided range
    print("-" * 50)

    print("\n--- Test Case 8: Outside all defined areas (far south-east) ---")
    test_map_endpoint(55.500, 39.000) # Significantly outside the provided range
    print("-" * 50)

    print("\n--- Test Case 9: Missing longitude parameter ---")
    test_map_endpoint(56.000, None)
    print("-" * 50)

    print("\n--- Test Case 10: Malformed latitude parameter (non-numeric) ---")
    test_map_endpoint("not_a_number", 38.380)
    print("-" * 50)

    print("\n--- Test Case 11: Malformed longitude parameter (non-numeric) ---")
    test_map_endpoint(56.000, "invalid_lon")
    print("-" * 50)

    print("\n--- Test Case 12: Both parameters missing ---")
    test_map_endpoint(None, None)
    print("-" * 50)