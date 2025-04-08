from datetime import datetime
import os
import secrets
from flask import url_for, render_template, flash, redirect, request
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, OrderForm, RegisterForm, ProductForm
from app.models import Order, User, Product
from flasgger import swag_from

def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_image.filename)
    image_fn = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/product_images', image_fn)
    form_image.save(image_path)
    return image_fn

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.route('/')
@swag_from('docs/home.yml')
def home():
    return render_template('home.jinja')

@app.route('/login', methods=['GET', 'POST'])
@swag_from('docs/login.yml')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    next_page = request.args.get('next')
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(next_page or url_for('home'))
        else:
            return render_template('login.jinja', form=form, error='Username atau password salah.')
    return render_template('login.jinja', form=form)

@app.route('/register', methods=['GET', 'POST'])
@swag_from('docs/register.yml')
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
@swag_from('docs/logout.yml')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/produk/buat', methods=['GET', 'POST'])
@login_required
@swag_from('docs/create_product.yml')
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
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            weight=form.weight.data,
            image_file=image_file,
            seller_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('Produk Anda telah dibuat!', 'success')
        return redirect(url_for('create_product'))
    return render_template('create_product.jinja', form=form)

@app.route('/produk/list')
@swag_from('docs/katalog_product.yml')
def katalog_product():
    products = Product.query.order_by(Product.name.asc()).all() 
    return render_template('katalog_product.jinja', products=products)

@app.route('/produk/saya')
@login_required
@swag_from('docs/etalase_product.yml')
def etalase_product():
    if current_user.role != 'Penjual':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template('etalase_product.jinja', products=products)

@app.route('/produk/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@swag_from('docs/edit_product.yml')
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Cek apakah pengguna memiliki izin untuk mengedit produk
    if product.seller_id != current_user.id:
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    form = ProductForm(obj=product)  # Mengisi form dengan data produk
    old_image = product.image_file  # Simpan nama gambar lama untuk perbandingan nanti

    if form.validate_on_submit():
        # Jika pengguna mengunggah gambar baru
        if form.image.data:
            new_image = save_image(form.image.data)  # Simpan gambar baru
            product.image_file = new_image  # Ganti dengan gambar baru

            # Hapus gambar lama jika bukan default.jpg
            if old_image and old_image != 'default.jpg':
                old_image_path = os.path.join(app.root_path, 'static/product_images', old_image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)  # Hapus gambar lama
        
        # Update informasi produk tanpa menghapus gambar
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.weight = form.weight.data

        db.session.commit()
        flash('Produk Anda telah diperbarui!', 'success')

        return redirect(url_for('etalase_product'))

    return render_template('edit_product.jinja', form=form, product=product)

@app.route('/produk/hapus_gambar/<int:product_id>', methods=['POST'])
@login_required
@swag_from('docs/delete_product_image.yml')
def delete_product_image(product_id):
    product = Product.query.get_or_404(product_id)

    # Pastikan hanya pemilik produk yang bisa menghapus gambar
    if product.seller_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus gambar ini.', 'danger')
        return redirect(url_for('home'))

    # Hapus gambar jika bukan default.jpg
    if product.image_file and product.image_file != 'default.jpg':
        image_path = os.path.join(app.root_path, 'static/product_images', product.image_file)
        if os.path.exists(image_path):
            os.remove(image_path)  # Hapus file gambar dari storage

        product.image_file = 'default.jpg'  # Reset ke gambar default
        db.session.commit()
        flash('Gambar berhasil dihapus.', 'success')

    return redirect(url_for('edit_product', product_id=product.id))

@app.route('/produk/hapus/<int:product_id>', methods=['POST'])
@login_required
@swag_from('docs/delete_product.yml')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Pastikan hanya pemilik produk yang bisa menghapus
    if product.seller_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus produk ini.', 'danger')
        return redirect(url_for('home'))

    # Path lengkap gambar yang akan dihapus
    if product.image_file:  # Pastikan gambar ada
        image_path = os.path.join(app.root_path, 'static/product_images', product.image_file)

        # Cek apakah file gambar ada sebelum menghapus
        if os.path.exists(image_path):
            os.remove(image_path)  # Hapus file gambar

    # Hapus produk dari database
    db.session.delete(product)
    db.session.commit()

    flash('Produk telah dihapus!', 'success')
    return redirect(url_for('etalase_product'))

@app.route('/produk/<int:product_id>')
@swag_from('docs/detail_product.yml')
def detail_product(product_id):
    # Query produk berdasarkan ID
    product = Product.query.get(product_id)

    # Jika produk tidak ditemukan, tampilkan pesan dan redirect
    if product is None:
        flash("Produk Tidak Ditemukan, kembali ke halaman produk.", "danger")
        return redirect(request.referrer or url_for('katalog_product'))

    return render_template('detail_product.jinja', product=product)

@app.route('/produk/checkout', methods=['GET', 'POST'])
@login_required
@swag_from('docs/checkout.yml')
def checkout():
    product_id = request.args.get('product_id', type=int)
    amount = request.args.get('amount', type=int) or 1
    product = Product.query.get_or_404(product_id)
    product_form = ProductForm(obj=product)
    
    if product is None or product.stock <= 0:
        flash("Maaf, produk tidak tersedia.", "danger")
        return redirect(url_for('home'))
    if product.stock < amount:
        return handle_stock_issue(product)
    form = OrderForm()
    form.date.data = datetime.utcnow()

    if form.validate_on_submit():
        if product.stock < amount:
            return handle_stock_issue(product)

        order = Order(
            destination=form.destination.data,
            product_id=product_id,
            name=product.name,
            total_price=product.price * amount,
            seller_name=product.seller.name,
            date=datetime.utcnow()
        )
        db.session.add(order)
        db.session.commit()
        order.receipt_code = f"EMJ-{order.id}-{datetime.utcnow().strftime('%Y%m%d')}"
        db.session.commit()
        product.stock -= amount
        db.session.commit()
        return redirect(url_for('payment', order_id=order.id))
    return render_template('checkout.jinja', form=form, product_form=product_form, amount=amount)

def handle_stock_issue(product):
    if product.stock == 0:
        flash("Maaf, stok habis.", "warning")
        return redirect(url_for('home'))
    else:
        flash("Maaf, stok tidak cukup.", "warning")
        return redirect(url_for('checkout', product_id=product.id, amount=product.stock))

@app.route('/produk/pembayaran/<int:order_id>', methods=['GET', 'POST'])
@login_required
@swag_from('docs/payment.yml')
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    return f'''
    payment for order id: {order.id}\n
    total price: {order.total_price}\n
    receipt: {order.receipt_code}
'''

@app.route('/produk/cari', methods=['GET'])
@login_required
@swag_from('docs/search_product.yml')
def search_product():
    if current_user.role != 'Penjual':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))
    
    query = request.args.get('q', '').strip()  # Ambil parameter pencarian dari query string
    if not query:
        flash('Masukkan kata kunci untuk mencari produk.', 'warning')
        return redirect(url_for('etalase_product'))
    
    # Cari produk berdasarkan nama yang dimiliki oleh penjual yang sedang login
    products = Product.query.filter(
        Product.seller_id == current_user.id,
        Product.name.ilike(f'%{query}%')
    ).all()
    
    if not products:
        flash('Tidak ada produk yang ditemukan.', 'info')
    return render_template('etalase_product.jinja', products=products)

    