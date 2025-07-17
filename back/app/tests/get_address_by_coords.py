import requests
import json
import time

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
    # Nominatim API endpoint for reverse geocoding
    url = "https://nominatim.openstreetmap.org/reverse"

    # Parameters for the request
    params = {
        "format": "json",       # Request a JSON response
        "lat": latitude,
        "lon": longitude,
        "zoom": 18,             # Adjust zoom level for more detailed address (0=country, 18=building)
        "addressdetails": 1     # Include detailed address breakdown
    }

    # IMPORTANT: Provide a User-Agent to identify your application.
    # This is crucial for adhering to Nominatim's usage policy.
    # Replace 'YourAppName/1.0 (your.email@example.com)' with your actual app name and email.
    headers = {
        "User-Agent": "MyCoordinateToAddressApp/1.0 (my.email@example.com)"
    }

    try:
        # Send the GET request to the Nominatim API
        response = requests.get(url, params=params, headers=headers)

        # Raise an exception for HTTP errors (e.g., 404, 500)
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Check if an address was found
        if data and "display_name" in data:
            return data["display_name"]
        else:
            print(f"No address found for coordinates: {latitude}, {longitude}")
            print(f"Full API response: {data}") # Print full response for debugging
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Nominatim: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response content: {response.text}") # Print raw content for debugging
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Example coordinates (e.g., Brandenburg Gate, Berlin, Germany)
    lat_berlin = 52.51627
    lon_berlin = 13.37770

    print(f"Attempting to get address for coordinates: Lat {lat_berlin}, Lon {lon_berlin}")
    address_berlin = get_address_from_coordinates(lat_berlin, lon_berlin)

    if address_berlin:
        print(f"\nAddress found: {address_berlin}")
    else:
        print("\nCould not retrieve address for Berlin example.")

    # --- Another example (e.g., Eiffel Tower, Paris, France) ---
    print("\n--- Another Example ---")
    lat_eiffel = 48.8583701
    lon_eiffel = 2.2944813

    # Add a small delay to respect Nominatim's usage policy (1 request per second max)
    time.sleep(1.5) # Increased sleep slightly to be safe

    print(f"Attempting to get address for coordinates: Lat {lat_eiffel}, Lon {lon_eiffel}")
    address_eiffel = get_address_from_coordinates(lat_eiffel, lon_eiffel)

    if address_eiffel:
        print(f"\nAddress found: {address_eiffel}")
    else:
        print("\nCould not retrieve address for Eiffel Tower example.")

    # --- New Example: Red Square, Moscow, Russia ---
    print("\n--- New Example: Red Square, Moscow, Russia ---")
    lat_red_square = 55.754093
    lon_red_square = 37.620407

    # Add a small delay again
    time.sleep(1.5)

    print(f"Attempting to get address for coordinates: Lat {lat_red_square}, Lon {lon_red_square}")
    address_red_square = get_address_from_coordinates(lat_red_square, lon_red_square)

    if address_red_square:
        print(f"\nAddress found: {address_red_square}")
    else:
        print("\nCould not retrieve address for Red Square example.")