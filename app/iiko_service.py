import requests
from app.logger import logger
from app.models import db, Category, Product, Addon, Recommendation, ProductAddon, ProductRecommendation
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os

from dotenv import load_dotenv
load_dotenv()

# Import diskcache
from diskcache import Cache

# Initialize the cache
# The cache directory will be 'iiko_cache' in the current working directory
# Data will expire after 900 seconds (15 minutes)
cache = Cache('iiko_cache', expire=900)

IIKO_API_URL = os.getenv("IIKO_API_URL")
IIKO_API_TOKEN = os.getenv("IIKO_API_TOKEN")

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
@cache.memoize()
def get_iiko_token():
    """
    Получить токен доступа для работы с iiko API.
    """
    logger.info("Fetching iiko token...")
    url = f"{IIKO_API_URL}/api/1/access_token"
    payload = {"apiLogin": IIKO_API_TOKEN}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        token = response.json().get("token")
        logger.info("iiko token fetched successfully.")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting iiko token: {e}")
        return None

@cache.memoize()
def get_organizations(token):
    """
    Получить список организаций.
    """
    logger.info("Fetching organizations...")
    url = f"{IIKO_API_URL}/api/1/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": []} # Empty list to get all organizations
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        organizations = response.json().get("organizations", [])
        logger.info(f"Fetched {len(organizations)} organizations.")
        return organizations
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting organizations: {e}")
        return None

@cache.memoize()
def get_menu_summary(token):
    """
    Получить сводную информацию по меню (список доступных внешних меню).
    """
    logger.info("Fetching menu summary...")
    url = f"{IIKO_API_URL}/api/2/menu"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        menu_summary = response.json()
        logger.info(f"Menu summary fetched with {len(menu_summary.get('externalMenus', []))} external menus.")
        return menu_summary
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting menu summary: {e}")
        return None

@cache.memoize()
def get_menu_details_by_id(organization_id, menu_id, token):
    """
    Получить номенклатуру (детали меню) для конкретной организации и внешнего меню ID.
    """
    logger.info(f"Fetching menu details for organization {organization_id} and menu {menu_id}...")
    url = f"{IIKO_API_URL}/api/2/menu/by_id"
    headers = {"Authorization": f"Bearer {token}"}
    json_payload = {"externalMenuId": menu_id, "organizationIds": [organization_id]}
    try:
        response = requests.post(url, headers=headers, json=json_payload)
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

# --- Synchronization Logic ---
def synchronize_iiko_data():
    logger.info("Starting iiko data synchronization...")
    try:
        iiko_data, main_organization_id = get_iiko_menu_data()
    except Exception as e:
        logger.error(f"Failed to fetch data from iiko: {e}. Exiting sync.")
        return

    if not iiko_data:
        logger.error("Empty data received from iiko. Exiting sync.")
        return

    iiko_categories_raw = iiko_data.get('itemCategories', [])
    iiko_modifier_groups_raw = iiko_data.get('modifierGroups', [])

    # --- FIX START: Populate all_iiko_items_by_id from both 'itemCategories' and top-level 'items' ---
    all_iiko_items_by_id = {}

    # First, populate from items nested within categories
    for category_data in iiko_categories_raw:
        for item_data in category_data.get('items', []):
            item_id = item_data.get('itemId')
            if item_id:
                all_iiko_items_by_id[item_id] = item_data

    # Second, populate from top-level 'items' array (for modifiers, sometimes products/recs)
    for item_data in iiko_data.get('items', []):
        item_id = item_data.get('itemId')
        if item_id:
            # Overwrite if already exists from categories, or add if new
            all_iiko_items_by_id[item_id] = item_data
    # --- FIX END ---

    # --- Step 0: Identify the Recommendation Category in iiko ---
    recommendation_category_internal_db_id = None
    recommendation_iiko_id = None

    rec_cat_data = next((c for c in iiko_categories_raw if c.get('name') == RECOMMENDATION_CATEGORY_NAME), None)
    if rec_cat_data:
        recommendation_iiko_id = rec_cat_data['id']

    if recommendation_iiko_id:
        logger.info(f"Identified iiko Recommendation Category ID: {recommendation_iiko_id}")
    else:
        logger.info(f"WARNING: Could not identify iiko Recommendation Category by name '{RECOMMENDATION_CATEGORY_NAME}'. Recommendations won't be synced via category.")

    # --- Initial Cleanup (Soft Delete) ---
    try:
        db.session.query(Category).update({Category.is_hidden: True})
        db.session.query(Product).update({Product.is_hidden: True})
        db.session.commit()
        logger.info("Marked existing categories and products as hidden for initial cleanup.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during initial cleanup (setting is_hidden): {e}")

    # --- Step 1: Sync Categories ---
    logger.info("Syncing Categories...")
    existing_categories = {c.iiko_category_id: c for c in Category.query.all()}
    category_iiko_to_db_id_map = {}

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
                iiko_category_id=cat_iiko_id,
                name=name,
                description=description,
                image_url=image_url,
                is_hidden=is_hidden,
                icon=icon_map.get(name, "❓"),
                color=color_map.get(name, "from-gray-400 to-gray-600")
            )
            db.session.add(category)
        db.session.flush()
        category_iiko_to_db_id_map[cat_iiko_id] = category.id

        if cat_iiko_id == recommendation_iiko_id:
            recommendation_category_internal_db_id = category.id

    db.session.commit()
    logger.info("Categories synced.")

    # --- Step 2: Sync Products, Addons, and Recommendations ---
    logger.info("Syncing Products, Addons, and Recommendations...")

    existing_products = {p.iiko_product_id: p for p in Product.query.all()}
    existing_addons = {a.iiko_addon_id: a for a in Addon.query.all()}
    existing_recommendations = {r.iiko_recommendation_id: r for r in Recommendation.query.all()}

    product_iiko_to_db_map = {}
    addon_iiko_to_db_map = {}
    recommendation_iiko_to_db_map = {}

    # Process items found within categories (these will be products and possibly recommendations)
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

            price_value = Decimal('0.00')
            item_image_url = None

            item_sizes = iiko_item.get('itemSizes', [])
            if item_sizes:
                first_size = item_sizes[0]
                if first_size.get('prices'):
                    price_entry = first_size['prices'][0]
                    raw_price_value = price_entry.get('price')

                    try:
                        if isinstance(raw_price_value, (int, float)):
                            price_value = Decimal(str(raw_price_value))
                        elif isinstance(raw_price_value, str):
                            cleaned_price_str = raw_price_value.replace(',', '.').strip()
                            price_value = Decimal(cleaned_price_str)
                        else:
                            price_value = Decimal('0.00')
                            logger.info(f"WARNING: Unexpected type for price '{type(raw_price_value)}' for item '{item_name}' (ID: {item_iiko_id}). Defaulting to 0.00.")

                    except InvalidOperation as e:
                        logger.info(f"ERROR: Could not convert price '{raw_price_value}' to Decimal for item '{item_name}' (ID: {item_iiko_id}). Error: {e}. Defaulting to 0.00.")
                        price_value = Decimal('0.00')

                item_image_url = first_size.get('buttonImageUrl')

            if not item_image_url and iiko_item.get('images'):
                item_image_url = iiko_item['images'][0].get('imageUrl')
            elif not item_image_url and iiko_item.get('picture'):
                item_image_url = iiko_item['picture']

            # --- UPDATED NUTRITION DATA EXTRACTION LOGIC ---
            nutrition_data = {
                'calories': 0.0,
                'carbs': 0.0,
                'fat': 0.0,
                'proteins': 0.0
            }
            if item_sizes: # Check if item_sizes exist
                first_size_nutrition = item_sizes[0].get('nutritionPerHundredGrams')
                if first_size_nutrition:
                    # Use .get() with default 0.0 to safely extract values
                    nutrition_data['calories'] = float(first_size_nutrition.get('energy', 0.0))
                    nutrition_data['carbs'] = float(first_size_nutrition.get('carbs', 0.0))
                    nutrition_data['fat'] = float(first_size_nutrition.get('fats', 0.0)) # Note: iiko uses 'fats'
                    nutrition_data['proteins'] = float(first_size_nutrition.get('proteins', 0.0))
            # --- END UPDATED NUTRITION DATA EXTRACTION ---

            ingredients_list = []
            if iiko_item.get('allergens'):
                ingredients_list.extend([a['name'] for a in iiko_item['allergens'] if 'name' in a])
            if iiko_item.get('tags'):
                ingredients_list.extend(iiko_item['tags'])
            if iiko_item.get('labels'):
                ingredients_list.extend(iiko_item['labels'])

            if not item_iiko_id or not item_name:
                logger.info(f"Skipping malformed item data in category '{category_data.get('name')}': {iiko_item}")
                continue

            is_our_product = False
            is_our_recommendation = False

            if recommendation_category_internal_db_id and category_id == recommendation_iiko_id:
                is_our_recommendation = True
            elif item_type in ['DISH', 'GOODS']: # These are main menu items
                is_our_product = True


            if is_our_product:
                product = product_iiko_to_db_map.get(item_iiko_id) or existing_products.get(item_iiko_id)

                if product:
                    product.name = item_name
                    product.description = item_description
                    product.price = price_value
                    product.image = item_image_url
                    product.categoryId = category_db_id
                    product.nutrition = nutrition_data # Updated nutrition data
                    product.ingredients = ingredients_list if ingredients_list else None
                    product.is_hidden = is_hidden
                    product.sku = sku
                    product.measure_unit = measure_unit
                    product.item_type = item_type
                else:
                    product = Product(
                        iiko_product_id=item_iiko_id,
                        name=item_name,
                        description=item_description,
                        price=price_value,
                        image=item_image_url,
                        categoryId=category_db_id,
                        nutrition=nutrition_data, # Updated nutrition data
                        ingredients=ingredients_list if ingredients_list else None,
                        is_hidden=is_hidden,
                        sku=sku,
                        measure_unit=measure_unit,
                        item_type=item_type
                    )
                    db.session.add(product)
                db.session.flush()
                product_iiko_to_db_map[item_iiko_id] = product

            # Recommendations found within a category
            elif is_our_recommendation:
                recommendation = recommendation_iiko_to_db_map.get(item_iiko_id) or existing_recommendations.get(item_iiko_id)
                if recommendation:
                    recommendation.name = item_name
                    recommendation.price = price_value
                    recommendation.image = item_image_url
                else:
                    recommendation = Recommendation(
                        iiko_recommendation_id=item_iiko_id,
                        name=item_name,
                        price=price_value,
                        image=item_image_url
                    )
                    db.session.add(recommendation)
                db.session.flush()
                recommendation_iiko_to_db_map[item_iiko_id] = recommendation

    # --- NEW ADDITION: Process top-level 'items' which are often modifiers or other un-categorized items ---
    # These items might not be associated with a specific category, but are needed for lookups
    for iiko_item in iiko_data.get('items', []): # Loop through top-level 'items'
        item_iiko_id = iiko_item.get('itemId')
        item_name = iiko_item.get('name')
        item_type = iiko_item.get('type')
        is_hidden = iiko_item.get('isHidden', False)

        price_value = Decimal('0.00')
        item_image_url = None

        item_sizes = iiko_item.get('itemSizes', [])
        if item_sizes:
            first_size = item_sizes[0]
            if first_size.get('prices'):
                price_entry = first_size['prices'][0]
                raw_price_value = price_entry.get('price')
                try:
                    if isinstance(raw_price_value, (int, float)):
                        price_value = Decimal(str(raw_price_value))
                    elif isinstance(raw_price_value, str):
                        cleaned_price_str = raw_price_value.replace(',', '.').strip()
                        price_value = Decimal(cleaned_price_str)
                except InvalidOperation as e:
                    logger.error(f"ERROR: Could not convert price '{raw_price_value}' to Decimal for item '{item_name}' (ID: {item_iiko_id}). Error: {e}. Defaulting to 0.00.")

            item_image_url = first_size.get('buttonImageUrl')

        if not item_image_url and iiko_item.get('images'):
            item_image_url = iiko_item['images'][0].get('imageUrl')
        elif not item_image_url and iiko_item.get('picture'):
            item_image_url = iiko_item['picture']

        # Only process as addon if it's explicitly a MODIFIER type
        if item_type == 'MODIFIER':
            addon = addon_iiko_to_db_map.get(item_iiko_id) or existing_addons.get(item_iiko_id)
            if addon:
                addon.name = item_name
                addon.price = price_value
                addon.image = item_image_url
            else:
                addon = Addon(
                    iiko_addon_id=item_iiko_id,
                    name=item_name,
                    price=price_value,
                    image=item_image_url
                )
                db.session.add(addon)
            db.session.flush()
            addon_iiko_to_db_map[item_iiko_id] = addon

    db.session.commit()
    logger.info("Products, Addons, and Recommendations synced. Now setting up relationships.")

    # --- Step 3: Clean up and Rebuild Relationships ---
    try:
        db.session.query(ProductAddon).delete()
        db.session.query(ProductRecommendation).delete()
        db.session.commit()
        logger.info("Existing Product-Addon and Product-Recommendation relationships cleared.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing old relationships: {e}")

    # --- Sync Modifiers (Addons) ---
    for iiko_mod_group in iiko_modifier_groups_raw:
        product_iiko_id = iiko_mod_group.get('product')
        parent_product_obj = product_iiko_to_db_map.get(product_iiko_id)

        if not parent_product_obj:
            logger.info(f"Skipping modifier group for iiko Product ID '{product_iiko_id}' not found in our Products map. It might be a non-menu item or a deleted product.")
            continue

        for iiko_modifier_item_ref in iiko_mod_group.get('modifiers', []):
            mod_iiko_id = iiko_modifier_item_ref.get('product')

            addon_obj = addon_iiko_to_db_map.get(mod_iiko_id)

            if not addon_obj:
                logger.info(f"WARNING: Addon '{mod_iiko_id}' not found in our Addon map for product '{parent_product_obj.name}'. Trying to create it.")
                full_mod_item_data = all_iiko_items_by_id.get(mod_iiko_id)

                if full_mod_item_data:
                    mod_name = full_mod_item_data.get('name')
                    mod_price = Decimal('0.00')

                    mod_item_sizes = full_mod_item_data.get('itemSizes', [])
                    if mod_item_sizes:
                        first_mod_size = mod_item_sizes[0]
                        if first_mod_size.get('prices'):
                            raw_mod_price_value = first_mod_size['prices'][0].get('price')

                            try:
                                if isinstance(raw_mod_price_value, (int, float)):
                                    mod_price = Decimal(str(raw_mod_price_value))
                                elif isinstance(raw_mod_price_value, str):
                                    cleaned_mod_price_str = raw_mod_price_value.replace(',', '.').strip()
                                    mod_price = Decimal(cleaned_mod_price_str)
                                else:
                                    logger.info(f"WARNING: Unexpected type for modifier price '{type(raw_mod_price_value)}' for addon '{mod_name}' (ID: {mod_iiko_id}). Defaulting to 0.00.")
                                    mod_price = Decimal('0.00')

                            except InvalidOperation as e:
                                logger.error(f"ERROR: Could not convert modifier price '{raw_mod_price_value}' to Decimal for addon '{mod_name}' (ID: {mod_iiko_id}). Error: {e}. Defaulting to 0.00.")
                                mod_price = Decimal('0.00')

                    mod_image = None
                    if mod_item_sizes:
                        mod_image = mod_item_sizes[0].get('buttonImageUrl')
                    elif full_mod_item_data.get('images'):
                        mod_image = full_mod_item_data['images'][0].get('imageUrl')
                    elif full_mod_item_data.get('picture'):
                        mod_image = full_mod_item_data['picture']

                    addon_obj = Addon(
                        iiko_addon_id=mod_iiko_id,
                        name=mod_name,
                        price=mod_price,
                        image=mod_image
                    )
                    db.session.add(addon_obj)
                    db.session.flush()
                    addon_iiko_to_db_map[mod_iiko_id] = addon_obj
                    logger.info(f"Created Addon '{mod_name}' (ID: {mod_iiko_id}) and added to map.")
                else:
                    logger.error(f"ERROR: Could not find full data for Addon '{mod_iiko_id}'. Skipping relationship for product '{parent_product_obj.name}'.")
                    continue

            # Add the relationship only if addon_obj was found or successfully created
            product_addon = ProductAddon(
                product_id=parent_product_obj.id,
                addon_id=addon_obj.id
            )
            db.session.add(product_addon)

    # --- Sync Recommendations (linking all products to all recommendations) ---
    all_products_db_objects = list(product_iiko_to_db_map.values())
    all_recommendations_db_objects = list(recommendation_iiko_to_db_map.values())

    for product_obj in all_products_db_objects:
        for rec_obj in all_recommendations_db_objects:
            product_recommendation = ProductRecommendation(
                product_id=product_obj.id,
                recommendation_id=rec_obj.id
            )
            db.session.add(product_recommendation)

    db.session.commit()
    logger.info("Relationships synced.")

    logger.info("Data synchronization complete.")
