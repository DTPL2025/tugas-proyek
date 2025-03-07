import os
import secrets
from flask import url_for, render_template, flash, redirect, request
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, RegisterForm, ProductForm
from app.models import User, Product
from flask import session

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
        return render_template('home.jinja', username=current_user.username, role=current_user.role)
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
        new_user = User(username=form.username.data, password=hashed_password, role=form.role.data, name=form.name.data, description=form.description.data)
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
        product = Product(name=form.name.data, description=form.description.data, price=form.price.data, stock=form.stock.data, weight=form.weight.data, image_file=image_file, seller_id=current_user.id)
        db.session.add(product)
        db.session.commit()
        flash('Produk Anda telah dibuat!', 'success')
        return redirect(url_for('create_product'))
    return render_template('create_product.jinja', form=form)

@app.route('/produk/saya', methods=['GET', 'POST'])
@login_required
def view_product_seller():
    if current_user.role != 'Penjual':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template('view_product_seller.jinja', products=products, username=current_user.username)

@app.route('/produk/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Cek apakah pengguna memiliki izin untuk mengedit produk
    if product.seller_id != current_user.id:
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    
    form = ProductForm(obj=product)  # Mengisi form dengan data produk

    if form.validate_on_submit():
        # Cek apakah ada gambar baru yang diunggah
        if form.image.data:
            image_file = save_image(form.image.data)
            product.image_file = image_file  # Simpan gambar baru
        
        # Update informasi produk
        product.name = form.name.data
        product.description = form.description.data  # Pastikan deskripsi juga diperbarui
        product.price = form.price.data
        product.stock = form.stock.data
        product.weight = form.weight.data
        
        db.session.commit()
        flash('Produk Anda telah diperbarui!', 'success')
        
        return redirect(url_for('view_product_seller'))
    session.pop('_flashes', None)
    return render_template('edit_product.jinja', form=form, product=product)


@app.route('/produk/hapus/<int:product_id>', methods=['GET', 'POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    db.session.delete(product)
    db.session.commit()
    flash('Produk Anda telah dihapus!', 'success')
    return redirect(url_for('view_product_seller'))

@app.route('/produk/list', methods=['GET'])
def view_product_buyer():
    products = Product.query.order_by(Product.name.asc()).all()  # Urut berdasarkan nama toko
    return render_template('view_product_buyer.jinja', products=products)


# @app.route('/produk/<int:product_id>')
# def detail_product(product_id):
#     product = Product.query.get_or_404(product_id)  # Ambil produk dari database
#     return render_template('detail_product.jinja', product=product)


# @app.route('/cart/add/<int:product_id>', methods=['POST'])
# @login_required
# def add_to_cart(product_id):
#     product = Product.query.get_or_404(product_id)
    
#     # Logika menambahkan produk ke keranjang
#     cart_item = Cart(user_id=current_user.id, product_id=product.id, quantity=1)
#     db.session.add(cart_item)
#     db.session.commit()

#     flash(f'Produk {product.name} telah ditambahkan ke keranjang!', 'success')
#     return redirect(url_for('view_cart'))
