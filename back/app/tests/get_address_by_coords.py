import requests
import json
import time

def get_address_from_coordinates(latitude, longitude):
    """
    Retrieves the address for given latitude and longitude coordinates
    using OpenStreetMap's Nominatim reverse geocoding service.
    This updated version returns a dictionary with structured address details.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict or None: A dictionary containing detailed address components if found,
                      otherwise None.
                      Example structure:
                      {
                        "road": "Unter den Linden",
                        "suburb": "Mitte",
                        "city": "Berlin",
                        "postcode": "10117",
                        "country": "Deutschland",
                        "country_code": "de",
                        # ... other address details
                      }
    """
    # Nominatim API endpoint for reverse geocoding
    url = "https://nominatim.openstreetmap.org/reverse"

    # Parameters for the request
    params = {
        "format": "json",        # Request a JSON response
        "lat": latitude,
        "lon": longitude,
        "zoom": 18,              # Adjust zoom level for more detailed address (0=country, 18=building)
        "addressdetails": 1      # IMPORTANT: Include detailed address breakdown
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

        # Check if a detailed address was found and return it
        if data and "address" in data:
            return data["address"]
        else:
            print(f"No structured address found for coordinates: {latitude}, {longitude}")
            print(f"Full API response: {data}") # Print full response for debugging
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Nominatim: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        # Attempt to print raw response content if available, for debugging
        try:
            print(f"Raw response content: {response.text}")
        except NameError:
            print("No response content available.")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Example coordinates (e.g., Brandenburg Gate, Berlin, Germany)
    lat_berlin = 56.012226
    lon_berlin = 38.381220

    print(f"Attempting to get structured address for coordinates: Lat {lat_berlin}, Lon {lon_berlin}")
    address_berlin = get_address_from_coordinates(lat_berlin, lon_berlin)

    if address_berlin:
        print(f"\nStructured Address found for Berlin:")
        for key, value in address_berlin.items():
            print(f"  {key}: {value}")
        # You can access specific fields like this:
        # print(f"\n  City: {address_berlin.get('city', 'N/A')}")
        # print(f"  Road: {address_berlin.get('road', 'N/A')}")
        # print(f"  Postcode: {address_berlin.get('postcode', 'N/A')}")
    else:
        print("\nCould not retrieve structured address for Berlin example.")

    # --- Another example (e.g., Eiffel Tower, Paris, France) ---
    print("\n--- Another Example ---")
    lat_eiffel = 55.992897
    lon_eiffel = 38.373313

    # Add a small delay to respect Nominatim's usage policy (1 request per second max)
    time.sleep(1.5) # Increased sleep slightly to be safe

    print(f"Attempting to get structured address for coordinates: Lat {lat_eiffel}, Lon {lon_eiffel}")
    address_eiffel = get_address_from_coordinates(lat_eiffel, lon_eiffel)

    if address_eiffel:
        print(f"\nStructured Address found for Eiffel Tower:")
        for key, value in address_eiffel.items():
            print(f"  {key}: {value}")
    else:
        print("\nCould not retrieve structured address for Eiffel Tower example.")

    # --- New Example: Red Square, Moscow, Russia ---
    print("\n--- New Example: Red Square, Moscow, Russia ---")
    lat_red_square = 55.754093
    lon_red_square = 37.620407

    # Add a small delay again
    time.sleep(1.5)

    print(f"Attempting to get structured address for coordinates: Lat {lat_red_square}, Lon {lon_red_square}")
    address_red_square = get_address_from_coordinates(lat_red_square, lon_red_square)

    if address_red_square:
        print(f"\nStructured Address found for Red Square:")
        for key, value in address_red_square.items():
            print(f"  {key}: {value}")
    else:
        print("\nCould not retrieve structured address for Red Square example.")
