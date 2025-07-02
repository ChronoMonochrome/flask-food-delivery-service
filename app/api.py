# app/api.py

import traceback
from flask import Blueprint
from flask_restx import Api, Resource, fields
from app.models import db, Category, Product, ProductAddon, Addon, Recommendation, Order, OrderItem, ProductRecommendation
from sqlalchemy.orm import joinedload # Keep this import
from datetime import datetime
import json
from decimal import Decimal # Import Decimal for type checking/conversion if needed

api_bp = Blueprint('api', __name__)
api = Api(api_bp, version='1.0', title='Mandarin Food Delivery API',
          description='A comprehensive API for Mandarin Food Delivery App', doc='/doc')

# Models for Flask-RESTx documentation
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
    'image': fields.String(description='Addon image URL', allow_null=True) # Added image field
})

recommendation_model = api.model('Recommendation', {
    'id': fields.String(required=True, description='Recommendation ID'), # Changed to required=True based on product_model
    'name': fields.String(required=True, description='Recommendation name'), # Changed to required=True
    'price': fields.Float(required=True, description='Recommendation price'), # Changed to required=True
    'image': fields.String(description='Recommendation image URL', allow_null=True)
})

nutrition_model = api.model('Nutrition', {
    'calories': fields.Float(description='Energy in kcal', attribute='calories', allow_null=True), # Use 'attribute' to map to DB field name if different
    'carbs': fields.Float(description='Carbohydrates in grams', allow_null=True),
    'fat': fields.Float(description='Fat in grams', allow_null=True),
    'proteins': fields.Float(description='Proteins in grams', allow_null=True)
})

product_model = api.model('Product', {
    'id': fields.String(required=True, description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description'),
    'price': fields.Float(required=True, description='Product price'),
    'image': fields.String(description='Product image URL'),
    'categoryId': fields.String(required=True, description='ID of the category this product belongs to'),
    'nutrition': fields.Nested(nutrition_model, description='Nutritional information', allow_null=True, default={
        "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0 # Explicit default structure
    }),
    'ingredients': fields.List(fields.String, description='List of ingredients', allow_null=True, default=[]), # Default to empty list
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
        return categories

@api.route('/products')
class ProductList(Resource):
    # Removed @api.marshal_list_with(product_model) because we are doing manual marshalling
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
            nutrition_data_for_marshal = product.nutrition if product.nutrition is not None else {
                "calories": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "proteins": 0.0
            }
            if not isinstance(nutrition_data_for_marshal, dict):
                nutrition_data_for_marshal = {
                    "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0
                }

            valid_recommendations = []
            if product.recommendations:
                for pr_association in product.recommendations:
                    rec_obj = pr_association.recommendation # This is the Recommendation object
                    if (rec_obj and rec_obj.id and isinstance(rec_obj.name, str) and
                        rec_obj.name and rec_obj.price is not None):
                        valid_recommendations.append({
                            'id': str(rec_obj.id),
                            'name': rec_obj.name,
                            'price': float(rec_obj.price) if isinstance(rec_obj.price, Decimal) else rec_obj.price,
                            'image': rec_obj.image
                        })
                    else:
                        print(f"WARNING: Skipping malformed recommendation for product {product.id}: {rec_obj} (ID: {getattr(rec_obj, 'id', 'N/A')}, Name: {getattr(rec_obj, 'name', 'N/A')}, Price: {getattr(rec_obj, 'price', 'N/A')})")


            valid_addons = []
            if product.available_addons:
                for pa_association in product.available_addons:
                    addon_obj = pa_association.addon # This is the Addon object
                    if (addon_obj and addon_obj.id and isinstance(addon_obj.name, str) and
                        addon_obj.name and addon_obj.price is not None):
                        valid_addons.append({
                            'id': str(addon_obj.id),
                            'name': addon_obj.name,
                            'price': float(addon_obj.price) if isinstance(addon_obj.price, Decimal) else addon_obj.price,
                            'image': addon_obj.image
                        })
                    else:
                        print(f"WARNING: Skipping malformed addon for product {product.id}: {addon_obj} (ID: {getattr(addon_obj, 'id', 'N/A')}, Name: {getattr(addon_obj, 'name', 'N/A')}, Price: {getattr(addon_obj, 'price', 'N/A')})")


            product_for_marshal = {
                'id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
                'image': product.image,
                'categoryId': str(product.categoryId),
                'nutrition': nutrition_data_for_marshal,
                'ingredients': product.ingredients if product.ingredients is not None else [],
                'availableAddons': valid_addons,
                'recommendations': valid_recommendations
            }

            try:
                marshaled_products.append(api.marshal(product_for_marshal, product_model))
            except Exception as e:
                print(f"ERROR: Failed to marshal product ID: {product.id}. Error: {e}")
                product_data_for_debug = {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price) if isinstance(product.price, Decimal) else product.price,
                    "image": product.image,
                    "categoryId": str(product.categoryId),
                    "nutrition_raw": product.nutrition,
                    "ingredients_raw": product.ingredients,
                    "availableAddons_raw": [str(pa.addon.id) for pa in product.available_addons] if product.available_addons else [], # FIXED: Access through .addon
                    "recommendations_raw": [str(pr.recommendation.id) for pr in product.recommendations] if product.recommendations else [], # FIXED: Access through .recommendation
                    "error_details": str(e),
                    "error_traceback": traceback.format_exc()
                }
                marshaled_products.append(product_data_for_debug) # Add raw data for debugging


        return marshaled_products

@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, product_id):
        """Get a single product by ID"""
        product = Product.query.filter_by(is_hidden=False).options(
            # --- MINIMAL CHANGE: Use the correct relationship names ---
            joinedload(Product.available_addons).joinedload(ProductAddon.addon), # Corrected relationship name
            joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation) # Corrected relationship name
        ).get_or_404(product_id)

        # --- FIX 1 (same as ProductList) ---
        nutrition_data_for_marshal = product.nutrition if product.nutrition is not None else {
            "calories": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "proteins": 0.0
        }
        if not isinstance(nutrition_data_for_marshal, dict):
            nutrition_data_for_marshal = {
                "calories": 0.0, "carbs": 0.0, "fat": 0.0, "proteins": 0.0
            }


        # --- FIX 2 & 3 (same as ProductList) ---
        valid_recommendations = []
        if product.recommendations: # Use correct relationship name
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
                    print(f"WARNING: Skipping malformed recommendation for product {product.id}: {rec_obj} (ID: {getattr(rec_obj, 'id', 'N/A')}, Name: {getattr(rec_obj, 'name', 'N/A')}, Price: {getattr(rec_obj, 'price', 'N/A')})")


        valid_addons = []
        if product.available_addons: # Use correct relationship name
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
                    print(f"WARNING: Skipping malformed addon for product {product.id}: {addon_obj} (ID: {getattr(addon_obj, 'id', 'N/A')}, Name: {getattr(addon_obj, 'name', 'N/A')}, Price: {getattr(addon_obj, 'price', 'N/A')})")


        product_for_marshal = {
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': float(product.price) if isinstance(product.price, Decimal) else product.price,
            'image': product.image,
            'categoryId': str(product.categoryId),
            'nutrition': nutrition_data_for_marshal,
            'ingredients': product.ingredients if product.ingredients is not None else [],
            'availableAddons': valid_addons,
            'recommendations': valid_recommendations
        }
        return product_for_marshal


@api.route('/orders')
class OrderList(Resource):
    @api.marshal_list_with(order_model)
    def get(self):
        """Get all orders"""
        orders = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons).joinedload(ProductAddon.addon), # Corrected relationship
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation) # Corrected relationship
        ).all()

        serialized_orders = []
        for order in orders:
            items_data = []
            for item in order.items:
                product_obj = item.product

                selected_addons = []
                if item.selected_addons_ids:
                    addons = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                    for addon in addons:
                        if addon and addon.id and isinstance(addon.name, str) and addon.name and addon.price is not None:
                            selected_addons.append(addon)
                        else:
                            print(f"WARNING: Skipping malformed selected addon ID: {getattr(addon, 'id', 'N/A')} for order item.")


                selected_recommendations = []
                if item.selected_recommendation_ids:
                    recs = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
                    for rec in recs:
                        if rec and rec.id and isinstance(rec.name, str) and (rec.name or rec.price is not None):
                            selected_recommendations.append(rec)
                        else:
                            print(f"WARNING: Skipping malformed selected recommendation ID: {getattr(rec, 'id', 'N/A')} for order item.")


                items_data.append({
                    'product': product_obj,
                    'quantity': item.quantity,
                    'selectedAddons': selected_addons,
                    'selectedRecommendations': selected_recommendations
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
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons).joinedload(ProductAddon.addon), # Corrected relationship
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations).joinedload(ProductRecommendation.recommendation) # Corrected relationship
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
                print(f"WARNING: Skipping malformed addon in AddonList: ID={getattr(addon, 'id', 'N/A')}, Name={getattr(addon, 'name', 'N/A')}, Price={getattr(addon, 'price', 'N/A')}")
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
                print(f"WARNING: Skipping malformed recommendation in RecommendationList: ID={getattr(rec, 'id', 'N/A')}, Name={getattr(rec, 'name', 'N/A')}, Price={getattr(rec, 'price', 'N/A')}")
        return valid_recommendations
