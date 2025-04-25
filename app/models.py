from datetime import datetime
from flask_login import UserMixin
from app import db
from sqlalchemy import Enum

# Model Order
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Menunggu Pembayaran')
    bukti_pembayaran = db.Column(db.String(255), nullable=True)

    order_details = db.relationship('OrderDetail', backref='order', lazy=True)

# Model User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    role = db.Column(Enum('Penjual', 'Pembeli', name='user_roles'), nullable=False, default='Pembeli')

    products = db.relationship('Product', backref='seller', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    discussions = db.relationship('Discussion', backref='user_discussions', lazy=True)
    comments = db.relationship('Comment', backref='user_comments', lazy=True)

# Model Product
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

    # Relasi dengan Comment
    comments = db.relationship('Comment', back_populates='product', lazy=True)

    # Relasi dengan Discussion
    discussions = db.relationship('Discussion', backref='product_discussions', lazy=True)

# Model Cart
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship('User', backref='cart_items', lazy=True)
    product = db.relationship('Product', backref='carts', lazy=True)

# Model OrderDetail
class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)

# Model Rating
class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1 to 5
    review = db.Column(db.Text, nullable=True)  # Optional written review
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='ratings', lazy=True)
    product = db.relationship('Product', backref='ratings', lazy=True)

# Model Discussion
class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='discussions_product', lazy=True)
    user = db.relationship('User', backref='discussions_user', lazy=True)

# Model Comment
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', back_populates='comments')

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # ForeignKey yang hilang
    user = db.relationship('User', backref='user_comments', lazy=True)

# Model InfoPage (FAQ dan Panduan Pembelian)
class InfoPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    product = db.relationship('Product', backref='info_pages')

    @classmethod
    def get_info_by_category(cls, category):
        return cls.query.filter_by(category=category).all()


