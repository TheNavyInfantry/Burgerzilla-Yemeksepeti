from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from burgerzilla import db
from flask_restx import Resource, marshal
from burgerzilla.api_models import (Restaurant_Dataset, Menu_Dataset, Order_Dataset, Order_Menu_Dataset,
                                    Restaurant_Order_Dataset, Response_Message)
from burgerzilla.models import User, Restaurant, Menu, Order, Order_Menu

from burgerzilla.routes import restaurant_ns

@restaurant_ns.route('/restaurant')
@restaurant_ns.doc(body=Restaurant_Dataset,
          responses={200: "Success", 400: "Validation Error", 403: "Invalid Credentials", 404: "User Not Found"})
class RestaurantOperations(Resource):
    @restaurant_ns.marshal_list_with(Restaurant_Dataset, code=200, envelope='restaurants')
    def get(self):
        all_restaurants = Restaurant.query.all()
        return all_restaurants


@restaurant_ns.route('/menu')
class MenuOperations(Resource):
    @restaurant_ns.marshal_list_with(Menu_Dataset, code=200, envelope='menus')
    def get(self):
        all_menus = Menu.query.all()
        return all_menus

    @jwt_required()
    @restaurant_ns.marshal_with(Menu_Dataset, code=201, envelope='menu')
    def post(self):
        json_data = request.get_json()
        product = json_data.get('product')
        price = json_data.get('price')
        description = json_data.get('description')
        image = json_data.get('image')
        restaurant_id = json_data.get('restaurant_id')
        new_menu = Menu(name=product, price=price, description=description, image=image, restaurant_id=restaurant_id)
        db.session.add(new_menu)
        db.session.commit()
        return new_menu


@restaurant_ns.route('/order')
class RestaurantOrder(Resource):
    @jwt_required()
    @restaurant_ns.marshal_list_with(Order_Menu_Dataset, envelope='restaurant_order_item')
    def get(self):
        '''Returns which menu order was taken'''
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        order = Order.query.filter_by(user_id=user.id).first()
        menus = Order_Menu.query.filter_by(order_id=order.id)

        item_list = []
        for each in menus:
            item_list.append(each)

        return item_list


@restaurant_ns.route('/order/detail')
class RestaurantOrderDetail(Resource):
    @jwt_required()
    @restaurant_ns.marshal_list_with(Restaurant_Order_Dataset, envelope='restaurant_order_item_detail')
    def get(self):
        '''Returns order details of the user to the Restaurant'''
        user_id = get_jwt_identity()  # JWT den gelmis gibi sayiliyor
        order = Order.query.filter_by(status='NEW', user_id=user_id).first()

        if order == None:
            return {"Error": "Your restaurant does not have any pending orders at the moment!"}, 404
        else:
            order_status = Order.query.filter_by(status='NEW', user_id=user_id).update({'status': 'PENDING'})
            db.session.commit()

            user = User.query.get(user_id)

            menus = Order_Menu.query.filter_by(order_id=order.id)
            item_list = []
            price = 0

            for menu in menus:
                item = Menu.query.get(menu.menu_id)  # menu item

                price += item.price  # menu price

                item_list.append(item)

            return marshal(
                {"name": user.name, 'address': user.address, 'timestamp': order.timestamp, 'user_id': user_id,
                 'restaurant_id': order.restaurant_id, "menus": item_list, "sum_price": price}, Order_Dataset), 200


@restaurant_ns.route('/order/cancel')
class OrderCancel(Resource):
    @jwt_required()
    @restaurant_ns.marshal_with(Response_Message)
    def post(self):
        order_id = get_jwt_identity()  # postmandan gelecek
        order_id_exists = db.session.query(Order).filter(Order.id == order_id, Order.status != "NEW",
                                                         Order.status != "CANCELLED").first() is not None  # kullancinin siparisi var mi (sepet/order)

        if not order_id_exists:
            return {"Message": "There is no available order!"}, 404

        db.session.query(Order).filter_by(id=order_id).update(
            {'status': 'CANCELLED'})  # Delete degil update olacak burada status icin """Statusu Cancel yap"""
        db.session.commit()

        return {"Message": "DELETED!"}, 200