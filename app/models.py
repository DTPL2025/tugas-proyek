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

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(200), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref='order', lazy=True)
    name = db.Column(db.String(50), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    seller_name = db.Column(db.String(50), nullable=False)
    status = db.Column(
        Enum('Menunggu pembayaran',
            'Diproses',
            'Batal',
            'Sampai tujuan',
            name='order_status'), nullable=False, default='Menunggu pembayaran')
    payment_file = db.Column(db.String(100), nullable=True)
    receipt_code = db.Column(db.String(50), nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)