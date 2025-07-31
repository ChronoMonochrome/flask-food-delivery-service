import requests
from app.config import Config
from app.logger import logger
from app.models import db, Category, MainCategory, Product, Addon, Recommendation, ProductAddon, ProductRecommendation, SAUCES_CATEGORY_NAME, WOK_PRODUCT_CONSTRUCTOR_ID
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os

from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

# Import diskcache
from diskcache import Cache

# Initialize the cache
# The cache directory will be 'iiko_cache' in the current working directory
# Data will expire after 900 seconds (15 minutes)
cache = Cache('iiko_cache', expire=900)

USING_MOCK = False
IIKO_API_URL = os.getenv("IIKO_API_URL")
IIKO_API_MOCK_URL = "http://mock_iiko:5000"

IIKO_API_TOKEN = Config.IIKO_API_TOKEN

RECOMMENDATION_CATEGORY_NAME = "Рекомендованные (сиутативные)"

# --- Icon and Color Mappings ---
# These are custom mappings and are not sourced from iiko API directly.
# They will be used to set default icons and colors for categories.
icon_map = {
    # Main categories, trying to generalize where possible
    "Доставка": "🚚",
    "Горячие блюда": "🍲",
    "Фокачча": "🍞",
    "Суши и роллы/Маки": "🍣",
    "Wok": "🍜",
    "Паста": "🍝",
    "Напитки": "🥤",
    "Пицца/ Неаполитано": "🍕",
    "Суши и роллы/Спайси": "🌶️", # Spice indicates a spicy variant
    "Горячие закуски": "🔥", # Hot/fire for hot snacks
    "Суши и роллы/запеченные роллы": "🍣🔥", # Sushi with a fire symbol for baked
    "Рекомендованные (общие)": "⭐", # Star for general recommendations
    "Пицца/Римская": "🍕",
    "Хачапури/Хачапури по-аджарски ": "🧀🍳", # Cheese and egg for Adjaruli
    "Салаты": "🥗",
    "Хачапури/Хачапури по-имеретински": "🧀", # Cheese for Imeretinski
    "Суши и роллы/Соевый соус, васаби, имбирь": "🧂", # Salt shaker for condiments
    "Пицца/Кальцоне": "🍕",
    "Осетинские пироги": "🥧",
    "Пицца": "🍕", # General Pizza
    "Суши и роллы/Роллы": "🍣", # General Rolls
    "Суши и роллы": "🍣", # Even more general Sushi & Rolls
    "Суши и роллы/Sеты": "🍱", # Sets
    "Суши и роллы/онигири": "🍙", # Onigiri
    "Суши и роллы/Серия 'Черный бархат'": "🖤🍣", # Black heart + sushi for "Black Velvet" series
    "Рулетики": "🌯",
    "Суши и роллы/Гунканы": "🍣", # Gunkan, using general sushi icon
    "Супы ": "🥣", # Space after Супы, keeping as is
    "Хачапури": "🧀", # General Khachapuri
    "Суши и роллы/горячие роллы": "🍣🔥", # Hot rolls
    "Суши и роллы/Нигири": "🍣", # Nigiri, using general sushi icon
    "Добавки": "➕", # General Addons/Extras
    "Кимпабы": "🍙", # Kimbap, using onigiri as closest
    "Пицца/Классическая": "🍕",
    "Пицца/Чикаго": "🍕",
    "Хот-доги и донер": "🌭",
    "Бургеры": "🍔",
    "Рекомендованные (сиутативные)": "💡", # Lightbulb for situational recommendations

    # Addons specific keys (from your old map, map to new specific addon types)
    "Добавки/Сыр": "🧀",
    "Добавки/Мясо": "🥩",
    "Добавки/Рыба и морепродукты": "🦐",

    # Keeping some very specific old keys for completeness if they might still appear as product types
    # "Кальцоне": "🍕", # Already handled by "Пицца/Кальцоне"
    # "Ламаджо": "🍖", # Not in new list, keeping for now if a product is "Ламаджо"
    # "Лапша": "🍜", # Not in new list, keeping for now if a product is "Лапша"
    # "Начинка": "🌶️", # Not in new list, implies "Добавки"
    # "Дополнительный соус": "🧂", # Not in new list, implies "Добавки" or "Суши и роллы/Соевый соус..."
    # "Донер на выбор": "🥙", # Not in new list, implies "Хот-доги и донер"
    # "Сосиска на выбор": "🌭", # Not in new list, implies "Хот-доги и донер"
    # "Допы горячий цех": "🔥", # Not in new list, implies "Горячие закуски" or "Добавки"
    # "Fasty rolls": "🌯", # Not in new list, but matches "Рулетики"
    # "По-имеретински": "🥧", # More specific now, covered by "Хачапури/Хачапури по-имеретински"
    # "КАФЕ ПИЦЦА 35см": "🍕", "КАФЕ ПИЦЦА РИМСКАЯ": "🍕", "Пицца 35 см.": "🍕",
    # "Пицца Неаполитано 24 см": "🍕", "Пицца Чикаго 29 см": "🍕", "Римская пицца": "🍕" # Covered by specific pizza types
}


color_map = {
    # Main categories
    "Доставка": "from-blue-500 to-indigo-600",
    "Горячие блюда": "from-red-600 to-pink-700",
    "Фокачча": "from-yellow-600 to-orange-700",
    "Суши и роллы/Маки": "from-blue-300 to-purple-500",
    "Wok": "from-purple-400 to-fuchsia-500",
    "Паста": "from-red-300 to-red-500",
    "Напитки": "from-teal-400 to-cyan-500",
    "Пицца/ Неаполитано": "from-red-400 to-red-600",
    "Суши и роллы/Спайси": "from-orange-500 to-red-600",
    "Горячие закуски": "from-amber-400 to-orange-600",
    "Суши и роллы/запеченные роллы": "from-orange-400 to-red-500", # Warm tones for baked
    "Рекомендованные (общие)": "from-yellow-400 to-yellow-600",
    "Пицца/Римская": "from-red-500 to-pink-600",
    "Хачапури/Хачапури по-аджарски ": "from-lime-500 to-green-600",
    "Салаты": "from-green-400 to-lime-500",
    "Хачапури/Хачапури по-имеретински": "from-lime-400 to-green-500",
    "Суши и роллы/Соевый соус, васаби, имбирь": "from-gray-500 to-gray-700",
    "Пицца/Кальцоне": "from-orange-400 to-red-500",
    "Осетинские пироги": "from-yellow-500 to-lime-600",
    "Пицца": "from-red-400 to-red-600", # General Pizza
    "Суши и роллы/Роллы": "from-blue-300 to-indigo-500", # General Rolls
    "Суши и роллы": "from-blue-400 to-purple-500", # General Sushi & Rolls
    "Суши и роллы/Сеты": "from-pink-500 to-purple-600",
    "Суши и роллы/онигири": "from-gray-300 to-gray-500",
    "Суши и роллы/Серия 'Черный бархат'": "from-gray-800 to-black",
    "Рулетики": "from-amber-400 to-orange-500",
    "Суши и роллы/Гунканы": "from-blue-400 to-purple-500",
    "Супы ": "from-emerald-400 to-cyan-600",
    "Хачапури": "from-lime-500 to-green-600", # General Khachapuri
    "Суши и роллы/горячие роллы": "from-orange-400 to-red-500", # Warm tones for hot rolls
    "Суши и роллы/Нигири": "from-blue-400 to-purple-500",
    "Добавки": "from-gray-400 to-gray-600",
    "Кимпабы": "from-green-500 to-emerald-600",
    "Пицца/Классическая": "from-red-400 to-red-600",
    "Пицца/Чикаго": "from-red-700 to-red-900", # Deeper red for Chicago style
    "Хот-доги и донер": "from-orange-400 to-red-500",
    "Бургеры": "from-yellow-400 to-orange-500",
    "Рекомендованные (сиутативные)": "from-purple-400 to-pink-500", # Distinct color for situational recommendations

    # Addons specific keys
    "Добавки/Сыр": "from-yellow-300 to-yellow-500",
    "Добавки/Мясо": "from-red-700 to-pink-800",
    "Добавки/Рыба и морепродукты": "from-blue-500 to-cyan-600",
}


# --- Helper functions for iiko API interaction ---
# Cache IIKO token for 10 minutes (600 seconds)
@cache.memoize(expire=10 * 60)
def get_iiko_token():
    """
    Получить токен доступа для работы с iiko API.
    """
    logger.info("Fetching iiko token...")
    url = f"{IIKO_API_URL}/api/1/access_token"
    payload = {"apiLogin": IIKO_API_TOKEN}
    try:
        response = requests.post(url, json=payload, timeout=10) # Added timeout
        response.raise_for_status()
        token = response.json().get("token")
        logger.info(f"iiko token fetched successfully.")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting iiko token: {e}")
        return None

# Cache organizations for 10 minutes (600 seconds)
@cache.memoize(expire=10 * 60)
def get_organizations(token):
    """
    Получить список организаций.
    """
    logger.info("Fetching organizations...")
    url = f"{IIKO_API_URL}/api/1/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": []} # Empty list to get all organizations
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10) # Added timeout
        response.raise_for_status()
        organizations = response.json().get("organizations", [])
        logger.info(f"Fetched {len(organizations)} organizations.")
        return organizations
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting organizations: {e}")
        return None

# Cache terminal groups for 10 minutes (600 seconds)
@cache.memoize(expire=10 * 60)
def get_terminal_groups(organization_id: str, token: str):
    """
    Получить терминальные группы для организации.
    """
    logger.info(f"Fetching terminal groups for organization {organization_id} from IIKO...")
    url = f"{IIKO_API_URL}/api/1/terminal_groups"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": [organization_id], "includeDisabled": True}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        terminal_groups_data = response.json().get("terminalGroups", [])
        logger.info(f"Fetched {len(terminal_groups_data)} terminal group entries for organization {organization_id}.")
        return terminal_groups_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting terminal groups from IIKO for organization {organization_id}: {e}")
        return None

# Cache menu summary for 2 hours (7200 seconds)
@cache.memoize(expire=2 * 60 * 60)
def get_menu_summary(token):
    """
    Получить сводную информацию по меню (список доступных внешних меню).
    """
    logger.info("Fetching menu summary...")
    url = f"{IIKO_API_URL}/api/2/menu"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()
        menu_summary = response.json()
        logger.info(f"Menu summary fetched with {len(menu_summary.get('externalMenus', []))} external menus.")
        return menu_summary
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting menu summary: {e}")
        return None

# Cache menu details by ID for 2 hours (7200 seconds)
@cache.memoize(expire=2 * 60 * 60)
def get_menu_details_by_id(organization_id, menu_id, token):
    """
    Получить номенклатуру (детали меню) для конкретной организации и внешнего меню ID.
    """
    logger.info(f"Fetching menu details for organization {organization_id} and menu {menu_id}...")
    url = f"{IIKO_API_URL}/api/2/menu/by_id"
    headers = {"Authorization": f"Bearer {token}"}
    json_payload = {"externalMenuId": menu_id, "organizationIds": [organization_id]}
    try:
        response = requests.post(url, headers=headers, json=json_payload, timeout=30) # Increased timeout
        response.raise_for_status()
        data = response.json()
        logger.info("Menu details fetched successfully.")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting menu by ID: {e}")
        return None

def get_iiko_menu_data():
    """
    Оркестрирует вызовы iiko API для получения полного меню.
    Возвращает (iiko_menu_data, main_organization_id)
    """
    token = get_iiko_token()
    if not token:
        return None, None

    try:
        organizations = get_organizations(token)
        if not organizations:
            logger.info("No organizations found. Cannot proceed with menu sync.")
            return None, None
        
        main_organization_id = organizations[0]["id"]
        logger.info(f"Using primary organization ID: {main_organization_id}")

        menu_summary = get_menu_summary(token)
        if not menu_summary or not menu_summary.get("externalMenus"):
            logger.info("No external menus found. Cannot retrieve detailed menu.")
            return None, main_organization_id
        
        # Take the first external menu for synchronization
        first_external_menu_id = menu_summary["externalMenus"][0]["id"]
        logger.info(f"Using first external menu ID: {first_external_menu_id}")

        menu_data = get_menu_details_by_id(main_organization_id, first_external_menu_id, token)
        return menu_data, main_organization_id

    except Exception as e:
        logger.error(f"An error occurred during iiko menu data retrieval: {e}")
        return None, None

def get_addons_from_iiko_item(iiko_item):
    """
    Extracts addon (modifier) information from a single iiko item structure,
    including those nested within itemSizes -> itemModifierGroups.

    Args:
        iiko_item (dict): A dictionary representing an iiko menu item.

    Returns:
        list: A list of dictionaries, where each dictionary represents an addon
              with keys matching the Addon model fields (iiko_addon_id, name, price, image).
    """
    addons = []
    
    # Check for itemModifierGroups directly under the main item (less common but possible)
    if "itemModifierGroups" in iiko_item and iiko_item["itemModifierGroups"]:
        for modifier_group in iiko_item["itemModifierGroups"]:
            if "name" in modifier_group and modifier_group["name"]:
                addon_group_name = modifier_group["name"] # Corrected: use modifier_group["name"]
            else:
                addon_group_name = "Ungrouped"
            if "items" in modifier_group and modifier_group["items"]:
                for addon_data in modifier_group["items"]:
                    addon_id = addon_data.get("id") or addon_data.get("itemId") # Use 'id' or 'itemId'
                    if not addon_id:
                        logger.warning(f"Skipping addon with no ID found in modifier group for item: {iiko_item.get('name', 'N/A')}")
                        continue

                    addon_name = addon_data.get("name")
                    addon_price = Decimal('0.00')
                    
                    if addon_data.get("prices"):
                        raw_price = addon_data["prices"][0].get("price")
                        try:
                            if isinstance(raw_price, (int, float)):
                                addon_price = Decimal(str(raw_price))
                            elif isinstance(raw_price, str):
                                cleaned_price_str = raw_price.replace(',', '.').strip()
                                addon_price = Decimal(cleaned_price_str)
                        except InvalidOperation as e:
                            logger.error(f"Error converting price '{raw_price}' for addon '{addon_name}' (ID: {addon_id}): {e}. Defaulting to 0.00.")

                    addon_image = None
                    # Prioritize buttonImageUrl from first itemSize if available, then general images
                    if addon_data.get("itemSizes"):
                        first_size = addon_data["itemSizes"][0]
                        addon_image = first_size.get("buttonImageUrl")
                    
                    if not addon_image and addon_data.get("images"):
                        addon_image = addon_data["images"][0].get("imageUrl")
                    elif not addon_image and addon_data.get("picture"):
                        addon_image = addon_data["picture"]

                    addons.append({
                        "iiko_addon_id": addon_id,
                        "group_name": addon_group_name,
                        "name": addon_name,
                        "price": addon_price,
                        "image": addon_image
                    })

    # Check for itemModifierGroups nested within itemSizes
    if "itemSizes" in iiko_item and iiko_item["itemSizes"]:
        for size in iiko_item["itemSizes"]:
            if "itemModifierGroups" in size and size["itemModifierGroups"]:
                for modifier_group in size["itemModifierGroups"]:
                    if "name" in modifier_group and modifier_group["name"]:
                        addon_group_name = modifier_group["name"]
                    else:
                        addon_group_name = "Ungrouped"
                    if "items" in modifier_group and modifier_group["items"]:
                        for addon_data in modifier_group["items"]:
                            addon_id = addon_data.get("id") or addon_data.get("itemId")
                            if not addon_id:
                                logger.warning(f"Skipping nested addon with no ID found in modifier group for item: {iiko_item.get('name', 'N/A')}")
                                continue

                            # Check if this addon is already added (to avoid duplicates if present in multiple paths)
                            if any(a['iiko_addon_id'] == addon_id for a in addons):
                                continue

                            addon_name = addon_data.get("name")
                            addon_price = Decimal('0.00')
                            
                            if addon_data.get("prices"):
                                raw_price = addon_data["prices"][0].get("price")
                                try:
                                    if isinstance(raw_price, (int, float)):
                                        addon_price = Decimal(str(raw_price))
                                    elif isinstance(raw_price, str):
                                        cleaned_price_str = raw_price.replace(',', '.').strip()
                                        addon_price = Decimal(cleaned_price_str)
                                except InvalidOperation as e:
                                    logger.error(f"Error converting price '{raw_price}' for nested addon '{addon_name}' (ID: {addon_id}): {e}. Defaulting to 0.00.")

                            addon_image = None
                            if addon_data.get("itemSizes"):
                                first_size = addon_data["itemSizes"][0]
                                addon_image = first_size.get("buttonImageUrl")
                            
                            if not addon_image and addon_data.get("images"):
                                addon_image = addon_data["images"][0].get("imageUrl")
                            elif not addon_image and addon_data.get("picture"):
                                addon_image = addon_data["picture"]

                            addons.append({
                                "iiko_addon_id": addon_id,
                                "group_name": addon_group_name,
                                "name": addon_name,
                                "price": addon_price,
                                "image": addon_image
                            })
    return addons
    
def _make_post_request(url_path: str, payload: Dict[str, Any], token: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Helper function to make a POST request.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    full_url = f"{IIKO_API_URL}{url_path}" # Changed 'url' to 'url_path' for consistency
    try:
        response = requests.post(full_url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text if response else 'N/A'}")
        raise
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred: {conn_err}")
        raise
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred: {timeout_err}")
        raise
    except requests.exceptions.RequestException as req_err:
        logger.error(f"An unexpected request error occurred: {req_err}")
        raise
    
# Cache cities for 24 hours (86400 seconds)
@cache.memoize(expire=24 * 60 * 60)
def get_cities(organization_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Получить список городов для указанных организаций.
    """
    token = get_iiko_token()
    if not token:
        raise RuntimeError("Failed to get IIKO token.")

    url = "/api/1/cities"
    payload = {"organizationIds": organization_ids}
    logger.info(f"Получаем города для {organization_ids}.")
    try:
        response_json = _make_post_request(url, payload, token, timeout=10)
        cities = response_json.get("cities", [])
        logger.info(f"Города для {organization_ids} получены.")
        return cities
    except Exception as e:
        logger.error(f"Ошибка получения городов: {e}")
        raise

# Cache streets by city for 24 hours (86400 seconds)
@cache.memoize(expire=24 * 60 * 60)
def get_streets_by_city(organization_id: str, city_id: str) -> List[Dict[str, Any]]:
    """
    Получить список улиц для указанного города и организации.
    """
    token = get_iiko_token()
    if not token:
        raise RuntimeError("Failed to get IIKO token.")

    url = "/api/1/streets/by_city"
    payload = {"organizationId": organization_id, "cityId": city_id}
    logger.info(f"Получаем улицы для города {city_id} (организация: {organization_id}).")
    try:
        response_json = _make_post_request(url, payload, token, timeout=10)
        streets = response_json.get("streets", [])
        logger.info(f"Улицы для города {city_id} получены.")
        return streets
    except Exception as e:
        logger.error(f"Ошибка получения улиц: {e}")
        raise


# Add other IIKO service functions as they were (e.g., get_payment_types, create_delivery_order)
def get_payment_types(organization_ids: List[str], token: str) -> List[Dict[str, Any]]:
    """
    Retrieves a list of payment types from the IIKO API for specified organizations.
    """
    logger.info(f"Fetching payment types for organizations {organization_ids} from IIKO...")
    url = f"{IIKO_API_URL}/api/1/payment_types"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": organization_ids}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        payment_types_data = response.json().get("paymentTypes", [])
        # IIKO returns a list of dicts, each containing 'organizationId' and 'items' (list of payment types)
        # We want to flatten this into a single list of all payment types
        all_payment_types = []
        for org_data in payment_types_data:
            all_payment_types.extend(org_data.get('items', []))
        logger.info(f"Fetched {len(all_payment_types)} payment types for organizations {organization_ids}.")
        return all_payment_types
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting payment types from IIKO for organizations {organization_ids}: {e}")
        raise

def create_delivery_order(organization_id: str, terminal_group_id: str, order: Dict[str, Any], create_order_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a delivery order to the IIKO API.
    """
    logger.info(f"Sending delivery order for organization {organization_id}, terminal group {terminal_group_id} to IIKO.")
    token = get_iiko_token() # Re-fetch token to ensure it's fresh for crucial calls
    if not token:
        raise RuntimeError("Failed to get IIKO token for order creation.")

    url = f"{IIKO_API_URL}/api/1/deliveries/create"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "organizationId": organization_id,
        "terminalGroupId": terminal_group_id,
        "order": order,
        "createOrderSettings": create_order_settings
    }
    
    try:
        # Use a longer timeout for order creation as it can take more time
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"IIKO delivery order response: {response_data}")
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending delivery order to IIKO: {e}")
        # Log the full response text if available for debugging
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"IIKO API Error Response Text: {e.response.text}")
        raise

def create_delivery_order(organization_id: str, terminal_group_id: str, order: dict, create_order_settings: dict = None):
    """
    Создать заказ на доставку в iiko (или в mock-сервис).

    :param organization_id: ID организации.
    :param terminal_group_id: ID терминальной группы.
    :param order: Полностью сформированный заказ (словарь).
    :param create_order_settings: Дополнительные настройки для создания заказа (словарь).
    :return: Ответ API iiko.
    """
    logger.info(f"Attempting to create delivery order in IIKO for organization: {organization_id}, terminal group: {terminal_group_id}")
    url = f"{IIKO_API_MOCK_URL}/api/1/deliveries/create" # This is the endpoint for delivery orders
    token = get_iiko_token() # Get token for each request, or cache it appropriately
    if not token:
        logger.error("Failed to get IIKO access token, cannot create delivery order.")
        raise Exception("Failed to get IIKO access token.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "organizationId": organization_id,
        "terminalGroupId": terminal_group_id,
        "order": order,
        "createOrderSettings": create_order_settings or {"transportToFrontTimeout": 0}
    }
    logger.info(f"Sending IIKO delivery order payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Successfully created delivery order in IIKO. Response: {response_json}")
        return response_json
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating delivery order in IIKO: {e}")
        if response is not None:
            logger.error(f"IIKO API Response content: {response.text}")
        raise

def get_payment_types(organization_ids, token):
    """
    Retrieves payment types for given organization IDs from IIKO.
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"organizationIds": organization_ids}
        response = requests.post(f"{IIKO_API_URL}/api/1/payment_types", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"Successfully retrieved IIKO payment types.")
        return response_data.get("paymentTypes", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting IIKO payment types: {e}", exc_info=True)
        if e.response:
            logger.error(f"IIKO Payment Types Error Response: {e.response.text}")
        return None

# Helper function for safe Decimal conversion
def _safe_decimal_conversion(raw_price, item_name, item_id, default_value=Decimal('0.00')):
    """Safely converts a raw price value to a Decimal."""
    if raw_price is None:
        logger.info(f"WARNING: Price is None for item '{item_name}' (ID: {item_id}). Defaulting to {default_value}.")
        return default_value
    try:
        if isinstance(raw_price, (int, float)):
            return Decimal(str(raw_price))
        elif isinstance(raw_price, str):
            cleaned_price_str = raw_price.replace(',', '.').strip()
            return Decimal(cleaned_price_str)
        else:
            logger.info(f"WARNING: Unexpected type for price '{type(raw_price)}' for item '{item_name}' (ID: {item_id}). Defaulting to {default_value}.")
            return default_value
    except InvalidOperation as e:
        logger.error(f"Error converting price '{raw_price}' for item '{item_name}' (ID: {item_id}): {e}. Defaulting to {default_value}.")
        return default_value

def _extract_item_image_url(iiko_item):
    """Extracts the best available image URL from an iiko item."""
    item_image_url = None
    item_sizes = iiko_item.get('itemSizes', [])
    if item_sizes:
        item_image_url = item_sizes[0].get('buttonImageUrl')

    if not item_image_url and iiko_item.get('images'):
        item_image_url = iiko_item['images'][0].get('imageUrl')
    elif not item_image_url and iiko_item.get('picture'):
        item_image_url = iiko_item['picture']
    return item_image_url

def _extract_item_nutrition(iiko_item):
    """Extracts nutrition data from an iiko item."""
    nutrition_data = {
        'calories': 0.0,
        'carbs': 0.0,
        'fat': 0.0,
        'proteins': 0.0
    }
    item_sizes = iiko_item.get('itemSizes', [])
    if item_sizes:
        first_size_nutrition = item_sizes[0].get('nutritionPerHundredGrams')
        if first_size_nutrition:
            nutrition_data['calories'] = float(first_size_nutrition.get('energy', 0.0))
            nutrition_data['carbs'] = float(first_size_nutrition.get('carbs', 0.0))
            nutrition_data['fat'] = float(first_size_nutrition.get('fats', 0.0))
            nutrition_data['proteins'] = float(first_size_nutrition.get('proteins', 0.0))
    return nutrition_data

def _extract_item_ingredients(iiko_item):
    """Extracts ingredients/allergens/tags from an iiko item."""
    ingredients_list = []
    if iiko_item.get('allergens'):
        ingredients_list.extend([a['name'] for a in iiko_item['allergens'] if 'name' in a])
    if iiko_item.get('tags'):
        ingredients_list.extend(iiko_item['tags'])
    if iiko_item.get('labels'):
        ingredients_list.extend(iiko_item['labels'])
    return ingredients_list if ingredients_list else None


def _fetch_and_prepare_iiko_data():
    """
    Fetches raw iiko data and preprocesses it by creating a flat map of all items.
    """
    logger.info("Starting iiko data synchronization...")
    try:
        iiko_data, main_organization_id = get_iiko_menu_data()
    except Exception as e:
        logger.error(f"Failed to fetch data from iiko: {e}. Exiting sync.")
        return None, None, None, None

    if not iiko_data:
        logger.error("Empty data received from iiko. Exiting sync.")
        return None, None, None, None

    iiko_categories_raw = iiko_data.get('itemCategories', [])
    iiko_modifier_groups_raw = iiko_data.get('modifierGroups', [])
    iiko_standalone_items_raw = iiko_data.get('items', [])

    all_iiko_items_by_id = {}
    for category_data in iiko_categories_raw:
        for item_data in category_data.get('items', []):
            item_id = item_data.get('itemId')
            if item_id:
                all_iiko_items_by_id[item_id] = item_data

    for item_data in iiko_standalone_items_raw:
        item_id = item_data.get('itemId')
        if item_id:
            all_iiko_items_by_id[item_id] = item_data

    return iiko_data, iiko_categories_raw, iiko_modifier_groups_raw, all_iiko_items_by_id

def _perform_initial_db_cleanup():
    """
    Marks existing categories and products in the database as hidden
    as a preliminary step for synchronization.
    """
    try:
        db.session.query(Category).update({Category.is_hidden: True})
        db.session.query(Product).update({Product.is_hidden: True})
        db.session.commit()
        logger.info("Marked existing categories and products as hidden for initial cleanup.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during initial cleanup (setting is_hidden): {e}")

def _sync_categories(iiko_categories_raw):
    """
    Synchronizes iiko categories with the local database.
    Returns a map from iiko category ID to local database Category object ID.
    Also identifies the internal DB ID for the recommendation category.
    """
    logger.info("Syncing Categories...")
    existing_categories = {c.iiko_category_id: c for c in Category.query.all()}
    category_iiko_to_db_id_map = {}
    recommendation_category_internal_db_id = None
    recommendation_iiko_id = None

    rec_cat_data = next((c for c in iiko_categories_raw if c.get('name') == RECOMMENDATION_CATEGORY_NAME), None)
    if rec_cat_data:
        recommendation_iiko_id = rec_cat_data['id']

    if recommendation_iiko_id:
        logger.info(f"Identified iiko Recommendation Category ID: {recommendation_iiko_id}")
    else:
        logger.info(f"WARNING: Could not identify iiko Recommendation Category by name '{RECOMMENDATION_CATEGORY_NAME}'. Recommendations won't be synced via category.")

    for iiko_cat in iiko_categories_raw:
        cat_iiko_id = iiko_cat.get('id')
        name = iiko_cat.get('name')
        description = iiko_cat.get('description')
        image_url = iiko_cat.get('buttonImageUrl') or iiko_cat.get('headerImageUrl')
        is_hidden = iiko_cat.get('isHidden', False)

        if not cat_iiko_id or not name:
            logger.info(f"Skipping malformed category data: {iiko_cat}")
            continue

        category = existing_categories.get(cat_iiko_id)
        if category:
            category.name = name
            category.description = description
            category.image_url = image_url
            category.is_hidden = is_hidden
        else:
            category = Category(
                id=cat_iiko_id, # Using iiko_category_id as primary key 'id' if unique
                iiko_category_id=cat_iiko_id,
                name=name,
                description=description,
                image_url=image_url,
                is_hidden=is_hidden,
                icon=icon_map.get(name, "❓"),
                color=color_map.get(name, "from-gray-400 to-gray-600")
            )
            db.session.add(category)
        db.session.flush() # Flush to assign ID if new or make changes available for subsequent checks
        category_iiko_to_db_id_map[cat_iiko_id] = category.id

        if cat_iiko_id == recommendation_iiko_id:
            recommendation_category_internal_db_id = category.id

    db.session.commit()
    logger.info("Categories synced.")
    return category_iiko_to_db_id_map, recommendation_category_internal_db_id, recommendation_iiko_id

def _build_main_category_map():
    """
    Builds a map from iiko category IDs to their corresponding main category IDs in the database.
    """
    iiko_to_main_category_map = {}
    for main_cat_obj in MainCategory.query.all():
        if main_cat_obj.iiko_category_ids:
            for iiko_cid_in_main_cat in main_cat_obj.iiko_category_ids:
                iiko_to_main_category_map[iiko_cid_in_main_cat] = main_cat_obj.id
    logger.info("iiko_to_main_category_map built.")
    return iiko_to_main_category_map

def _process_wok_sauces(iiko_categories_raw):
    """
    Collects additional addons from the 'Sauces' category specifically for the Wok Constructor.
    Returns a list of dictionaries, each representing a ProductAddon relationship to be built later.
    """
    logger.info(f"Adding additional addons from '{SAUCES_CATEGORY_NAME}' category for Wok Constructor.")
    wok_sauce_product_addon_rels = []

    sauces_iiko_cat_id = None
    for iiko_cat in iiko_categories_raw:
        if iiko_cat.get('name') == SAUCES_CATEGORY_NAME:
            sauces_iiko_cat_id = iiko_cat.get('id')
            logger.info(f"Found sauces category {sauces_iiko_cat_id}")
            break

    if sauces_iiko_cat_id:
        sauces_category_data = next((c for c in iiko_categories_raw if c.get('id') == sauces_iiko_cat_id), None)
        if sauces_category_data and sauces_category_data.get('items'):
            for sauce_product_data in sauces_category_data['items']:
                sauce_product_id = sauce_product_data.get('itemId')
                sauce_product_name = sauce_product_data.get('name')

                if not sauce_product_id or not sauce_product_name:
                    logger.warning(f"Skipping malformed sauce product data: {sauce_product_data}")
                    continue

                # Fetch or create Addon
                addon = Addon.query.filter_by(iiko_addon_id=sauce_product_id).first()

                if not addon:
                    sauce_price = _safe_decimal_conversion(
                        sauce_product_data.get('itemSizes', [{}])[0].get('prices', [{}])[0].get('price')
                        if sauce_product_data.get('itemSizes') and sauce_product_data['itemSizes'][0].get('prices') else None,
                        sauce_product_name, sauce_product_id
                    )

                    sauce_image = _extract_item_image_url(sauce_product_data)

                    addon = Addon(
                        id=sauce_product_id,
                        iiko_addon_id=sauce_product_id,
                        group_name=SAUCES_CATEGORY_NAME,
                        name=sauce_product_name,
                        price=sauce_price,
                        image=sauce_image
                    )
                    db.session.add(addon)
                    db.session.flush() # Flush to make the new addon available in the session
                    logger.info(f"Created Addon for sauce: {sauce_product_name} (ID: {addon.id}) with group '{SAUCES_CATEGORY_NAME}'")

                # Link this addon to the Wok Constructor product
                # Note: WOK_PRODUCT_CONSTRUCTOR_ID might not be in product_iiko_to_db_map yet,
                # so we query directly or ensure it's handled in the main product sync.
                # For now, we assume it will exist later when relationships are built.
                wok_constructor_product_obj = Product.query.filter_by(iiko_product_id=WOK_PRODUCT_CONSTRUCTOR_ID).first()
                if wok_constructor_product_obj and addon:
                    # Store relationship in temporary list instead of adding to session immediately
                    wok_sauce_product_addon_rels.append({
                        'product_id': wok_constructor_product_obj.id,
                        'addon_id': addon.id,
                        'product_name': wok_constructor_product_obj.name,
                        'addon_name': addon.name
                    })
                    logger.info(f"Queued linking sauce addon '{addon.name}' to Wok Constructor product '{wok_constructor_product_obj.name}'.")
                else:
                    if not wok_constructor_product_obj:
                        logger.error(f"Wok constructor product (ID: {WOK_PRODUCT_CONSTRUCTOR_ID}) not found when trying to queue sauce addons. Make sure it's synced before this step or handled gracefully.")
                    if not addon:
                        logger.error(f"Sauce addon for product '{sauce_product_name}' (ID: {sauce_product_id}) could not be created/found when queuing.")
        else:
            logger.warning(f"No items found in '{SAUCES_CATEGORY_NAME}' category or category data missing.")
    else:
        logger.warning(f"iiko category '{SAUCES_CATEGORY_NAME}' not found. Cannot add specific sauce addons.")

    logger.info(f"Additional addons from '{SAUCES_CATEGORY_NAME}' processed and relationships queued for later establishment.")
    return wok_sauce_product_addon_rels

def _sync_products_addons_recommendations(iiko_data, iiko_categories_raw, category_iiko_to_db_id_map,
                                          recommendation_category_internal_db_id, recommendation_iiko_id,
                                          iiko_to_main_category_map, all_iiko_items_by_id):
    """
    Synchronizes products, addons, and recommendations from iiko data.
    Populates mappings for later relationship building.
    """
    logger.info("Syncing Products, Addons, and Recommendations...")

    existing_products = {p.iiko_product_id: p for p in Product.query.all()}
    existing_addons = {a.iiko_addon_id: a for a in Addon.query.all()}
    existing_recommendations = {r.iiko_recommendation_id: r for r in Recommendation.query.all()}

    product_iiko_to_db_map = {} # Maps iiko product ID to DB Product object
    addon_iiko_to_db_map = {a.iiko_addon_id: a for a in existing_addons.values()} # Maps iiko addon ID to DB Addon object
    recommendation_iiko_to_db_map = {} # Maps iiko recommendation ID to DB Recommendation object

    product_addon_relationships_to_build = {} # Dict: product_iiko_id -> list of addon_iiko_ids

    # Process items within categories
    for category_data in iiko_categories_raw:
        category_id = category_data.get('id')
        category_db_id = category_iiko_to_db_id_map.get(category_id)

        if not category_db_id:
            logger.info(f"WARNING: Category '{category_data.get('name')}' (iiko ID: {category_id}) not found in DB map. Skipping its items for product/recommendation processing.")
            continue

        for iiko_item in category_data.get('items', []):
            item_iiko_id = iiko_item.get('itemId')
            item_name = iiko_item.get('name')
            item_description = iiko_item.get('description')
            item_type = iiko_item.get('type')
            is_hidden = iiko_item.get('isHidden', False)
            sku = iiko_item.get('sku')
            measure_unit = iiko_item.get('measureUnit')

            if not item_iiko_id or not item_name:
                logger.info(f"Skipping malformed item data in category '{category_data.get('name')}': {iiko_item}")
                continue
            logger.info(f"iiko_item {str(iiko_item)}")
            price_value = _safe_decimal_conversion(
                iiko_item.get('itemSizes', [{}])[0].get('prices', [{}])[0].get('price')
                if iiko_item.get('itemSizes') and iiko_item['itemSizes'][0].get('prices') else None,
                item_name, item_iiko_id
            )
            item_image_url = _extract_item_image_url(iiko_item)
            nutrition_data = _extract_item_nutrition(iiko_item)
            ingredients_list = _extract_item_ingredients(iiko_item)

            is_our_product = False
            is_our_recommendation = False

            if recommendation_category_internal_db_id and category_id == recommendation_iiko_id:
                is_our_recommendation = True
            elif item_type in ['DISH', 'GOODS', 'SERVICE']: # Assuming 'DISH' and 'GOODS' are product types
                is_our_product = True

            if is_our_product:
                product = product_iiko_to_db_map.get(item_iiko_id) or existing_products.get(item_iiko_id)
                is_wok_constructor = (item_iiko_id == WOK_PRODUCT_CONSTRUCTOR_ID)
                corresponding_main_category_id = iiko_to_main_category_map.get(category_id)

                if product:
                    product.name = item_name
                    product.description = item_description
                    product.price = price_value
                    product.image = item_image_url
                    product.categoryId = category_db_id
                    product.main_category_id = corresponding_main_category_id
                    product.nutrition = nutrition_data
                    product.ingredients = ingredients_list
                    product.is_hidden = is_hidden
                    product.sku = sku
                    product.measure_unit = measure_unit
                    product.item_type = item_type
                    product.is_customizable = is_wok_constructor
                else:
                    logger.info(f"Created product {item_name} with id {item_iiko_id}")
                    product = Product(
                        id=item_iiko_id, # Using iiko_product_id as primary key 'id'
                        iiko_product_id=item_iiko_id,
                        name=item_name,
                        description=item_description,
                        price=price_value,
                        image=item_image_url,
                        categoryId=category_db_id,
                        main_category_id=corresponding_main_category_id,
                        nutrition=nutrition_data,
                        ingredients=ingredients_list,
                        is_hidden=is_hidden,
                        sku=sku,
                        measure_unit=measure_unit,
                        item_type=item_type,
                        is_customizable=is_wok_constructor
                    )
                    db.session.add(product)
                db.session.flush()
                product_iiko_to_db_map[item_iiko_id] = product

                # Extract addons directly associated with the product (e.g., from modifiers in the item JSON)
                extracted_addons_data = get_addons_from_iiko_item(iiko_item)
                current_product_addon_ids = set()

                for addon_info in extracted_addons_data:
                    addon_id = addon_info['iiko_addon_id']
                    addon_group_name = addon_info['group_name']
                    addon_name = addon_info['name']
                    addon_price = addon_info['price']
                    addon_image = addon_info['image']

                    addon = addon_iiko_to_db_map.get(addon_id) or existing_addons.get(addon_id)
                    if addon:
                        addon.group_name = addon_group_name
                        addon.name = addon_name
                        addon.price = addon_price
                        addon.image = addon_image
                    else:
                        logger.info(f"Created addon {addon_name} with id {addon_id}")
                        addon = Addon(
                            id=addon_id, # Using iiko_addon_id as primary key 'id'
                            iiko_addon_id=addon_id,
                            group_name=addon_group_name,
                            name=addon_name,
                            price=addon_price,
                            image=addon_image
                        )
                        db.session.add(addon)
                    db.session.flush()
                    addon_iiko_to_db_map[addon_id] = addon
                    current_product_addon_ids.add(addon_id)

                if current_product_addon_ids:
                    # Store relationship to be built after all products/addons are guaranteed to exist
                    product_addon_relationships_to_build[item_iiko_id] = list(current_product_addon_ids)

            elif is_our_recommendation:
                recommendation = recommendation_iiko_to_db_map.get(item_iiko_id) or existing_recommendations.get(item_iiko_id)
                if recommendation:
                    recommendation.name = item_name
                    recommendation.price = price_value
                    recommendation.image = item_image_url
                else:
                    recommendation = Recommendation(
                        id=item_iiko_id, # Using iiko_recommendation_id as primary key 'id'
                        iiko_recommendation_id=item_iiko_id,
                        name=item_name,
                        price=price_value,
                        image=item_image_url
                    )
                    db.session.add(recommendation)
                db.session.flush()
                recommendation_iiko_to_db_map[item_iiko_id] = recommendation

    # Process standalone items from iiko_data.items (often modifiers not explicitly linked in categories)
    for iiko_item in iiko_data.get('items', []):
        item_iiko_id = iiko_item.get('itemId')
        item_name = iiko_item.get('name')
        item_type = iiko_item.get('type')

        # Only process if it's a MODIFIER and not already processed as an addon linked to a product
        if item_type == 'MODIFIER' and item_iiko_id not in addon_iiko_to_db_map:
            price_value = _safe_decimal_conversion(
                iiko_item.get('itemSizes', [{}])[0].get('prices', [{}])[0].get('price')
                if iiko_item.get('itemSizes') and iiko_item['itemSizes'][0].get('prices') else None,
                item_name, item_iiko_id
            )
            item_image_url = _extract_item_image_url(iiko_item)

            addon = existing_addons.get(item_iiko_id)
            if addon:
                addon.group_name = "Ungrouped" # Default group for standalone modifiers
                addon.name = item_name
                addon.price = price_value
                addon.image = item_image_url
            else:
                addon = Addon(
                    id=item_iiko_id, # Using iiko_addon_id as primary key 'id'
                    iiko_addon_id=item_iiko_id,
                    group_name="Ungrouped", # Default group for standalone modifiers
                    name=item_name,
                    price=price_value,
                    image=item_image_url
                )
                db.session.add(addon)
            db.session.flush()
            addon_iiko_to_db_map[item_iiko_id] = addon

    db.session.commit()
    logger.info("Products, Addons, and Recommendations synced. Now setting up relationships.")
    return product_iiko_to_db_map, addon_iiko_to_db_map, recommendation_iiko_to_db_map, product_addon_relationships_to_build

def _clear_existing_relationships():
    """Clears all existing ProductAddon and ProductRecommendation relationships."""
    try:
        db.session.query(ProductAddon).delete()
        db.session.query(ProductRecommendation).delete()
        db.session.commit()
        logger.info("Existing Product-Addon and Product-Recommendation relationships cleared.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing old relationships: {e}")

def _build_product_addon_relationships(product_addon_relationships_to_build, iiko_modifier_groups_raw,
                                       product_iiko_to_db_map, addon_iiko_to_db_map, all_iiko_items_by_id):
    """
    Builds Product-Addon relationships from extracted data and iiko modifier groups.
    """
    logger.info("Building Product-Addon relationships from extracted data...")
    for product_iiko_id, addon_iiko_ids in product_addon_relationships_to_build.items():
        parent_product_obj = product_iiko_to_db_map.get(product_iiko_id)
        if not parent_product_obj:
            logger.warning(f"Product '{product_iiko_id}' not found in DB map for building addon relationships. Skipping.")
            continue

        for addon_iiko_id in addon_iiko_ids:
            addon_obj = addon_iiko_to_db_map.get(addon_iiko_id)
            if not addon_obj:
                logger.warning(f"Addon '{addon_iiko_id}' not found in DB map for product '{parent_product_obj.name}'. This should ideally not happen if get_addons_from_iiko_item works correctly and top-level modifiers are processed.")
                continue

            try:
                # Check for existence before adding to prevent IntegrityError if it already exists from another path
                existing_product_addon = db.session.query(ProductAddon).filter_by(
                    product_id=parent_product_obj.id,
                    addon_id=addon_obj.id
                ).first()
                if not existing_product_addon:
                    product_addon = ProductAddon(
                        product_id=parent_product_obj.id,
                        addon_id=addon_obj.id
                    )
                    db.session.add(product_addon)
            except IntegrityError: # Catching specific error for duplicates
                db.session.rollback()
                logger.warning(f"Duplicate ProductAddon relationship for Product '{parent_product_obj.name}' and Addon '{addon_obj.name}'. Skipping.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding ProductAddon relationship for Product '{parent_product_obj.name}' and Addon '{addon_obj.name}': {e}")

    logger.info("Building Product-Addon relationships from iiko modifierGroups...")
    for iiko_mod_group in iiko_modifier_groups_raw:
        product_iiko_id = iiko_mod_group.get('product')
        parent_product_obj = product_iiko_to_db_map.get(product_iiko_id)

        if not parent_product_obj:
            logger.debug(f"Skipping modifier group for iiko Product ID '{product_iiko_id}' not found in our Products map (might be non-menu item or deleted).")
            continue

        for iiko_modifier_item_ref in iiko_mod_group.get('modifiers', []):
            mod_iiko_id = iiko_modifier_item_ref.get('product')

            addon_obj = addon_iiko_to_db_map.get(mod_iiko_id)

            if not addon_obj:
                logger.warning(f"Addon '{mod_iiko_id}' referenced in modifier group for product '{parent_product_obj.name}' but not found in our Addon map. Attempting to create it from all_iiko_items_by_id.")
                full_mod_item_data = all_iiko_items_by_id.get(mod_iiko_id)

                if full_mod_item_data:
                    # Determine group_name from modifierGroup if available, else default
                    mod_group_name = iiko_mod_group.get('name') or "Ungrouped"
                    mod_name = full_mod_item_data.get('name')

                    mod_price = _safe_decimal_conversion(
                        full_mod_item_data.get('itemSizes', [{}])[0].get('prices', [{}])[0].get('price')
                        if full_mod_item_data.get('itemSizes') and full_mod_item_data['itemSizes'][0].get('prices') else None,
                        mod_name, mod_iiko_id
                    )
                    mod_image = _extract_item_image_url(full_mod_item_data)

                    addon_obj = Addon(
                        id=mod_iiko_id,
                        iiko_addon_id=mod_iiko_id,
                        group_name=mod_group_name,
                        name=mod_name,
                        price=mod_price,
                        image=mod_image
                    )
                    db.session.add(addon_obj)
                    db.session.flush()
                    addon_iiko_to_db_map[mod_iiko_id] = addon_obj
                    logger.info(f"Created Addon '{mod_name}' (ID: {mod_iiko_id}) and added to map from modifier group reference.")
                else:
                    logger.error(f"ERROR: Could not find full data for Addon '{mod_iiko_id}' referenced in modifier group. Skipping relationship for product '{parent_product_obj.name}'.")
                    continue

            try:
                existing_product_addon = db.session.query(ProductAddon).filter_by(
                    product_id=parent_product_obj.id,
                    addon_id=addon_obj.id
                ).first()
                if not existing_product_addon:
                    product_addon = ProductAddon(
                        product_id=parent_product_obj.id,
                        addon_id=addon_obj.id
                    )
                    db.session.add(product_addon)
                else:
                    logger.debug(f"ProductAddon relationship already exists for Product '{parent_product_obj.name}' and Addon '{addon_obj.name}'. Skipping.")

            except IntegrityError:
                db.session.rollback()
                logger.warning(f"Duplicate ProductAddon relationship for Product '{parent_product_obj.name}' and Addon '{addon_obj.name}'. Skipping due to IntegrityError.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding ProductAddon relationship for Product '{parent_product_obj.name}' (ID: {parent_product_obj.id}) and Addon '{addon_obj.id}' (ID: {addon_obj.id}): {e}")

def _add_queued_wok_sauce_relationships(wok_sauce_product_addon_rels):
    """Adds the previously queued Wok-Sauce relationships to the database."""
    logger.info("Adding queued Wok-Sauce relationships.")
    for rel_data in wok_sauce_product_addon_rels:
        try:
            # We need to re-check existence here because the delete() operation cleared them
            existing_product_addon = db.session.query(ProductAddon).filter_by(
                product_id=rel_data['product_id'],
                addon_id=rel_data['addon_id']
            ).first()
            if not existing_product_addon:
                product_addon = ProductAddon(
                    product_id=rel_data['product_id'],
                    addon_id=rel_data['addon_id']
                )
                db.session.add(product_addon)
                logger.info(f"Re-added Wok-Sauce link: Product '{rel_data['product_name']}' <-> Addon '{rel_data['addon_name']}'.")
            else:
                logger.debug(f"Wok-Sauce relationship already exists for Product '{rel_data['product_name']}' and Addon '{rel_data['addon_name']}'. Skipping re-add.")
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Duplicate Wok-Sauce relationship for Product '{rel_data['product_name']}' and Addon '{rel_data['addon_name']}'. Skipping due to IntegrityError during re-add.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error re-adding Wok-Sauce relationship for Product '{rel_data['product_name']}' (ID: {rel_data['product_id']}) and Addon '{rel_data['addon_name']}' (ID: {rel_data['addon_id']}): {e}")

def _sync_product_recommendation_relationships(product_iiko_to_db_map, recommendation_iiko_to_db_map):
    """
    Synchronizes Product-Recommendation relationships by linking all products to all recommendations.
    """
    # Sync Recommendations (linking all products to all recommendations)
    all_products_db_objects = list(product_iiko_to_db_map.values())
    all_recommendations_db_objects = list(recommendation_iiko_to_db_map.values())

    for product_obj in all_products_db_objects:
        for rec_obj in all_recommendations_db_objects:
            try:
                existing_product_recommendation = db.session.query(ProductRecommendation).filter_by(
                    product_id=product_obj.id,
                    recommendation_id=rec_obj.id
                ).first()
                if not existing_product_recommendation:
                    product_recommendation = ProductRecommendation(
                        product_id=product_obj.id,
                        recommendation_id=rec_obj.id
                    )
                    db.session.add(product_recommendation)
                else:
                    logger.debug(f"ProductRecommendation relationship already exists for Product '{product_obj.name}' and Recommendation '{rec_obj.name}'. Skipping.")
            except IntegrityError:
                db.session.rollback()
                logger.warning(f"Duplicate ProductRecommendation relationship for Product '{product_obj.name}' and Recommendation '{rec_obj.name}'. Skipping due to IntegrityError.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding ProductRecommendation relationship for Product '{product_obj.name}' (ID: {product_obj.id}) and Recommendation '{rec_obj.id}' (ID: {rec_obj.id}): {e}")

def synchronize_iiko_data():
    """
    Main function to synchronize iiko menu data with the local database.
    This function orchestrates calls to smaller, logical functions.
    """
    # Step 1: Fetch and Prepare Data
    iiko_data, iiko_categories_raw, iiko_modifier_groups_raw, all_iiko_items_by_id = _fetch_and_prepare_iiko_data()
    if not iiko_data:
        return # Exit if initial data fetch fails or is empty

    # Step 2: Initial DB Cleanup
    _perform_initial_db_cleanup()

    # Step 3: Sync Categories
    category_iiko_to_db_id_map, recommendation_category_internal_db_id, recommendation_iiko_id = _sync_categories(iiko_categories_raw)

    # Step 4: Build Main Category Map (assumes MainCategory data is static or synced elsewhere)
    iiko_to_main_category_map = _build_main_category_map()

    # Step 5: Process Wok Constructor Sauces (queues relationships)
    wok_sauce_product_addon_rels = _process_wok_sauces(iiko_categories_raw)

    # Step 6: Sync Products, Addons, and Recommendations
    # This step also populates product_iiko_to_db_map, addon_iiko_to_db_map,
    # recommendation_iiko_to_db_map, and product_addon_relationships_to_build (from item modifiers)
    product_iiko_to_db_map, addon_iiko_to_db_map, recommendation_iiko_to_db_map, product_addon_relationships_to_build = \
        _sync_products_addons_recommendations(iiko_data, iiko_categories_raw, category_iiko_to_db_id_map,
                                              recommendation_category_internal_db_id, recommendation_iiko_id,
                                              iiko_to_main_category_map, all_iiko_items_by_id)

    # Step 7: Clear and Rebuild Relationships
    _clear_existing_relationships()

    # Step 8: Build Product-Addon relationships (from item modifiers and modifier groups)
    _build_product_addon_relationships(product_addon_relationships_to_build, iiko_modifier_groups_raw,
                                       product_iiko_to_db_map, addon_iiko_to_db_map, all_iiko_items_by_id)

    # Step 9: Add Queued Wok-Sauce Relationships
    _add_queued_wok_sauce_relationships(wok_sauce_product_addon_rels)

    # Step 10: Sync Product-Recommendation relationships
    _sync_product_recommendation_relationships(product_iiko_to_db_map, recommendation_iiko_to_db_map)

    db.session.commit() # Final commit for all relationship changes
    logger.info("Relationships synced.")

    logger.info("Data synchronization complete.")
