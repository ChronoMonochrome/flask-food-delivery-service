from flask import Blueprint
from flask_restx import Api, Resource, fields
from app.models import db, Category, Product, Addon, Recommendation, Order, OrderItem
from sqlalchemy.orm import joinedload
from datetime import datetime

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
    'price': fields.Float(required=True, description='Addon price')
})

recommendation_model = api.model('Recommendation', {
    'id': fields.String(required=True, description='Recommendation ID'),
    'name': fields.String(required=True, description='Recommendation name'),
    'price': fields.Float(required=True, description='Recommendation price'),
    'image': fields.String(description='Recommendation image URL')
})

nutrition_model = api.model('Nutrition', {
    'calories': fields.Float(description='Calories per serving'),
    'protein': fields.Float(description='Protein in grams'),
    'fat': fields.Float(description='Fat in grams'),
    'carbs': fields.Float(description='Carbohydrates in grams')
})

product_model = api.model('Product', {
    'id': fields.String(required=True, description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description'),
    'price': fields.Float(required=True, description='Product price'),
    'image': fields.String(description='Product image URL'),
    'categoryId': fields.String(required=True, description='ID of the category this product belongs to'),
    'nutrition': fields.Nested(nutrition_model, description='Nutritional information'),
    'ingredients': fields.List(fields.String, description='List of ingredients'),
    'availableAddons': fields.List(fields.Nested(addon_model), description='List of available addons for this product'),
    'recommendations': fields.List(fields.Nested(recommendation_model), description='List of recommended products for this product')
})

order_item_model = api.model('OrderItem', {
    'product': fields.Nested(product_model, description='Product details'), # Full product object
    'quantity': fields.Integer(required=True, description='Quantity of the product'),
    'selectedAddons': fields.List(fields.Nested(addon_model), description='Selected addons for this product item'),
    'selectedRecommendations': fields.List(fields.Nested(recommendation_model), description='Selected recommendations for this product item')
})

delivery_info_model = api.model('DeliveryInfo', {
    'address': fields.String(required=True, description='Delivery address'),
    'phone': fields.String(required=True, description='Contact phone number'),
    'paymentMethod': fields.String(required=True, description='Payment method (e.g., cash, card)'),
    'comment': fields.String(description='Additional comments for delivery')
})

order_model = api.model('Order', {
    'id': fields.String(required=True, description='Order ID'),
    'items': fields.List(fields.Nested(order_item_model), description='List of items in the order'),
    'total': fields.Float(required=True, description='Total price of the order'),
    'deliveryInfo': fields.Nested(delivery_info_model, required=True, description='Delivery information'),
    'status': fields.String(required=True, description='Current status of the order'),
    'createdAt': fields.DateTime(dt_format='iso8601', description='Timestamp of order creation'),
    'estimatedDelivery': fields.DateTime(dt_format='iso8601', description='Estimated delivery time')
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
    @api.marshal_list_with(product_model)
    @api.param('categoryId', 'Filter products by category ID')
    def get(self):
        """Get all products, optionally filtered by category"""
        category_id = api.parser().add_argument('categoryId', type=str, location='args').parse_args()['categoryId']

        query = Product.query.options(
            joinedload(Product.available_addons),
            joinedload(Product.recommendations)
        )
        if category_id:
            query = query.filter_by(categoryId=category_id)
        
        products = query.all()
        return products

@api.route('/products/<string:product_id>')
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, product_id):
        """Get a single product by ID"""
        product = Product.query.options(
            joinedload(Product.available_addons),
            joinedload(Product.recommendations)
        ).get_or_404(product_id)
        return product

@api.route('/orders')
class OrderList(Resource):
    @api.marshal_list_with(order_model)
    def get(self):
        """Get all orders"""
        orders = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations)
        ).all()
        
        # Manually construct selected addons/recommendations for order items
        # This is due to JSON field storing IDs and not full objects
        serialized_orders = []
        for order in orders:
            items_data = []
            for item in order.items:
                product_obj = item.product
                
                selected_addons = []
                if item.selected_addons_ids:
                    selected_addons = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
                
                selected_recommendations = []
                if item.selected_recommendation_ids:
                    selected_recommendations = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()

                items_data.append({
                    'product': product_obj,
                    'quantity': item.quantity,
                    'selectedAddons': selected_addons,
                    'selectedRecommendations': selected_recommendations
                })
            
            serialized_orders.append({
                'id': order.id,
                'items': items_data,
                'total': order.total,
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

    @api.expect(order_model) # Use the same model for input expectation
    @api.marshal_with(order_model, code=201)
    def post(self):
        """Create a new order"""
        data = api.payload
        
        # Calculate total based on received items, or use provided total
        calculated_total = 0
        order_items_to_add = []

        for item_data in data['items']:
            product = Product.query.get(item_data['product']['id']) # Get product from DB
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

        # Use the provided total if it's close to the calculated total, otherwise use calculated.
        # This provides some flexibility for client-side calculations but also ensures data integrity.
        final_total = data.get('total', calculated_total)
        if abs(final_total - calculated_total) > 0.01: # Allow a small floating point difference
            api.logger.warning(f"Client provided total {data.get('total')} differs from calculated total {calculated_total}. Using calculated total.")
            final_total = calculated_total

        new_order = Order(
            # Generate a new unique ID for the order
            id=f'order-{int(datetime.now().timestamp() * 1000)}',
            total=final_total,
            delivery_address=data['deliveryInfo']['address'],
            delivery_phone=data['deliveryInfo']['phone'],
            payment_method=data['deliveryInfo']['paymentMethod'],
            comment=data['deliveryInfo'].get('comment'),
            status='pending', # Default status for new orders
            created_at=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush() # Flush to assign ID before adding order items

        for item in order_items_to_add:
            item.order_id = new_order.id
            db.session.add(item)

        db.session.commit()
        
        # Reload the order with relationships for proper marshaling
        created_order = Order.query.options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.available_addons),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.recommendations)
        ).get(new_order.id)

        # Manually construct selected addons/recommendations for order items in the response
        response_items = []
        for item in created_order.items:
            product_obj = item.product
            selected_addons = Addon.query.filter(Addon.id.in_(item.selected_addons_ids)).all()
            selected_recommendations = Recommendation.query.filter(Recommendation.id.in_(item.selected_recommendation_ids)).all()
            
            response_items.append({
                'product': product_obj,
                'quantity': item.quantity,
                'selectedAddons': selected_addons,
                'selectedRecommendations': selected_recommendations
            })

        response_data = {
            'id': created_order.id,
            'items': response_items,
            'total': created_order.total,
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

from flask import Blueprint, jsonify, request

@api_bp.route('/addons', methods=['GET'])
def get_addons():
    # This is where you would fetch your addon data
    # For demonstration, returning dummy data
    addons_data = [
        {"id": 1, "name": "Premium Feature Pack", "price": 9.99},
        {"id": 2, "name": "Extra Storage", "price": 4.99}
    ]
    return jsonify(addons_data)

@api_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    # This is where you would generate or fetch recommendations
    # For demonstration, returning dummy data
    recommendations_data = [
        {"id": 101, "item": "Recommended Product A", "score": 0.9},
        {"id": 102, "item": "Recommended Service B", "score": 0.85}
    ]
    return jsonify(recommendations_data)
