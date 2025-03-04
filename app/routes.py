import os
import secrets
from flask import url_for, render_template, flash, redirect, request
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, RegisterForm, ProductForm
from app.models import User, Product

def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_image.filename)
    image_fn = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/product_images', image_fn)
    form_image.save(image_path)
    return image_fn

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('home.jinja', username=current_user.username)
    else:
        return render_template('home.jinja')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.jinja', form=form, error='Username atau password salah.')
    return render_template('login.jinja', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.jinja', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/produk/buat', methods=['GET', 'POST'])
@login_required
def create_product():
    if current_user.role != 'Penjual':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    form = ProductForm()
    if form.validate_on_submit():
        if form.image.data and form.image.data.filename != '':
            image_file = save_image(form.image.data)
        else:
            image_file = 'default.jpg'
        product = Product(name=form.name.data, price=form.price.data, stock=form.stock.data, weight=form.weight.data, image_file=image_file, seller_id=current_user.id)
        db.session.add(product)
        db.session.commit()
        flash('Produk Anda telah dibuat!', 'success')
        return redirect(url_for('create_product'))
    return render_template('create_product.jinja', form=form)
