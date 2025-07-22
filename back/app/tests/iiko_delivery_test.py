import requests
import os
import time
import json
from datetime import datetime, timedelta
import uuid
import logging
from typing import List
from diskcache import Cache # Import Cache from diskcache

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

IIKO_API_URL = "https://api-ru.iiko.services"
IIKO_API_TOKEN = os.getenv("IIKO_API_TOKEN")

# Disk Cache configuration
CACHE_DIR = "iiko_api_cache_data" # Directory to store cache files
cache = Cache(CACHE_DIR)

# Cache expiration times
TOKEN_CACHE_KEY = "iiko_access_token"
TOKEN_EXPIRATION_SECONDS = 14 * 60 # Token is valid for 15 mins, refresh slightly before
DATA_CACHE_EXPIRATION_SECONDS = 24 * 60 * 60 # 24 hours for other data

# Global cache (from original script, kept for context, but now handled by diskcache)
# CACHE = {"timestamp": 0, "menu": None, "tables": None}
# CACHE_EXPIRATION = 900

def get_access_token():
    """
    Получить токен доступа для работы с iiko API, используя кэш.
    Токен кэшируется на 14 минут для избежания частых запросов.
    """
    cached_info = cache.get(TOKEN_CACHE_KEY)
    if cached_info:
        cached_token, timestamp = cached_info
        if (time.time() - timestamp) < TOKEN_EXPIRATION_SECONDS:
            logger.info("Возвращаем токен доступа из кэша.")
            return cached_token

    # Если токена нет в кэше или он устарел, получаем новый
    url = f"{IIKO_API_URL}/api/1/access_token"
    payload = {"apiLogin": IIKO_API_TOKEN}
    logger.info(f"Получаем новый токен доступа с URL: {url}")
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        token = response.json().get("token")
        if token:
            logger.info("Новый токен успешно получен и кэширован.")
            # Кэшируем токен на время, чуть большее его фактического срока действия, чтобы избежать гонки
            cache.set(TOKEN_CACHE_KEY, (token, time.time()), expire=TOKEN_EXPIRATION_SECONDS + 60)
            return token
        else:
            logger.error(f"Ошибка: Токен не найден в ответе. Ответ: {response.text}")
            raise Exception("Токен не получен.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения токена: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.response.text}")
        raise

def get_organizations(token):
    """
    Получить список организаций, используя кэш.
    Кэшируется на 24 часа.
    """
    cache_key = "organizations_data"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info("Возвращаем организации из кэша.")
        return cached_data

    url = f"{IIKO_API_URL}/api/1/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": []}
    logger.info(f"Получаем новые организации с URL: {url}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        organizations = response.json().get("organizations", [])
        logger.info("Новые организации получены и кэшированы.")
        cache.set(cache_key, organizations, expire=DATA_CACHE_EXPIRATION_SECONDS)
        return organizations
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения организаций: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.response.text}")
        raise

def get_cities(token, organization_ids: List[str]):
    """
    Получить список городов для указанных организаций, используя кэш.
    Кэшируется на 24 часа.
    """
    # Ключ кэша должен зависеть от organization_ids, так как данные могут различаться
    cache_key = f"cities_{'_'.join(sorted(organization_ids))}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Возвращаем города для {organization_ids} из кэша.")
        return cached_data

    url = f"{IIKO_API_URL}/api/1/cities"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": organization_ids}
    logger.info(f"Получаем новые города для {organization_ids} с URL: {url}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        cities = response.json().get("cities", [])
        logger.info(f"Новые города для {organization_ids} получены и кэшированы.")
        cache.set(cache_key, cities, expire=DATA_CACHE_EXPIRATION_SECONDS)
        return cities
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения городов: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.text}")
        raise

def get_streets_by_city(token, organization_id: str, city_id: str):
    """
    Получить список улиц для указанного города и организации, используя кэш.
    Кэшируется на 24 часа.
    """
    cache_key = f"streets_{organization_id}_{city_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Возвращаем улицы для города {city_id} из кэша.")
        return cached_data

    url = f"{IIKO_API_URL}/api/1/streets/by_city"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationId": organization_id, "cityId": city_id}
    logger.info(f"Получаем новые улицы для города {city_id} с URL: {url}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        streets = response.json().get("streets", [])
        logger.info(f"Новые улицы для города {city_id} получены и кэшированы.")
        cache.set(cache_key, streets, expire=DATA_CACHE_EXPIRATION_SECONDS)
        return streets
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения улиц: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.text}")
        raise

def get_menu(token):
    """
    Получить номенклатуру (меню) для конкретной организации, используя кэш.
    Кэшируется на 24 часа.
    """
    cache_key = "menu_data"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info("Возвращаем меню из кэша.")
        return cached_data

    url = f"{IIKO_API_URL}/api/2/menu"
    headers = {"Authorization": f"Bearer {token}"}
    logger.info(f"Получаем новое меню с URL: {url}")
    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info("Новое меню получено и кэшировано.")
        cache.set(cache_key, data, expire=DATA_CACHE_EXPIRATION_SECONDS)
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения меню: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.text}")
        raise

def get_menu_by_id(organization_id, menu_id, token):
    """
    Получить номенклатуру (меню) для конкретной организации по ID меню, используя кэш.
    Кэшируется на 24 часа.
    """
    cache_key = f"menu_by_id_{organization_id}_{menu_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Возвращаем меню по ID {menu_id} из кэша.")
        return cached_data

    url = f"{IIKO_API_URL}/api/2/menu/by_id"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"externalMenuId": menu_id, "organizationIds": [organization_id]}
    logger.info(f"Получаем новое меню по ID {menu_id} с URL: {url} с payload: {json.dumps(payload)}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Новое меню по ID {menu_id} получено и кэшировано.")
        cache.set(cache_key, data, expire=DATA_CACHE_EXPIRATION_SECONDS)
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения меню по ID: {e}")
        if e.response:
            logger.error(f"Ответ API: {e.text}")
        raise

def create_delivery_order_test(token, payload):
    """
    Отправить тестовый payload для создания заказа на доставку в iiko.
    Эта функция не кэшируется, так как создает новый ресурс.
    """
    url = f"{IIKO_API_URL}/api/1/deliveries/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    logger.info(f"\n--- Отправка тестового заказа на доставку ---")
    logger.info(f"URL: {url}")
    logger.info(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"\n--- Успешный ответ от IIKO API ---")
        logger.info(f"Response:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
        return response_json
    except requests.exceptions.RequestException as e:
        logger.error(f"\n--- Ошибка при создании заказа на доставку в IIKO ---")
        logger.error(f"Ошибка: {e}")
        if e.response is not None:
            logger.error(f"IIKO API Response content: {e.response.text}")
        raise

if __name__ == '__main__':
    try:
        # Ensure the cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)

        token = get_access_token()
        logger.info(f"\nПолученный токен: {token}")

        organizations = get_organizations(token)
        if organizations:
            organization_id = organizations[0]["id"]
            logger.info(f"Получена первая организация: ID={organization_id}, Name={organizations[0]['name']}")
        else:
            logger.error("Не удалось получить организации или список организаций пуст. Завершение работы.")
            exit()

        # --- Динамическое получение города и улицы ---
        selected_city_id = None
        selected_city_name = None
        selected_street_id = None
        selected_street_name = None

        logger.info("Попытка получить список городов...")
        cities_data = get_cities(token, [organization_id])
        if cities_data:
            org_cities_list = next((org_data.get('items') for org_data in cities_data if org_data.get('organizationId') == organization_id), [])
            if org_cities_list:
                selected_city_id = org_cities_list[0]['id']
                selected_city_name = org_cities_list[0]['name']
                logger.info(f"Выбран первый доступный город: ID={selected_city_id}, Name='{selected_city_name}'")

                logger.info(f"Попытка получить улицы для города '{selected_city_name}'...")
                streets_data = get_streets_by_city(token, organization_id, selected_city_id)
                if streets_data:
                    selected_street_id = streets_data[0]['id']
                    selected_street_name = streets_data[0]['name']
                    logger.info(f"Выбрана первая доступная улица: ID={selected_street_id}, Name='{selected_street_name}'")
                else:
                    logger.warning(f"Не удалось получить улицы для города '{selected_city_name}' или список улиц пуст. Используем тестовые данные для улицы.")
                    selected_street_id = str(uuid.uuid4()) # Dummy ID
                    selected_street_name = "ТЕСТОВАЯ УЛИЦА"
            else:
                logger.warning("Не удалось найти города для выбранной организации. Используем тестовые данные для города и улицы.")
                selected_city_id = str(uuid.uuid4()) # Dummy ID
                selected_city_name = "ТЕСТОВЫЙ ГОРОД"
                selected_street_id = str(uuid.uuid4()) # Dummy ID
                selected_street_name = "ТЕСТОВАЯ УЛИЦА"
        else:
            logger.warning("Не удалось получить список городов. Используем тестовые данные для города и улицы.")
            selected_city_id = str(uuid.uuid4()) # Dummy ID
            selected_city_name = "ТЕСТОВЫЙ ГОРОД"
            selected_street_id = str(uuid.uuid4()) # Dummy ID
            selected_street_name = "ТЕСТОВАЯ УЛИЦА"

        # --- Тестовый payload для заказа на доставку ---
        test_delivery_payload = {
            "organizationId": organization_id,
            "terminalGroupId": "b20e5ffc-3e20-abc7-018e-eaf32ff70064",
            "order": {
                "id": str(uuid.uuid4()),
                "externalNumber": f"WEB-{str(uuid.uuid4())[:8]}",
                "phone": "+79999999999",
                "orderServiceType": "DeliveryByCourier", # Added orderServiceType
                "items": [
                    {
                        "type": "Product",
                        "productId": "859b7336-83a8-4fa0-80c9-62681ffeb8e4",
                        "productCode": "859b7336-83a8-4fa0-80c9-62681ffeb8e4",
                        "name": "Собери свою коробочку ",
                        "amount": 1,
                        "price": 0.0,
                        "modifiers": [
                            {
                                "productId": "109506d2-d18b-4787-a762-343b7ab3f28d", # Changed "id" to "productId"
                                "type": "Product",
                                "amount": 1
                            },
                            {
                                "productId": "1516b91a-6852-4829-8d5e-a8b69dfddf48", # Changed "id" to "productId"
                                "type": "Product",
                                "amount": 1
                            },
                            {
                                "productId": "898a9cdf-f578-4355-9fd0-1430dbbeea6e", # Changed "id" to "productId"
                                "type": "Product",
                                "amount": 1
                            }
                        ],
                        "comboId": None,
                        "positionId": str(uuid.uuid4())
                    },
                    {
                        "type": "Product",
                        "productId": "2d36623b-0e2d-4cf1-bd9a-196fe13da4d7",
                        "productCode": "2d36623b-0e2d-4cf1-bd9a-196fe13da4d7",
                        "name": "Доставка 100",
                        "amount": 1,
                        "price": 0.0,
                        "modifiers": [],
                        "comboId": None,
                        "positionId": str(uuid.uuid4())
                    }
                ],
                "deliveryPoint": {
                    "address": {
                        "street": {
                            "id": selected_street_id,
                            "name": selected_street_name
                        },
                        "city": {
                            "id": selected_city_id,
                            "name": selected_city_name
                        },
                        "house": "1",
                        "building": "1",
                        "index": "123456",
                        "line1": "Дополнительная информация по адресу",
                        "entrance": "1"
                    },
                    "coordinates": {
                        "latitude": 56.0167,
                        "longitude": 38.3833
                    }
                },
                "payments": [
                    {
                        "sum": 0.0,
                        "paymentTypeKind": "Cash",
                        "paymentTypeId": "09322f46-578a-d210-add7-eec222a08871",
                        "isProcessedExternally": False,
                        "isFiscalizedExternally": False,
                        "isPrepay": False
                    }
                ],
                "comment": "ТЕСТОВЫЙ ЗАКАЗ. НЕ ОБРАБАТЫВАТЬ.",
                "completeBefore": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            },
            "createOrderSettings": {
                "transportToFrontTimeout": 0
            }
        }

        create_delivery_order_test(token, test_delivery_payload)

    except Exception as e:
        logger.error(f"\nПроизошла критическая ошибка: {e}", exc_info=True)
