from flask_login import UserMixin
from app import db
from sqlalchemy import Enum

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(Enum('Penjual', 'Pembeli', name='user_roles'), nullable=False, default='Pembeli')
    products = db.relationship('Product', backref='seller', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)