# app/api.py

import traceback
from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields
from werkzeug.exceptions import HTTPException, InternalServerError # Import InternalServerError
from app.models import db, Category, Product, ProductAddon, Addon, Recommendation, Order, OrderItem, ProductRecommendation
from sqlalchemy.orm import joinedload
from datetime import datetime
import json
from decimal import Decimal

api_bp = Blueprint('api', __name__)
# It's good practice to set catch_all_404s=True if you want Flask-RESTx to handle all 404s
# and potentially other HTTP errors with its error handlers.
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


# --- Global error handler for all unhandled exceptions (500 errors) ---
@api.errorhandler(Exception)
@api.marshal_with(error_model, code=500) # Marshal the output with our error model
def handle_uncaught_exception(e):
    """
    This catches any unhandled exception (Python Exception) and returns a 500 Internal Server Error.
    It provides a more verbose JSON response than the default Flask HTML error page.
    """
    # Log the full traceback to your server logs
    full_traceback = traceback.format_exc()
    print(f"UNCAUGHT EXCEPTION: {e}\n{full_traceback}")

    # Determine if in debug mode to expose traceback
    # In a production environment, you typically set FLASK_DEBUG=False
    # You might want to get this from app.config['DEBUG'] if it's set globally
    # For now, let's assume if it's not explicitly true, we don't expose
    import os
    is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or api.app.debug # Check api.app.debug as well

    response = {
        'message': 'An unexpected internal server error occurred.',
        'status': 500,
        'error_type': type(e).__name__,
        'details': full_traceback if is_debug_mode else 'Please contact support with the error timestamp.'
    }
    return response, 500

# --- Global error handler for HTTPExceptions (e.g., 404, 400, 405) ---
@api.errorhandler(HTTPException)
@api.marshal_with(error_model, code=lambda e: e.code) # Dynamically set status code from HTTPException
def handle_http_exception(e):
    """
    This catches HTTP-related exceptions (like 404 Not Found, 400 Bad Request, etc.)
    and returns a JSON response.
    """
    # Log the exception, but not necessarily the full traceback unless it's a 5xx
    if e.code >= 500:
        print(f"HTTP EXCEPTION (SERVER ERROR): {e}\n{traceback.format_exc()}")
    else:
        print(f"HTTP EXCEPTION (CLIENT ERROR): {e}")

    # Determine if in debug mode to expose traceback
    import os
    is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or api.app.debug

    response = {
        'message': e.description, # HTTPException usually has a description
        'status': e.code,
        'error_type': type(e).__name__,
        'details': traceback.format_exc() if is_debug_mode and e.code >= 500 else None # Only show traceback for server-side HTTP errors in debug
    }
    return response, e.code


# ... (rest of your app/api.py content remains the same) ...
# You should place the error handlers after the 'api = Api(...)' initialization.


# --- Your existing models and routes go here, e.g.: ---

# --- New Ingredient Item Model ---
ingredient_item_model = api.model('IngredientItem', {
    'code': fields.String(description='Ingredient code', allow_null=True),
    'name': fields.String(required=True, description='Ingredient name')
})

category_model = api.model('Category', {
    'id': fields.String(required=True, description='Category ID'),
    'name': fields.String(required=True, description='Category name'),
    'icon': fields.String(description='Category icon (emoji)'),
    'color': fields.String(description='Category color (Tailwind CSS gradient classes)')
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

product_model = api.model('Product', {
    'id': fields.String(required=True, description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description'),
    'price': fields.Float(required=True, description='Product price'),
    'image': fields.String(description='Product image URL'),
    'categoryId': fields.String(required=True, description='ID of the category this product belongs to'),
    'nutrition': fields.Nested(nutrition_model, description='Nutritional information', allow_null=False, default={
        "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0
    }),
    'ingredients': fields.List(fields.Nested(ingredient_item_model), description='List of ingredients', allow_null=True, default=[]),
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


@api.route('/categories')
class CategoryList(Resource):
    @api.marshal_list_with(category_model)
    def get(self):
        """Get all categories"""
        categories = Category.query.all()
        # This is where an error might occur if categories is malformed or DB connection fails
        # For example, if a category's 'name' is None but your model requires it.
        return categories

@api.route('/products')
class ProductList(Resource):
    @api.param('categoryId', 'Filter products by category ID')
    def get(self):
        """Get all products, optionally filtered by category"""
        category_id = api.parser().add_argument('categoryId', type=str, location='args').parse_args()['categoryId']

        query = Product.query.filter_by(is_hidden=False).options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        )
        if category_id:
            query = query.filter_by(categoryId=category_id)

        products = query.all()

        marshaled_products = []

        for product in products:
            nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
            for key in ["calories", "carbs", "fat", "proteins"]:
                if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                    nutrition_data_for_marshal[key] = 0.0
                if isinstance(nutrition_data_for_marshal[key], Decimal):
                    nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

            valid_recommendations = []
            if product.recommendations:
                for pr_association in product.recommendations:
                    rec_obj = pr_association.recommendation
                    if (rec_obj and rec_obj.id and isinstance(rec_obj.name, str) and
                        rec_obj.name and rec_obj.price is not None):
                        valid_recommendations.append({
                            'id': str(rec_obj.id),
                            'name': rec_obj.name,
                            'price': float(rec_obj.price) if isinstance(rec_obj.price, Decimal) else rec_obj.price,
                            'image': rec_obj.image
                        })
                    else:
                        print(f"WARNING: Skipping malformed recommendation for product {product.id}: ID={getattr(rec_obj, 'id', 'N/A')}, Name={repr(getattr(rec_obj, 'name', 'N/A'))} (Type: {type(getattr(rec_obj, 'name', None))}), Price={getattr(rec_obj, 'price', 'N/A')})")

            valid_addons = []
            if product.available_addons:
                for pa_association in product.available_addons:
                    addon_obj = pa_association.addon
                    if (addon_obj and addon_obj.id and isinstance(addon_obj.name, str) and
                        addon_obj.name and addon_obj.price is not None):
                        valid_addons.append({
                            'id': str(addon_obj.id),
                            'name': addon_obj.name,
                            'price': float(addon_obj.price) if isinstance(addon_obj.price, Decimal) else addon_obj.price,
                            'image': addon_obj.image
                        })
                    else:
                        print(f"WARNING: Skipping malformed addon for product {product.id}: ID={getattr(addon_obj, 'id', 'N/A')}, Name={repr(getattr(addon_obj, 'name', 'N/A'))} (Type: {type(getattr(addon_obj, 'name', None))}), Price={getattr(addon_obj, 'price', 'N/A')})")

            processed_ingredients = product.ingredients if product.ingredients is not None else []
            cleaned_ingredients = []
            for ing in processed_ingredients:
                if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                    cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
                else:
                    print(f"WARNING: Skipping malformed ingredient for product {product.id}: {ing!r}")
            
            product_for_marshal = {
                'id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
                'image': product.image,
                'categoryId': str(product.categoryId),
                'nutrition': nutrition_data_for_marshal,
                'ingredients': cleaned_ingredients,
                'availableAddons': valid_addons,
                'recommendations': valid_recommendations
            }

            try:
                marshaled_products.append(api.marshal(product_for_marshal, product_model))
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to marshal product ID: {product.id}. "
                      f"Error: {e}. Raw data: {product_for_marshal}. Traceback:\n{traceback.format_exc()}")
                continue

        return marshaled_products

@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    def get(self, product_id):
        """Get a single product by ID"""
        product = Product.query.filter_by(is_hidden=False).options(
            joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get_or_404(product_id) # get_or_404 will automatically raise a 404 HTTPException

        nutrition_data_for_marshal = product.nutrition if isinstance(product.nutrition, dict) else {}
        for key in ["calories", "carbs", "fat", "proteins"]:
            if key not in nutrition_data_for_marshal or nutrition_data_for_marshal[key] is None:
                nutrition_data_for_marshal[key] = 0.0
            if isinstance(nutrition_data_for_marshal[key], Decimal):
                nutrition_data_for_marshal[key] = float(nutrition_data_for_marshal[key])

        valid_recommendations = []
        if product.recommendations:
            for pr_association in product.recommendations:
                rec_obj = pr_association.recommendation
                if (rec_obj and rec_obj.id and isinstance(rec_obj.name, str) and
                    rec_obj.name and rec_obj.price is not None):
                    valid_recommendations.append({
                        'id': str(rec_obj.id),
                        'name': rec_obj.name,
                        'price': float(rec_obj.price) if isinstance(rec_obj.price, Decimal) else rec_obj.price,
                        'image': rec_obj.image
                    })
                else:
                    print(f"WARNING: Skipping malformed recommendation for product {product.id}: ID={getattr(rec_obj, 'id', 'N/A')}, Name={repr(getattr(rec_obj, 'name', 'N/A'))} (Type: {type(getattr(rec_obj, 'name', None))}), Price={getattr(rec_obj, 'price', 'N/A')})")

        valid_addons = []
        if product.available_addons:
            for pa_association in product.available_addons:
                addon_obj = pa_association.addon
                if (addon_obj and addon_obj.id and isinstance(addon_obj.name, str) and
                    addon_obj.name and addon_obj.price is not None):
                    valid_addons.append({
                        'id': str(addon_obj.id),
                        'name': addon_obj.name,
                        'price': float(addon_obj.price) if isinstance(addon_obj.price, Decimal) else addon_obj.price,
                        'image': addon_obj.image
                    })
                else:
                    print(f"WARNING: Skipping malformed addon for product {product.id}: ID={getattr(addon_obj, 'id', 'N/A')}, Name={repr(getattr(addon_obj, 'name', 'N/A'))} (Type: {type(getattr(addon_obj, 'name', None))}), Price={getattr(addon_obj, 'price', 'N/A')})")

        processed_ingredients = product.ingredients if product.ingredients is not None else []
        cleaned_ingredients = []
        for ing in processed_ingredients:
            if isinstance(ing, dict) and 'name' in ing and isinstance(ing['name'], str):
                cleaned_ingredients.append({'code': ing.get('code', ''), 'name': ing['name']})
            else:
                print(f"WARNING: Skipping malformed ingredient for product {product.id}: {ing!r}")

        product_for_marshal = {
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
            'image': product.image,
            'categoryId': str(product.categoryId),
            'nutrition': nutrition_data_for_marshal,
            'ingredients': cleaned_ingredients,
            'availableAddons': valid_addons,
            'recommendations': valid_recommendations
        }
        
        try:
            return api.marshal(product_for_marshal, product_model)
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to marshal single product ID: {product.id}. "
                  f"Error: {e}. Raw data: {product_for_marshal}. Traceback:\n{traceback.format_exc()}")
            # Instead of abort(500), let the global error handler catch it.
            # Raising the original exception is generally better as the error handler can get the traceback.
            raise # Re-raise the exception to be caught by @api.errorhandler(Exception)


@api.route('/orders')
class OrderList(Resource):
    def get(self):
        """Get all orders"""
        orders = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.items).joinedload(OrderItem.selected_addons),
            joinedload(Order.items).joinedload(OrderItem.selected_recommendations)
        ).all()

        serialized_orders = []
        for order in orders:
            items_data = []
            for item in order.items:
                product_obj = item.product

                fetched_addons = []
                if item.selected_addons_ids:
                    addons_from_db = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                    for addon in addons_from_db:
                        if (addon and addon.id and isinstance(addon.name, str) and
                            addon.name and addon.price is not None):
                            fetched_addons.append({
                                'id': str(addon.id),
                                'name': addon.name,
                                'price': float(addon.price) if isinstance(addon.price, Decimal) else addon.price,
                                'image': addon.image
                            })
                        else:
                            print(f"WARNING: Skipping malformed selected addon ID: {getattr(addon, 'id', 'N/A')} for order item.")

                fetched_recommendations = []
                if item.selected_recommendation_ids:
                    recs_from_db = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
                    for rec in recs_from_db:
                        if (rec and rec.id and isinstance(rec.name, str) and
                            (rec.name or rec.price is not None)):
                            fetched_recommendations.append({
                                'id': str(rec.id),
                                'name': rec.name,
                                'price': float(rec.price) if isinstance(rec.price, Decimal) else rec.price,
                                'image': rec.image
                            })
                        else:
                            print(f"WARNING: Skipping malformed selected recommendation ID: {getattr(rec, 'id', 'N/A')} for order item.")


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

                product_marshaled = {
                    'id': str(product_obj.id),
                    'name': product_obj.name,
                    'description': product_obj.description,
                    'price': float(product_obj.price) if isinstance(product_obj.price, Decimal) else product_obj.price,
                    'image': product_obj.image,
                    'categoryId': str(product_obj.categoryId),
                    'nutrition': product_nutrition_data_for_marshal,
                    'ingredients': cleaned_ingredients_in_order_item,
                    'availableAddons': [], 
                    'recommendations': []
                }
                
                try:
                    marshaled_product_in_order_item = api.marshal(product_marshaled, product_model)
                except Exception as e:
                    print(f"ERROR: Failed to marshal product {product_obj.id} within order item. Error: {e}. Raw: {product_marshaled}")
                    marshaled_product_in_order_item = None # Or raise the exception if you want it to fail the whole request

                items_data.append({
                    'product': marshaled_product_in_order_item,
                    'quantity': item.quantity,
                    'selectedAddons': api.marshal(fetched_addons, addon_model),
                    'selectedRecommendations': api.marshal(fetched_recommendations, recommendation_model)
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
        return api.marshal(serialized_orders, order_model)


    @api.expect(order_model)
    @api.marshal_with(order_model, code=201)
    def post(self):
        """Create a new order"""
        data = api.payload

        calculated_total = 0
        order_items_to_add = []

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
            for rec_id in selected_recommendation_ids:
                recommendation = Recommendation.query.get(rec_id)
                if recommendation:
                    item_price += recommendation.price

            calculated_total += item_price * item_data['quantity']

            order_items_to_add.append(OrderItem(
                product_id=product.id,
                quantity=item_data['quantity'],
                selected_addons_ids=selected_addon_ids,
                selected_recommendation_ids=selected_recommendation_ids
            ))

        final_total = data.get('total', calculated_total)
        if abs(Decimal(str(final_total)) - Decimal(str(calculated_total))) > Decimal('0.01'):
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

        db.session.commit()

        created_order = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons).joinedload(ProductAddon.addon),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation)
        ).get(new_order.id)

        response_items = []
        for item in created_order.items:
            product_obj = item.product
            selected_addons = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
            selected_recommendations = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()

            response_items.append({
                'product': product_obj,
                'quantity': item.quantity,
                'selectedAddons': [addon for addon in selected_addons if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None],
                'selectedRecommendations': [rec for rec in selected_recommendations if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None)]
            })

        response_data = {
            'id': str(created_order.id),
            'items': response_items,
            'total': float(created_order.total) if isinstance(created_order.total, Decimal) else created_order.total,
            'deliveryInfo': {
                'address': created_order.delivery_address,
                'phone': created_order.delivery_phone,
                'paymentMethod': created_order.payment_method,
                'comment': created_order.comment
            },
            'status': created_order.status,
            'createdAt': created_order.created_at,
            'estimatedDelivery': created_order.estimated_delivery
        }
        return response_data, 201

@api.route('/addons')
class AddonList(Resource):
    @api.marshal_list_with(addon_model)
    def get(self):
        """Get all addons"""
        addons_data = Addon.query.all()
        valid_addons = []
        for addon in addons_data:
            if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None:
                valid_addons.append(addon)
            else:
                print(f"WARNING: Skipping malformed addon in AddonList: ID={getattr(addon, 'id', 'N/A')}, Name={repr(getattr(addon, 'name', 'N/A'))} (Type: {type(getattr(addon, 'name', None))}), Price={getattr(addon, 'price', 'N/A')}")
        return valid_addons

@api.route('/recommendations')
class RecommendationList(Resource):
    @api.marshal_list_with(recommendation_model)
    def get(self):
        """Get all recommendations"""
        recommendations_data = Recommendation.query.all()
        valid_recommendations = []
        for rec in recommendations_data:
            if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None):
                valid_recommendations.append(rec)
            else:
                print(f"WARNING: Skipping malformed recommendation in RecommendationList: ID={getattr(rec, 'id', 'N/A')}, Name={repr(getattr(rec, 'name', 'N/A'))} (Type: {type(getattr(rec, 'name', None))}), Price={getattr(rec, 'price', 'N/A')})")
        return valid_recommendations
