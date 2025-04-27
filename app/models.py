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
    discussions = db.relationship('Discussion', back_populates='user', cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='user', cascade="all, delete-orphan")

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

    # Relasi dengan Discussion
    discussions = db.relationship('Discussion', back_populates='product', cascade="all, delete-orphan")


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
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product = db.relationship('Product', back_populates='discussions')
    user = db.relationship('User', back_populates='discussions')
    comments = db.relationship('Comment', back_populates='discussion', cascade="all, delete-orphan")
# Model Comment
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    discussion = db.relationship('Discussion', back_populates='comments')
    user = db.relationship('User', back_populates='comments')

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


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul_acara = db.Column(db.String(200), nullable=False)
    deskripsi_acara = db.Column(db.Text, nullable=False)
    gambar_acara = db.Column(db.String(255), nullable=False)
    tanggal_mulai = db.Column(db.Date, nullable=False)
    tanggal_berakhir = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f"<Event {self.judul_acara}>"