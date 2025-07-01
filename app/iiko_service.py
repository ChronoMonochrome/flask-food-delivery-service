import requests
import os
from dotenv import load_dotenv
from app.models import db, Category, Product, Addon, Recommendation, ProductAddon, ProductRecommendation

load_dotenv() # Load environment variables from .env file

IIKO_API_URL = os.getenv("IIKO_API_URL")
IIKO_API_TOKEN = os.getenv("IIKO_API_TOKEN")

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

def get_access_token():
    """
    Получить токен доступа для работы с iiko API.
    """
    if not IIKO_API_URL or not IIKO_API_TOKEN:
        raise ValueError("IIKO_API_URL or IIKO_API_TOKEN not set in environment variables.")

    url = f"{IIKO_API_URL}/api/1/access_token"
    payload = {"apiLogin": IIKO_API_TOKEN}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json().get("token")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка получения токена: {e}")
    except ValueError as e:
        raise Exception(f"Ошибка парсинга JSON ответа токена: {e}, Ответ: {response.text}")


def get_organizations(token):
    """
    Получить список организаций.
    """
    url = f"{IIKO_API_URL}/api/1/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationIds": []} # Request all accessible organizations
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        organizations = response.json().get("organizations", [])
        if not organizations:
            raise Exception("Не найдено организаций по токену API.")
        return organizations
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка получения организаций: {e}")
    except ValueError as e:
        raise Exception(f"Ошибка парсинга JSON ответа организаций: {e}, Ответ: {response.text}")

def get_menu_from_iiko(organization_id, token):
    """
    Получить номенклатуру (меню) для конкретной организации из iiko API.
    """
    url = f"{IIKO_API_URL}/api/1/nomenclature"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"organizationId": organization_id}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30) # Increased timeout for menu
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка получения меню из iiko: {e}")
    except ValueError as e:
        raise Exception(f"Ошибка парсинга JSON ответа меню: {e}, Ответ: {response.text}")

def synchronize_iiko_data(overwrite_existing=True):
    """
    Основная функция для синхронизации данных из iiko в базу данных.
    :param overwrite_existing: Если True, полностью очищает БД перед загрузкой.
                               Если False, обновляет существующие записи и добавляет новые.
    """
    logger.info(f"Начало синхронизации данных с iiko (режим overwrite_existing={overwrite_existing})...")
    try:
        token = get_access_token()
        logger.info("Токен iiko получен.")
        organizations = get_organizations(token)
        if not organizations:
            logger.warning("Не найдено организаций для синхронизации.")
            return

        organization_id = organizations[0]["id"]
        logger.info(f"Синхронизация для организации ID: {organization_id} ({organizations[0]['name']})")

        iiko_menu_data = get_menu_from_iiko(organization_id, token)
        logger.info("Данные меню из iiko получены.")

        if overwrite_existing:
            # Clear existing data only if overwrite_existing is True
            logger.info("Очистка существующих данных в базе данных (overwrite_existing=True)...")
            db.session.query(ProductAddon).delete()
            db.session.query(ProductRecommendation).delete()
            db.session.query(Product).delete()
            db.session.query(Category).delete()
            db.session.query(Addon).delete()
            db.session.query(Recommendation).delete()
            db.session.commit()
            logger.info("Существующие данные очищены.")

        # Fetch existing data for comparison and updates
        existing_categories = {c.iiko_category_id: c for c in Category.query.all()}
        existing_products = {p.iiko_product_id: p for p in Product.query.all()}
        existing_addons = {a.iiko_addon_id: a for a in Addon.query.all()}
        existing_recommendations = {r.iiko_recommendation_id: r for r in Recommendation.query.all()}

        # Keep track of IDs from iiko to identify deleted items
        iiko_category_ids_present = set()
        iiko_product_ids_present = set()
        iiko_addon_ids_present = set()
        iiko_recommendation_ids_present = set() # Based on how we classify recommendations

        # --- Process Groups (Categories, Addons, Recommendations) ---
        iiko_groups = {g["id"]: g for g in iiko_menu_data.get("groups", [])}
        db_categories_map = {} # Map iiko_category_id to SQLAlchemy object
        db_addons_map = {} # Map iiko_addon_id to SQLAlchemy object
        db_recommendations_map = {} # Map iiko_recommendation_id to SQLAlchemy object

        # First pass: identify and store Categories, Addons, Recommendations based on group names
        for group_id, group_data in iiko_groups.items():
            group_name = group_data["name"]

            if "доп" in group_name.lower() or "дополнительн" in group_name.lower(): # Heuristic for addons
                iiko_addon_ids_present.add(group_id) # Mark group ID as present
                addon = existing_addons.get(group_id)
                if not addon:
                    addon = Addon(iiko_addon_id=group_id, name=group_name, price=0.0) # Price for group is irrelevant here
                    db.session.add(addon)
                    logger.debug(f"Добавлен новый аддон-группа: {group_name}")
                else:
                    # Update existing group name if it changed in iiko
                    if addon.name != group_name:
                        addon.name = group_name
                        logger.debug(f"Обновлено имя аддон-группы: {group_name}")
                db_addons_map[group_id] = addon

            # Add more heuristics for recommendation groups if they exist
            # For now, we'll treat products within these categories as recommendations if they fit criteria below.
            # Example: if "Рекомендации" in group_name.lower():
            #   iiko_recommendation_ids_present.add(group_id)
            #   ... (create/update Recommendation group)

            else: # Treat as regular category
                iiko_category_ids_present.add(group_id)
                category = existing_categories.get(group_id)
                if not category:
                    # You might need to map iiko categories to your desired icons/colors
                    icon_map = {
                        "Бургеры": "🍔", "Пицца": "🍕", "Суши": "🍣", "Салаты": "🥗",
                        "Десерты": "🍰", "Напитки": "🥤", "Закуски": "🍟", "Горячие блюда": "🍲",
                        "Вок": "🍜", "Кальцоне": "🍕", "Ламаджо": "🍖", "Осетинские пироги": "🥧",
                        "Паста": "🍝", "Роллы": "🍣", "Сеты": "🍱", "Супы": "🥣",
                        "Фокаччо": "🍞", "Хачапури": "🧀", "Хот-доги и донер": "🌭",
                        "Мясо": "🥩", "Начинка": "🌶️", "Дополнительный соус": "🧂", "Лапша": "🍜",
                        "Донер на выбор": "🥙", "Сосиска на выбор": "🌭"
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
                        "Донер на выбор": "from-yellow-700 to-orange-800", "Сосиска на выбор": "from-red-600 to-red-800"
                    }
                    category = Category(
                        iiko_category_id=group_id,
                        name=group_name,
                        icon=icon_map.get(group_name, "❓"), # Default icon if not found
                        color=color_map.get(group_name, "from-gray-400 to-gray-600") # Default color
                    )
                    db.session.add(category)
                    logger.debug(f"Добавлена новая категория: {group_name}")
                else:
                    # Update existing category if its name or metadata changed
                    if category.name != group_name:
                        category.name = group_name
                        logger.debug(f"Обновлено имя категории: {group_name}")
                    # Update icon/color if you have a logic for that
                db_categories_map[group_id] = category
        db.session.commit()
        logger.info("Категории, Допы и Рекомендации (группы) обработаны.")

        # --- Process Products ---
        iiko_products = iiko_menu_data.get("products", [])
        db_products_map = {} # Map iiko_product_id to SQLAlchemy object

        for product_data in iiko_products:
            iiko_product_id = product_data["id"]
            product_name = product_data["name"]
            product_description = product_data.get("description", "")

            size_prices = product_data.get("sizePrices", [])
            price = size_prices[0]["price"]["currentPrice"] if size_prices else 0.0

            image_links = product_data.get("imageLinks", [])
            image_url = image_links[0] if image_links else None

            iiko_parent_group_id = product_data.get("parentGroup")

            # Check if this product should be treated as an Addon or Recommendation itself
            # If the product's parent group is classified as an "addon group"
            if iiko_parent_group_id in db_addons_map:
                iiko_addon_ids_present.add(iiko_product_id) # This product ID is an addon item
                addon = existing_addons.get(iiko_product_id)
                if not addon:
                    addon = Addon(
                        iiko_addon_id=iiko_product_id,
                        name=product_name,
                        price=price,
                        image=image_url
                    )
                    db.session.add(addon)
                    logger.debug(f"Добавлен новый элемент-аддон: {product_name}")
                else:
                    # Update existing addon item
                    if addon.name != product_name: addon.name = product_name
                    if addon.price != price: addon.price = price
                    if addon.image != image_url: addon.image = image_url
                    logger.debug(f"Обновлен элемент-аддон: {product_name}")
                db_addons_map[iiko_product_id] = addon # Store for later lookup
                continue # Don't process as a regular product

            # Similar logic for recommendations if specific iiko groups indicate recommendations
            # For this example, we'll assume recommendations are just regular products for now
            # and you'd handle their 'recommended' status separately or based on a direct link from iiko.

            # If not an addon, process as a regular product
            iiko_product_ids_present.add(iiko_product_id)
            category = db_categories_map.get(iiko_parent_group_id) # Use the map of newly created/updated categories
            if not category:
                logger.warning(f"Предупреждение: Продукт '{product_name}' (ID: {iiko_product_id}) имеет неизвестную родительскую группу ID: {iiko_parent_group_id}. Пропуск.")
                continue

            product = existing_products.get(iiko_product_id)
            if not product:
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
                logger.debug(f"Добавлен новый продукт: {product_name}")
            else:
                # Update existing product fields
                if product.name != product_name: product.name = product_name
                if product.description != product_description: product.description = product_description
                if product.price != price: product.price = price
                if product.image != image_url: product.image = image_url
                if product.categoryId != category.id: product.categoryId = category.id # Update category if changed
                logger.debug(f"Обновлен продукт: {product_name}")

            db_products_map[iiko_product_id] = product # Store for later linking of junction tables

        db.session.commit()
        logger.info("Продукты обработаны.")

        # --- Handle Deletions ---
        # If overwrite_existing is False, we need to delete items no longer present in iiko
        if not overwrite_existing:
            logger.info("Проверка на удаленные элементы...")
            # Categories no longer in iiko
            for iiko_id, category in existing_categories.items():
                if iiko_id not in iiko_category_ids_present:
                    # Products belonging to this category must be deleted first or reassigned
                    db.session.query(Product).filter_by(categoryId=category.id).delete(synchronize_session='fetch')
                    db.session.delete(category)
                    logger.info(f"Удалена категория и связанные продукты: {category.name} (ID: {iiko_id})")

            # Addons (both group-level and item-level) no longer in iiko
            for iiko_id, addon in existing_addons.items():
                if iiko_id not in iiko_addon_ids_present:
                    # Remove all ProductAddon links first
                    db.session.query(ProductAddon).filter_by(addon_id=addon.id).delete(synchronize_session='fetch')
                    db.session.delete(addon)
                    logger.info(f"Удален аддон: {addon.name} (ID: {iiko_id})")

            # Products no longer in iiko (that are not addons/recommendations themselves)
            for iiko_id, product in existing_products.items():
                if iiko_id not in iiko_product_ids_present:
                    # Remove all junction table links for this product
                    db.session.query(ProductAddon).filter_by(product_id=product.id).delete(synchronize_session='fetch')
                    db.session.query(ProductRecommendation).filter_by(product_id=product.id).delete(synchronize_session='fetch')
                    # And any order items pointing to this product (handle with caution in a real app)
                    # For simplicity, we assume order items will be handled by your order management
                    # If you delete products, you might need to nullify product_id in OrderItem or cascade delete.
                    db.session.delete(product)
                    logger.info(f"Удален продукт: {product.name} (ID: {iiko_id})")

            # Recommendations no longer in iiko (if you have a specific way to track them by iiko_id)
            # For simplicity, if recommendations are just general products, you'd handle them via product deletion above.
            # If you had dedicated iiko_recommendation_ids for recommendation items, implement a similar loop.
            db.session.commit()
            logger.info("Проверка на удаленные элементы завершена.")


        # --- Link Products to Addons/Recommendations ---
        # This part still assumes a general linking logic because iiko's nomenclature API
        # doesn't provide product-specific modifier/addon relationships directly.
        # You'll need to adapt this if iiko provides such data via other endpoints.

        # Example: Link all main products to "Соевый соус" as an addon (if it exists)
        soy_sauce_addon = Addon.query.filter_by(name="Соевый соус").first() # Assuming name is unique
        # Example: Let's assume a general recommendation like "Cola 0.5l"
        # Find a product in your DB that you consider a general recommendation
        coke_recommendation = Product.query.filter_by(name="Кола 0.5л").first() # Assuming "Кола 0.5л" is a product

        # Clear existing product-addon/recommendation links for updated products
        # This is important to reflect changes from iiko or prevent duplicate links
        db.session.query(ProductAddon).delete()
        db.session.query(ProductRecommendation).delete()
        db.session.commit()
        logger.info("Связи продукт-аддон/рекомендация очищены для обновления.")


        # Re-establish links for all current products
        for iiko_product_id, db_product in db_products_map.items():
            # Only link to main products, not items that are themselves addons (like 'Соевый соус')
            # Check if this product is in the iiko_product_ids_present set (meaning it's a regular product)
            if iiko_product_id in iiko_product_ids_present:
                # Link common addons/recommendations
                if soy_sauce_addon:
                    # Check if link already exists before adding (important for non-overwrite mode)
                    existing_link = ProductAddon.query.filter_by(product_id=db_product.id, addon_id=soy_sauce_addon.id).first()
                    if not existing_link:
                        db.session.add(ProductAddon(product=db_product, addon=soy_sauce_addon))
                if coke_recommendation:
                    # For recommendations, we link the ProductRecommendation table.
                    # If 'coke_recommendation' is an actual Product, it means we are recommending another product.
                    # So, we should link to the Recommendation table if 'coke_recommendation' was treated as a Recommendation item.
                    # Or, if Recommendation is just a list of 'Product' IDs, then it's different.
                    # Let's assume for this purpose 'coke_recommendation' should exist in the Recommendation table.
                    # If "Кола 0.5л" is a product that you want to *recommend*, then it should be added to the Recommendation table first.
                    # Let's assume a recommendation *item* called "Кола 0.5л" exists in the Recommendation table.
                    coke_rec_item = Recommendation.query.filter_by(name="Кола 0.5л").first()
                    if coke_rec_item:
                        existing_link = ProductRecommendation.query.filter_by(product_id=db_product.id, recommendation_id=coke_rec_item.id).first()
                        if not existing_link:
                            db.session.add(ProductRecommendation(product=db_product, recommendation=coke_rec_item))
                # Add logic here for specific product modifiers if iiko API provides them.
                # E.g., if product_data has 'modifiers' list, iterate it here to create ProductAddon links.

        db.session.commit()
        logger.info("Продукты успешно связаны с аддонами/рекомендациями (на основе эвристики).")


        logger.info("Синхронизация данных с iiko завершена успешно.")

    except Exception as e:
        db.session.rollback() # Rollback all changes on error
        logger.error(f"Ошибка при синхронизации данных с iiko: {e}", exc_info=True) # Log full traceback
        raise # Re-raise the exception to propagate it

# This part is for testing the synchronization function
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    # IMPORTANT: Use a dedicated test database for local runs, not your production DB!
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@localhost/test_mydatabase' # Use your actual DB URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Basic logging setup for standalone execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


    with app.app_context():
        # Drop all tables and recreate them for a clean test run
        logger.info("Очистка базы данных для тестового запуска...")
        db.drop_all()
        db.create_all()
        logger.info("База данных очищена и создана.")

        # Test with overwrite_existing=True (first run, acts like current clear+load)
        logger.info("\n--- Тестовый запуск: overwrite_existing=True (чистая загрузка) ---")
        try:
            synchronize_iiko_data(overwrite_existing=True)
            # Verify data
            print("Категории после первой синхронизации:", Category.query.count())
            print("Продукты после первой синхронизации:", Product.query.count())
            print("Аддоны после первой синхронизации:", Addon.query.count())
            print("Рекомендации после первой синхронизации:", Recommendation.query.count())
            print("Связи продукт-аддон после первой синхронизации:", ProductAddon.query.count())
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")

        # Test with overwrite_existing=False (simulating an update)
        logger.info("\n--- Тестовый запуск: overwrite_existing=False (обновление) ---")
        # Simulate a change in iiko data for demonstration (you can manually edit mock data if testing locally)
        # For example, change a product name in iiko or add a new one.
        try:
            synchronize_iiko_data(overwrite_existing=False)
            # Verify data - counts should remain similar or increase slightly if new items were added
            print("Категории после второй синхронизации:", Category.query.count())
            print("Продукты после второй синхронизации:", Product.query.count())
            print("Аддоны после второй синхронизации:", Addon.query.count())
            print("Рекомендации после второй синхронизации:", Recommendation.query.count())
            print("Связи продукт-аддон после второй синхронизации:", ProductAddon.query.count())
        except Exception as e:
            logger.error(f"Update sync failed: {e}")

        # Example: Query some data to see the results
        burger_category = Category.query.filter_by(name="Бургеры").first()
        if burger_category:
            print(f"\nПродукты в категории '{burger_category.name}':")
            for p in burger_category.products:
                print(f"  - {p.name} (Price: {p.price})")
                if p.available_addons:
                    print("    Доступные аддоны:")
                    for pa in p.available_addons:
                        print(f"      - {pa.addon.name}")
