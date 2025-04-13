from datetime import datetime
from flask_login import UserMixin
from app import db
from sqlalchemy import Enum
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    role = db.Column(Enum('Penjual', 'Pembeli', name='user_roles'), nullable=False, default='Pembeli')

    products = db.relationship('Product', backref='seller', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_details = db.relationship('OrderDetail', backref='product', lazy=True)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship('User', backref='cart_items', lazy=True)
    product = db.relationship('Product', backref='carts', lazy=True)  # Relasi yang benar

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Menunggu Pembayaran')
    bukti_pembayaran = db.Column(db.String(255), nullable=True)

    order_details = db.relationship('OrderDetail', backref='order', lazy=True)

class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
