# app/api.py

import traceback
from flask import Blueprint, jsonify, current_app
from flask_restx import Api, Resource, fields
from werkzeug.exceptions import HTTPException, InternalServerError
from app.models import db, MainCategory, Category, Product, ProductAddon, Addon, Recommendation, Order, OrderItem, ProductRecommendation
from app import iiko_service
from sqlalchemy.orm import joinedload
from datetime import datetime
import json
from decimal import Decimal
from uuid import uuid4

api_bp = Blueprint('api', __name__)

api = Api(api_bp, version='1.0', title='Mandarin Food Delivery API',
          description='A comprehensive API for Mandarin Food Delivery App', doc='/doc',
          catch_all_404s=True)

# --- Define a model for error responses ---
error_model = api.model('Error', {
    'message': fields.String(description='A descriptive error message'),
    'status': fields.Integer(description='HTTP status code'),
    'error_type': fields.String(description='Type of the error (e.g., "InternalServerError", "BadRequest")'),
    'details': fields.String(description='More specific details about the error (e.g., traceback in debug mode)', allow_null=True)
})

# --- Models ---
ingredient_item_model = api.model('IngredientItem', {
    'code': fields.String(description='Ingredient code', allow_null=True),
    'name': fields.String(required=True, description='Ingredient name')
})

# Update category_model to represent MainCategory
main_category_model = api.model('MainCategory', {
    'id': fields.String(required=True, description='Main Category ID'),
    'name': fields.String(required=True, description='Main Category name'),
    'icon': fields.String(description='Main Category icon (emoji)', allow_null=True),
    'color': fields.String(description='Main Category color (Tailwind CSS gradient classes)', allow_null=True),
    'description': fields.String(description='Main Category description', allow_null=True),
    'image_url': fields.String(description='Main Category image URL', allow_null=True)
})

addon_model = api.model('Addon', {
    'id': fields.String(required=True, description='Addon ID'),
    'name': fields.String(required=True, description='Addon name'),
    'price': fields.Float(required=True, description='Addon price'),
    'image': fields.String(description='Addon image URL', allow_null=True)
})

recommendation_model = api.model('Recommendation', {
    'id': fields.String(required=True, description='Recommendation ID'),
    'name': fields.String(required=True, description='Recommendation name'),
    'price': fields.Float(required=True, description='Recommendation price'),
    'image': fields.String(description='Recommendation image URL', allow_null=True)
})

nutrition_model = api.model('Nutrition', {
    'calories': fields.Float(description='Energy in kcal', allow_null=False, default=0.0),
    'carbs': fields.Float(description='Carbohydrates in grams', allow_null=False, default=0.0),
    'fat': fields.Float(description='Fat in grams', allow_null=False, default=0.0),
    'proteins': fields.Float(description='Proteins in grams', allow_null=False, default=0.0)
})

# product_model's 'categoryId' field now refers to MainCategory ID
product_model = api.model('Product', {
    'id': fields.String(required=True, description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description', allow_null=True),
    'price': fields.Float(required=True, description='Product price'),
    'image': fields.String(description='Product image URL', allow_null=True),
    'categoryId': fields.String(required=True, description='ID of the main category this product belongs to'), # Now MainCategory ID
    'nutrition': fields.Nested(nutrition_model, description='Nutritional information', allow_null=False, default={
        "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0
    }),
    'ingredients': fields.List(fields.Nested(ingredient_item_model), description='List of ingredients', allow_null=True, default=[]),
    # CHANGED: Now returns nested addon_model for availableAddons
    'availableAddons': fields.List(fields.Nested(addon_model), description='List of available addons for this product', allow_null=True, default=[]),
    'recommendations': fields.List(fields.Nested(recommendation_model), description='List of recommended products for this product', allow_null=True, default=[])
})

order_item_model = api.model('OrderItem', {
    'product': fields.Nested(product_model, description='Product details'),
    'quantity': fields.Integer(required=True, description='Quantity of the product'),
    'selectedAddons': fields.List(fields.Nested(addon_model), description='Selected addons for this product item', default=[]),
    'selectedRecommendations': fields.List(fields.Nested(recommendation_model), description='Selected recommendations for this product item', default=[])
})

delivery_info_model = api.model('DeliveryInfo', {
    'address': fields.String(required=True, description='Delivery address'),
    'phone': fields.String(required=True, description='Contact phone number'),
    'paymentMethod': fields.String(required=True, description='Payment method (e.g., cash, card)'),
    'comment': fields.String(description='Additional comments for delivery', allow_null=True)
})

order_model = api.model('Order', {
    'id': fields.String(required=True, description='Order ID'),
    'items': fields.List(fields.Nested(order_item_model), description='List of items in the order'),
    'total': fields.Float(required=True, description='Total price of the order'),
    'deliveryInfo': fields.Nested(delivery_info_model, required=True, description='Delivery information'),
    'status': fields.String(required=True, description='Current status of the order'),
    'createdAt': fields.DateTime(dt_format='iso8601', description='Timestamp of order creation'),
    'estimatedDelivery': fields.DateTime(dt_format='iso8601', description='Estimated delivery time', allow_null=True)
})

## Category Endpoints

@api.route('/categories')
class CategoryList(Resource):
    def get(self):
        """Get all categories"""
        categories = MainCategory.query.order_by(MainCategory.display_order).all()
        marshaled_categories = api.marshal(categories, main_category_model)
        return jsonify(marshaled_categories)

## Product Endpoints

@api.route('/products')
class ProductList(Resource):
    @api.param('categoryId', 'Filter products by category ID')
    def get(self):
        """Get all products, optionally filtered by category"""
        category_id = api.parser().add_argument('categoryId', type=str, location='args').parse_args()['categoryId']

        # Ensure that Addons are also loaded so you can access their details
        query = Product.query.filter_by(is_hidden=False).options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        )
        if category_id:
            query = query.filter_by(main_category_id=category_id)

        products = query.all()

        marshaled_products = []
        for product in products:
            nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
            for key in ["calories", "carbs", "fat", "proteins"]:
                if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                    nutrition_data_for_marshal[key] = 0.0
                if isinstance(nutrition_data_for_marshal[key], Decimal):
                    nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

            processed_ingredients = product.ingredients if product.ingredients is not None else []
            cleaned_ingredients = []
            for ing in processed_ingredients:
                if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                    cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
                else:
                    current_app.logger.warning(f"Skipping malformed ingredient for product {product.id}: {ing!r}")

            marshaled_recommendations = [
                api.marshal(pr.recommendation, recommendation_model)
                for pr in product.recommendations if pr.recommendation
            ]

            # CHANGED: Marshal available_addons to their full model representation
            marshaled_available_addons = [
                api.marshal(pa.addon, addon_model)
                for pa in product.available_addons if pa.addon
            ]

            product_for_marshal = {
                'id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
                'image': product.image,
                'categoryId': str(product.main_category_id), # This is now the MainCategory ID
                'nutrition': nutrition_data_for_marshal,
                'ingredients': cleaned_ingredients,
                'availableAddons': marshaled_available_addons, # Use the marshaled list
                'recommendations': marshaled_recommendations
            }
            marshaled_products.append(api.marshal(product_for_marshal, product_model))

        return jsonify(marshaled_products)

@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, product_id):
        """Get a single product by ID"""
        # Ensure Addons are also loaded here
        product = Product.query.options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get_or_404(product_id)

        if product.is_hidden:
            api.abort(404, "Product not found or is hidden.")

        nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
        for key in ["calories", "carbs", "fat", "proteins"]:
            if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                nutrition_data_for_marshal[key] = 0.0
            if isinstance(nutrition_data_for_marshal[key], Decimal):
                nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

        processed_ingredients = product.ingredients if product.ingredients is not None else []
        cleaned_ingredients = []
        for ing in processed_ingredients:
            if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
            else:
                current_app.logger.warning(f"Skipping malformed ingredient for product {product.id}: {ing!r}")

        marshaled_recommendations = [
            api.marshal(pr.recommendation, recommendation_model)
            for pr in product.recommendations if pr.recommendation
        ]

        # CHANGED: Marshal available_addons to their full model representation
        marshaled_available_addons = [
            api.marshal(pa.addon, addon_model)
            for pa in product.available_addons if pa.addon
        ]

        product_for_marshal = {
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
            'image': product.image,
            'categoryId': str(product.main_category_id), # Corrected from product.categoryId
            'nutrition': nutrition_data_for_marshal,
            'ingredients': cleaned_ingredients,
            'availableAddons': marshaled_available_addons, # Use the marshaled list
            'recommendations': marshaled_recommendations
        }
        return product_for_marshal # Flask-RESTx's @api.marshal_with will jsonify this.

## Order Endpoints

@api.route('/orders')
class OrderList(Resource):
    @api.marshal_with(order_model, as_list=True)
    def get(self):
        """Get all orders"""
        orders = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product),
        ).all()

        serialized_orders = []
        for order in orders:
            items_data = []
            for item in order.items:
                product_obj = item.product

                fetched_addons = []
                if item.selected_addons_ids:
                    addons_from_db = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                    fetched_addons = [
                        api.marshal(addon, addon_model)
                        for addon in addons_from_db
                        if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None
                    ]
                    for addon in addons_from_db:
                        if not (addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None):
                            print(f"WARNING: Skipping malformed selected addon ID: {getattr(addon, 'id', 'N/A')} for order item {item.id}.")

                fetched_recommendations = []
                if item.selected_recommendation_ids:
                    recs_from_db = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
                    fetched_recommendations = [
                        api.marshal(rec, recommendation_model)
                        for rec in recs_from_db
                        if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)
                    ]
                    for rec in recs_from_db:
                        if not (rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)):
                                print(f"WARNING: Skipping malformed selected recommendation ID: {getattr(rec, 'id', 'N/A')} for order item {item.id}.")

                product_nutrition_data_for_marshal = product_obj.nutrition if isinstance(product_obj.nutrition, dict) else {}
                for key in ["calories", "carbs", "fat", "proteins"]:
                    if key not in product_nutrition_data_for_marshal or product_nutrition_data_for_marshal[key] is None:
                        product_nutrition_data_for_marshal[key] = 0.0
                    if isinstance(product_nutrition_data_for_marshal[key], Decimal):
                        product_nutrition_data_for_marshal[key] = float(product_nutrition_data_for_marshal[key])

                processed_ingredients_in_order_item = product_obj.ingredients if product_obj.ingredients is not None else []
                cleaned_ingredients_in_order_item = []
                for ing in processed_ingredients_in_order_item:
                    if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                        cleaned_ingredients_in_order_item.append({'code': ing.get('code', ''), 'name': ing['name']})
                    else:
                        print(f"WARNING: Skipping malformed ingredient for product {product_obj.id} within order item: {ing!r}")

                # CHANGED: Ensure product_obj's available_addons are loaded and marshaled for the product nested in order_item
                # You need to load available_addons relation explicitly if it's not already.
                # For `get_or_404` or `filter_by` on Product, ensure `joinedload(Product.available_addons).joinedload(ProductAddon.addon)`
                # is part of the initial product query when fetching orders if you want this
                # information available. If not, a separate query would be needed, which is less efficient.
                # Given product_obj comes from `joinedload(Order.items).joinedload(OrderItem.product)`,
                # you'd need to add `joinedload(OrderItem.product).joinedload(Product.available_addons).joinedload(ProductAddon.addon)`
                # to the main order query.
                product_marshaled_available_addons = [
                    api.marshal(pa.addon, addon_model)
                    for pa in product_obj.available_addons if pa.addon
                ]

                product_marshaled = {
                    'id': str(product_obj.id),
                    'name': product_obj.name,
                    'description': product_obj.description,
                    'price': float(product_obj.price) if isinstance(product_obj.price, Decimal) else product_obj.price,
                    'image': product_obj.image,
                    'categoryId': str(product_obj.main_category_id), # Corrected from product_obj.categoryId
                    'nutrition': product_nutrition_data_for_marshal,
                    'ingredients': cleaned_ingredients_in_order_item,
                    'availableAddons': product_marshaled_available_addons, # Use the marshaled list for product in order item
                    'recommendations': [
                        api.marshal(pr.recommendation, recommendation_model)
                        for pr in product_obj.recommendations if pr.recommendation
                    ]
                }
                marshaled_product_in_order_item = api.marshal(product_marshaled, product_model)

                items_data.append({
                    'product': marshaled_product_in_order_item,
                    'quantity': item.quantity,
                    'selectedAddons': fetched_addons,
                    'selectedRecommendations': fetched_recommendations
                })

            serialized_orders.append({
                'id': str(order.id),
                'items': items_data,
                'total': float(order.total) if isinstance(order.total, Decimal) else order.total,
                'deliveryInfo': {
                    'address': order.delivery_address,
                    'phone': order.delivery_phone,
                    'paymentMethod': order.payment_method,
                    'comment': order.comment
                },
                'status': order.status,
                'createdAt': order.created_at,
                'estimatedDelivery': order.estimated_delivery
            })
        return serialized_orders

    @api.expect(order_model)
    @api.marshal_with(order_model, code=201)
    def post(self):
        """Create a new order and send it to IIKO (mock for now)."""
        data = api.payload

        # --- Dynamic retrieval of Organization ID and Terminal Group ID ---
        iiko_token = iiko_service.get_iiko_token()
        if not iiko_token:
            api.logger.error("Failed to get IIKO access token for order creation.")
            api.abort(500, "Failed to connect to external ordering system (IIKO).")

        organization_id = None
        terminal_group_id = None

        try:
            organizations = iiko_service.get_organizations(iiko_token)
            if organizations:
                organization_id = organizations[0].get("id")
                api.logger.info(f"Using IIKO Organization ID: {organization_id}")
            else:
                api.logger.error("No organizations found from IIKO API.")
                api.abort(500, "Could not determine organization ID for external order.")

            terminal_groups = iiko_service.get_terminal_groups(organization_id, iiko_token)
            if terminal_groups and terminal_groups[0].get("items"):
                # Assuming the first item in the first terminal group list is the one we want
                terminal_group_id = terminal_groups[0]["items"][0].get("id")
                api.logger.info(f"Using IIKO Terminal Group ID: {terminal_group_id}")
            else:
                api.logger.error(f"No terminal groups found for organization {organization_id} from IIKO API.")
                api.abort(500, "Could not determine terminal group ID for external order.")

        except Exception as e:
            api.logger.error(f"Error fetching IIKO organization/terminal group IDs: {e}", exc_info=True)
            api.abort(500, f"Failed to initialize external ordering system: {str(e)}")
        # --- End Dynamic retrieval ---


        calculated_total = Decimal('0.00')
        order_items_to_add = []
        iiko_order_items = []

        for item_data in data['items']:
            product = Product.query.get(item_data['product']['id'])
            if not product:
                api.abort(400, f"Product with ID {item_data['product']['id']} not found.")

            item_price = product.price
            selected_addon_ids = [a['id'] for a in item_data.get('selectedAddons', [])]
            selected_recommendation_ids = [r['id'] for r in item_data.get('selectedRecommendations', [])]

            for addon_id in selected_addon_ids:
                addon = Addon.query.get(addon_id)
                if addon:
                    item_price += addon.price
                else:
                    api.logger.warning(f"Selected addon with ID {addon_id} not found. Skipping price calculation for it.")
            for rec_id in selected_recommendation_ids:
                 recommendation = Recommendation.query.get(rec_id)
                 if recommendation:
                     item_price += recommendation.price
                 else:
                     api.logger.warning(f"Selected recommendation with ID {rec_id} not found. Skipping price calculation for it.")

            calculated_total += item_price * Decimal(str(item_data['quantity']))

            order_items_to_add.append(OrderItem(
                product_id=product.id,
                quantity=item_data['quantity'],
                selected_addons_ids=selected_addon_ids,
                selected_recommendation_ids=selected_recommendation_ids
            ))

            iiko_modifiers = []
            for addon_id in selected_addon_ids:
                iiko_modifiers.append({
                    "id": addon_id, # This should be the IIKO ID for the addon
                    "type": "Product",
                    "amount": 1
                })
            for rec_id in selected_recommendation_ids:
                 iiko_modifiers.append({
                    "id": rec_id, # This should be the IIKO ID for the recommendation
                    "type": "Product",
                    "amount": 1
                })


            iiko_order_items.append({
                "productId": product.iiko_product_id, # Assuming your Product model has iiko_product_id
                "productCode": product.iiko_product_id, # iiko sometimes uses productCode as well
                "name": product.name,
                "amount": item_data['quantity'],
                "price": float(product.price),
                "modifiers": iiko_modifiers,
                "comboId": None,
                "positionId": str(uuid4())
            })


        final_total = Decimal(str(data.get('total', calculated_total)))
        if abs(final_total - calculated_total) > Decimal('0.01'):
            api.logger.warning(f"Client provided total {data.get('total')} differs from calculated total {calculated_total}. Using calculated total.")
            final_total = calculated_total

        new_order = Order(
            id=f'order-{int(datetime.now().timestamp() * 1000)}',
            total=final_total,
            delivery_address=data['deliveryInfo']['address'],
            delivery_phone=data['deliveryInfo']['phone'],
            payment_method=data['deliveryInfo']['paymentMethod'],
            comment=data['deliveryInfo'].get('comment'),
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush()

        for item in order_items_to_add:
            item.order_id = new_order.id
            db.session.add(item)

        try:
            iiko_order_payload = {
                "id": new_order.id,
                "externalId": new_order.id,
                "organizationId": organization_id, # Use dynamically retrieved ID
                "items": iiko_order_items,
                "phone": new_order.delivery_phone,
                "address": {
                    "street": new_order.delivery_address,
                    "city": "Default City"
                },
                "deliveryPoint": {
                    "latitude": 0, "longitude": 0
                },
                "deliveryDate": datetime.utcnow().isoformat(),
                "deliveryTime": datetime.utcnow().strftime("%H:%M"),
                "comment": new_order.comment,
                "fullSum": float(final_total),
                "isSelfService": False,
                "paymentItems": [
                    {
                        "sum": float(final_total),
                        "paymentType": {
                            "code": "Cash" if new_order.payment_method.lower() == "cash" else "Card",
                            "name": new_order.payment_method,
                            "combinable": True,
                            "externalId": None,
                            "isProcessed": True,
                            "isFiscal": True
                        },
                        "isPrepay": False,
                        "isExternal": False
                    }
                ],
                "sourceKey": "MandarinWebApp",
            }

            iiko_response = iiko_service.create_delivery_order(
                organization_id=organization_id, # Use dynamically retrieved ID
                terminal_group_id=terminal_group_id, # Use dynamically retrieved ID
                order=iiko_order_payload,
                create_order_settings={"transportToFrontTimeout": 0}
            )

            if iiko_response and iiko_response.get('orderId'):
                new_order.status = 'sent_to_iiko'
                api.logger.info(f"Order {new_order.id} successfully sent to IIKO. IIKO Order ID: {iiko_response['orderId']}")
            else:
                new_order.status = 'iiko_send_failed'
                api.logger.error(f"Failed to send order {new_order.id} to IIKO. Response: {iiko_response}")

        except Exception as e:
            db.session.rollback()
            api.logger.error(f"Error sending order to IIKO: {e}", exc_info=True)
            api.abort(500, f"Order created internally but failed to send to external system: {str(e)}")

        db.session.commit()

        created_order = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get(new_order.id)

        return created_order, 201

## Addon Endpoints
@api.route('/addons')
class AddonList(Resource):
    def get(self):
        """Get all addons"""
        addons_data = Addon.query.all()
        valid_addons = [api.marshal(addon, addon_model) for addon in addons_data if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None]
        for addon in addons_data:
            if not (addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None):
                print(f"WARNING: Skipping malformed addon in AddonList: ID={getattr(addon, 'id', 'N/A')}, Name={repr(getattr(addon, 'name', 'N/A'))} (Type: {type(getattr(addon, 'name', None))}), Price={getattr(addon, 'price', 'N/A')}")
        return jsonify(valid_addons)

## Recommendation Endpoints

@api.route('/recommendations')
class RecommendationList(Resource):
    def get(self):
        """Get all recommendations"""
        recommendations_data = Recommendation.query.all()
        valid_recommendations = [api.marshal(rec, recommendation_model) for rec in recommendations_data if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)]
        for rec in recommendations_data:
            if not (rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)):
                print(f"WARNING: Skipping malformed recommendation in RecommendationList: ID={getattr(rec, 'id', 'N/A')}, Name={repr(getattr(rec, 'name', 'N/A'))} (Type: {type(getattr(rec, 'name', None))}), Price={getattr(rec, 'price', 'N/A')})")
        return jsonify(valid_recommendations)
