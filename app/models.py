from flask_login import UserMixin
from app import db
from sqlalchemy import Enum

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(Enum('Penjual', 'Pembeli', name='user_roles'), nullable=False, default='Pembeli')