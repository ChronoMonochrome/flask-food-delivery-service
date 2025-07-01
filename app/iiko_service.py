import requests
import os
from dotenv import load_dotenv
from app.models import db, Category, Product, Addon, Recommendation, ProductAddon, ProductRecommendation, OrderItem
import diskcache as dc # Import diskcache

# Load environment variables from .env file (important for both app and standalone scripts)
load_dotenv()

IIKO_API_URL = os.getenv("IIKO_API_URL")
IIKO_API_TOKEN = os.getenv("IIKO_API_TOKEN")

# --- Cache Configuration ---
# Set the cache directory relative to the current script's location,
# placing it in the project root (.cache folder)
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache")

# Get expiration from environment variable, default to -1 (no expiration)
# Convert to integer, ensuring robustness against invalid input
try:
    CACHE_EXPIRATION_MINUTES = int(os.getenv("IIKO_CACHE_EXPIRATION_MINUTES", "-1"))
except ValueError:
    print("Warning: IIKO_CACHE_EXPIRATION_MINUTES is not a valid integer. Defaulting to -1 (no expiration).")
    CACHE_EXPIRATION_MINUTES = -1

CACHE_EXPIRATION_SECONDS = None
if CACHE_EXPIRATION_MINUTES != -1:
    CACHE_EXPIRATION_SECONDS = CACHE_EXPIRATION_MINUTES * 60

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize diskcache
cache = dc.Cache(CACHE_DIR)

# Assuming logger is set up in app/logger.py and imported in app/__init__.py
# For standalone testing, you might need a basic print or logging setup here.
try:
    from app.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- API Functions with Caching ---

@cache.memoize(expire=CACHE_EXPIRATION_SECONDS, tag='iiko_token')
def get_access_token():
    """
    Получить токен доступа для работы с iiko API.
    """
    logger.info("Attempting to get iiko access token (checking cache first)...")
    if not IIKO_API_URL or not IIKO_API_TOKEN:
        raise ValueError("IIKO_API_URL or IIKO_API_TOKEN not set in environment variables.")

    url = f"{IIKO_API_URL}/api/1/access_token"
    payload = {"apiLogin": IIKO_API_TOKEN}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        token = response.json().get("token")
        logger.info("iiko access token obtained (fresh from API and cached).")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting iiko token: {e}", exc_info=True)
        raise Exception(f"Ошибка получения токена: {e}")
    except ValueError as e:
        logger.error(f"Error parsing iiko token JSON response: {e}, Response: {response.text}", exc_info=True)
        raise Exception(f"Ошибка парсинга JSON ответа токена: {e}, Ответ: {response.text}")


@cache.memoize(expire=CACHE_EXPIRATION_SECONDS, tag='iiko_organizations')
def get_organizations(token):
    """
    Получить список организаций.
    """
    logger.info("Attempting to get iiko organizations (checking cache first)...")
    url = f"{IIKO_API_URL}/api/1/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": []} # Request all accessible organizations
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        organizations = response.json().get("organizations", [])
        if not organizations:
            logger.warning("No organizations found for the API token.")
            raise Exception("Не найдено организаций по токену API.")
        logger.info("iiko organizations obtained (fresh from API and cached).")
        return organizations
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting iiko organizations: {e}", exc_info=True)
        raise Exception(f"Ошибка получения организаций: {e}")
    except ValueError as e:
        logger.error(f"Error parsing iiko organizations JSON response: {e}, Response: {response.text}", exc_info=True)
        raise Exception(f"Ошибка парсинга JSON ответа организаций: {e}, Ответ: {response.text}")

@cache.memoize(expire=CACHE_EXPIRATION_SECONDS, tag='iiko_menu')
def get_menu_from_iiko(organization_id, token):
    """
    Получить номенклатуру (меню) для конкретной организации из iiko API.
    """
    logger.info(f"Attempting to get iiko menu for org {organization_id} (checking cache first)...")
    url = f"{IIKO_API_URL}/api/1/nomenclature"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationId": organization_id}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30) # Increased timeout for menu
        response.raise_for_status()
        menu_data = response.json()
        logger.info(f"iiko menu obtained for org {organization_id} (fresh from API and cached).")
        return menu_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting iiko menu: {e}", exc_info=True)
        raise Exception(f"Ошибка получения меню из iiko: {e}")
    except ValueError as e:
        logger.error(f"Error parsing iiko menu JSON response: {e}, Response: {response.text}", exc_info=True)
        raise Exception(f"Ошибка парсинга JSON ответа меню: {e}, Ответ: {response.text}")

# --- Main Synchronization Function ---
def synchronize_iiko_data():
    """
    Основная функция для синхронизации данных из iiko в базу данных.
    Это функция всегда полностью очищает БД перед загрузкой новых данных.
    """
    # Список категорий-аддонов
    addons_categories = ["Сосиска на выбор", "Добавки к пицце", "Начинка", "Сыр", "Спайси", "Донер на выбор", "Мясо", "Дополнительный соус", "Мясные допы", "Допы горячий цех"]
    logger.info("Начало синхронизации данных с iiko (режим полной перезаписи)...")
    try:
        token = get_access_token() # This call will now use the cache
        logger.info("Токен iiko получен.")
        organizations = get_organizations(token) # This call will now use the cache
        if not organizations:
            logger.warning("Не найдено организаций для синхронизации.")
            return

        organization_id = organizations[0]["id"]
        logger.info(f"Синхронизация для организации ID: {organization_id} ({organizations[0]['name']})")

        iiko_menu_data = get_menu_from_iiko(organization_id, token) # This call will now use the cache
        logger.info("Данные меню из iiko получены.")

        # Always clear existing data
        logger.info("Очистка существующих данных в базе данных...")
        # IMPORTANT: Delete child records first to satisfy foreign key constraints
        db.session.query(OrderItem).delete(synchronize_session='fetch')
        db.session.query(ProductAddon).delete(synchronize_session='fetch')
        db.session.query(ProductRecommendation).delete(synchronize_session='fetch')
        db.session.query(Product).delete(synchronize_session='fetch')
        db.session.query(Category).delete(synchronize_session='fetch')
        db.session.query(Addon).delete(synchronize_session='fetch')
        db.session.query(Recommendation).delete(synchronize_session='fetch')
        db.session.commit()
        logger.info("Существующие данные очищены.")

        # Maps to hold newly created/updated objects
        db_categories_map = {}
        db_addons_map = {}
        db_recommendations_map = {}
        db_products_map = {}

        # --- Process Groups (Categories, Addons, Recommendations) ---
        iiko_groups = {g["id"]: g for g in iiko_menu_data.get("groups", [])}

        for group_id, group_data in iiko_groups.items():
            group_id_str = str(group_id)
            group_name = group_data["name"]

            icon_map = {
                "Бургеры": "🍔", "Пицца": "🍕", "Суши": "🍣", "Салаты": "🥗",
                "Десерты": "🍰", "Напитки": "🥤", "Закуски": "🍟", "Горячие блюда": "🍲",
                "Вок": "🍜", "Кальцоне": "🍕", "Ламаджо": "🍖", "Осетинские пироги": "🥧",
                "Паста": "🍝", "Роллы": "🍣", "Сеты": "🍱", "Супы": "🥣",
                "Фокаччо": "🍞", "Хачапури": "🧀", "Хот-доги и донер": "🌭",
                "Мясо": "🥩", "Начинка": "🌶️", "Дополнительный соус": "🧂", "Лапша": "🍜",
                "Донер на выбор": "🥙", "Сосиска на выбор": "🌭", "Рыба и морепродукты": "🦐",
                "Сыр": "🧀", "Допы горячий цех": "🔥", "Роллы маки": "🍣", "Спайси": "🌶️",
                "Суши Гунканы": "🍣", "Рулетики": "🌯", "Соусы": "🥣", "Фаст роллы": "🌯",
                "По-имеретински": "🥧", "Хачапури": "🧀", "Начинка": "🧅", "Дополнительный соус": "🥫",
                "Донер на выбор": "🥙", "Сосиска на выбор": "🌭", "Горячие роллы": "🔥🍣",
                "Запеченные роллы": "♨️🍣", "Нигири": "🍣", "Онигири": "🍙",
                "КАФЕ ПИЦЦА 35см": "🍕", "КАФЕ ПИЦЦА РИМСКАЯ": "🍕", "Пицца 35 см.": "🍕",
                "Пицца Неаполитано 24 см": "🍕", "Пицца Чикаго 29 см": "🍕", "Римская пицца": "🍕"
            }
            color_map = {
                "Бургеры": "from-yellow-400 to-orange-500", "Пицца": "from-red-400 to-red-600",
                "Суши": "from-blue-400 to-purple-500", "Салаты": "from-green-400 to-lime-500",
                "Десерты": "from-pink-400 to-rose-500", "Напитки": "from-teal-400 to-cyan-500",
                "Закуски": "from-amber-400 to-yellow-600", "Горячие блюда": "from-orange-500 to-red-700",
                "Вок": "from-purple-400 to-fuchsia-500", "Кальцоне": "from-red-500 to-pink-600",
                "Ламаджо": "from-amber-500 to-orange-700", "Осетинские пироги": "from-yellow-500 to-lime-600",
                "Паста": "from-red-300 to-red-500", "Роллы": "from-blue-300 to-indigo-500",
                "Сеты": "from-pink-500 to-purple-600", "Супы": "from-emerald-400 to-cyan-600",
                "Фокаччо": "from-yellow-600 to-orange-700", "Хачапури": "from-lime-500 to-green-600",
                "Хот-доги и донер": "from-orange-400 to-red-500",
                "Мясо": "from-red-700 to-pink-800", "Начинка": "from-green-500 to-lime-700",
                "Дополнительный соус": "from-gray-300 to-gray-500", "Лапша": "from-purple-500 to-indigo-600",
                "Донер на выбор": "from-yellow-700 to-orange-800", "Сосиска на выбор": "from-red-600 to-red-800",
                "Рыба и морепродукты": "from-blue-500 to-cyan-600", "Сыр": "from-yellow-300 to-yellow-500",
                "Допы горячий цех": "from-red-400 to-red-600", "Роллы маки": "from-blue-400 to-indigo-600",
                "Спайси": "from-orange-500 to-red-600", "Суши Гунканы": "from-purple-400 to-fuchsia-500",
                "Рулетики": "from-amber-400 to-orange-500", "Соусы": "from-gray-500 to-gray-700",
                "Фаст роллы": "from-lime-400 to-green-500", "По-имеретински": "from-brown-400 to-orange-600",
                "КАФЕ ПИЦЦА 35см": "from-orange-400 to-red-500", "КАФЕ ПИЦЦА РИМСКАЯ": "from-red-500 to-pink-600",
                "Пицца 35 см.": "from-orange-400 to-red-500", "Пицца Неаполитано 24 см": "from-red-500 to-pink-600",
                "Пицца Чикаго 29 см": "from-orange-400 to-red-500", "Римская пицца": "from-red-500 to-pink-600"
            }

            # Heuristic for addons
            if group_name in addons_categories:
                addon = Addon(
                    iiko_addon_id=group_id,
                    name=group_name,
                    price=0.0 # Price for group is irrelevant here
                )
                db.session.add(addon)
                db_addons_map[group_id_str] = addon
                logger.debug(f"Добавлен аддон-группа: {group_name}")
            # Heuristic for recommendations (if specific group name for them)
            # Example: if "Рекомендации" in group_name.lower():
            #   recommendation = Recommendation(iiko_recommendation_id=group_id, name=group_name, price=0.0)
            #   db.session.add(recommendation)
            #   db_recommendations_map[group_id_str] = recommendation
            #   logger.debug(f"Добавлена рекомендация-группа: {group_name}")
            else: # Treat as regular category
                category = Category(
                    iiko_category_id=group_id,
                    name=group_name,
                    icon=icon_map.get(group_name, "❓"), # Default icon if not found
                    color=color_map.get(group_name, "from-gray-400 to-gray-600") # Default color
                )
                db.session.add(category)
                db_categories_map[group_id_str] = category
                logger.debug(f"Добавлена категория: {group_name}")
        db.session.commit() # Commit after categories/addons to ensure they have IDs for product linking
        logger.info("Категории, Допы и Рекомендации (группы) обработаны.")

        # --- Process Products ---
        iiko_products = iiko_menu_data.get("products", [])

        for product_data in iiko_products:
            iiko_product_id = product_data["id"]
            iiko_product_id_str = str(iiko_product_id)
            product_name = product_data["name"]
            product_description = product_data.get("description", "")

            size_prices = product_data.get("sizePrices", [])
            price = size_prices[0]["price"]["currentPrice"] if size_prices else 0.0

            image_links = product_data.get("imageLinks", [])
            image_url = image_links[0] if image_links else None

            iiko_parent_group_id = product_data.get("parentGroup")
            iiko_parent_group_id_str = str(iiko_parent_group_id) if iiko_parent_group_id else None

            # Check if this product should be treated as an Addon (item) or Recommendation (item) itself
            if iiko_parent_group_id_str in db_addons_map:
                addon = Addon(
                    iiko_addon_id=iiko_product_id, # Use product's iiko_id for the addon item
                    name=product_name,
                    price=price,
                    image=image_url
                )
                db.session.add(addon)
                db_addons_map[iiko_product_id_str] = addon # Store with product's iiko ID
                logger.debug(f"Добавлен новый элемент-аддон: {product_name}")
                continue # Don't process as a regular product

            # Similar logic for products that are recommendations themselves.
            # You might have a specific iiko group for 'recommended products'
            # For now, we'll assume a recommendation is either a group (already handled)
            # or a regular product that gets linked below.

            # If not an addon, process as a regular product
            category = db_categories_map.get(iiko_parent_group_id_str)
            if not category:
                logger.warning(f"Предупреждение: Продукт '{product_name}' (ID: {iiko_product_id}) имеет неизвестную родительскую группу ID: {iiko_parent_group_id}. Пропуск.")
                continue

            product = Product(
                iiko_product_id=iiko_product_id,
                name=product_name,
                description=product_description,
                price=price,
                image=image_url,
                categoryId=category.id,
                nutrition={}, # iiko doesn't provide this directly in nomenclature, leave empty
                ingredients=[] # iiko doesn't provide this directly, leave empty
            )
            db.session.add(product)
            db_products_map[iiko_product_id_str] = product # Store for later linking of junction tables
            logger.debug(f"Добавлен продукт: {product_name}")

        db.session.commit()
        logger.info("Продукты обработаны.")

        # --- Link Products to Addons/Recommendations ---
        # Re-establish links for all current products. This is a general linking approach.
        # If iiko provides specific product-modifier links, you'd integrate that here.

        # Example: Link all main products to "Соевый соус" as an addon (if it exists)
        soy_sauce_addon = Addon.query.filter_by(name="Соевый соус").first() # Assuming name is unique for common addons

        # Example: Let's assume a general recommendation like "Кола 0.5л"
        coke_rec_item = Recommendation.query.filter_by(name="Кола 0.5л").first()
        # If "Кола 0.5л" is a product that you want to *recommend*, and it's not yet a Recommendation item, create it.
        coke_product_for_rec = Product.query.filter_by(name="Кола 0.5л").first()
        if coke_product_for_rec and not coke_rec_item:
            coke_rec_item = Recommendation(
                iiko_recommendation_id=coke_product_for_rec.iiko_product_id, # Use product's iiko ID as recommendation ID
                name=coke_product_for_rec.name,
                price=coke_product_for_rec.price,
                image=coke_product_for_rec.image
            )
            db.session.add(coke_rec_item)
            db.session.commit() # Commit to get its ID before linking
            logger.info(f"Created new Recommendation entry for product: {coke_product_for_rec.name}")

        for db_product in db_products_map.values():
            # Link common addons
            if soy_sauce_addon:
                db.session.add(ProductAddon(product=db_product, addon=soy_sauce_addon))
                logger.debug(f"Linked {db_product.name} to {soy_sauce_addon.name} addon.")

            # Link common recommendations
            if coke_rec_item:
                db.session.add(ProductRecommendation(product=db_product, recommendation=coke_rec_item))
                logger.debug(f"Linked {db_product.name} to {coke_rec_item.name} recommendation.")

        db.session.commit()
        logger.info("Продукты успешно связаны с аддонами/рекомендациями.")


        logger.info("Синхронизация данных с iiko завершена успешно.")

    except Exception as e:
        db.session.rollback() # Rollback all changes on error
        logger.error(f"Ошибка при синхронизации данных с iiko: {e}", exc_info=True) # Log full traceback
        raise # Re-raise the exception to propagate it