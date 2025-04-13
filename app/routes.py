from datetime import datetime
import os
import secrets
from flask import url_for, render_template, flash, redirect, request
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, RegisterForm, ProductForm, CartUpdateForm, OrderStatusUpdateForm
from app.models import User, Product, Cart, Order
from flasgger import swag_from
from app.models import OrderDetail
from app.models import Order, OrderDetail
from app.forms import OrderStatusUpdateForm
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

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    # Cek apakah produk sudah ada di cart pengguna
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        # Jika produk sudah ada di cart, tambahkan kuantitasnya
        cart_item.quantity += 1
    else:
        # Jika produk belum ada di cart, tambahkan produk baru ke cart
        cart_item = Cart(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash('Produk berhasil ditambahkan ke keranjang!', 'success')
    return redirect(url_for('katalog_product'))


@app.route('/cart/update/<int:cart_item_id>', methods=['GET', 'POST'])
@login_required
@swag_from('docs/cart_update.yml')
def update_cart(cart_item_id):
    cart_item = Cart.query.get_or_404(cart_item_id)
    form = CartUpdateForm()

    if form.validate_on_submit():
        cart_item.quantity = form.quantity.data
        db.session.commit()
        flash('Kuantitas produk telah diperbarui!', 'success')
        return redirect(url_for('view_cart'))

    return render_template('update_cart.jinja', form=form, cart_item=cart_item)

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

@app.route('/cart', methods=['GET', 'POST'])
@login_required
@swag_from('docs/cart_view.yml')
def view_cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    # Membuat form untuk setiap item cart
    form = {}
    for item in cart_items:
        form[item.id] = CartUpdateForm()

    if not cart_items:
        flash('Keranjang Anda kosong.', 'info')
    
    if request.method == 'POST':
        # Proses pembaruan kuantitas di cart
        for item in cart_items:
            if form[item.id].validate_on_submit():
                item.quantity = form[item.id].quantity.data
                db.session.commit()
                flash('Kuantitas produk telah diperbarui!', 'success')

    return render_template('cart.jinja', cart_items=cart_items, form=form)

    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    # Membuat form untuk setiap item cart
    form = {}
    for item in cart_items:
        form[item.id] = CartUpdateForm()

    if not cart_items:
        flash('Keranjang Anda kosong.', 'info')
    
    if request.method == 'POST':
        # Proses pembaruan kuantitas di cart
        for item in cart_items:
            if form[item.id].validate_on_submit():
                item.quantity = form[item.id].quantity.data
                db.session.commit()
                flash('Kuantitas produk telah diperbarui!', 'success')

    return render_template('cart.jinja', cart_items=cart_items, form=form)

@app.route('/cart/delete/<int:cart_item_id>', methods=['POST'])
@login_required
@swag_from('docs/cart_delete.yml')
def delete_cart_item(cart_item_id):
    cart_item = Cart.query.get_or_404(cart_item_id)

    # Pastikan hanya pemilik cart yang dapat menghapus
    if cart_item.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus item ini.', 'danger')
        return redirect(url_for('view_cart'))

    db.session.delete(cart_item)
    db.session.commit()
    flash('Produk berhasil dihapus dari keranjang.', 'success')
    return redirect(url_for('view_cart'))
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        # Ambil data dari form
        address = request.form['address']
        payment_method = request.form['payment_method']

        # Buat pesanan baru
        order = Order(user_id=current_user.id, address=address, payment_method=payment_method, status='Menunggu Pembayaran')
        
        # Simpan pesanan baru terlebih dahulu ke database
        db.session.add(order)
        db.session.commit()  # Pastikan pesanan sudah disimpan sebelum detail pesanan ditambahkan

        # Tambahkan detail pesanan untuk setiap item di keranjang
        for item in cart_items:
            order_detail = OrderDetail(
                order_id=order.id,  # Kini order_id sudah ada setelah commit
                product_id=item.product.id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_detail)

        # Hapus isi keranjang setelah pesanan diproses
        db.session.query(Cart).filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash('Pesanan Anda telah diproses! Kami akan mengonfirmasi pesanan Anda segera.', 'success')
        return redirect(url_for('home'))  # Redirect ke halaman utama atau halaman yang diinginkan

    return render_template('checkout.jinja', cart_items=cart_items)

@app.route('/order/manage', methods=['GET', 'POST'])
@login_required
def manage_orders():
    if current_user.role != 'Penjual':  # Hanya penjual yang boleh mengakses halaman ini
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    orders = Order.query.all()  # Ambil semua order dari database

    return render_template('manage_orders.jinja', orders=orders)
@app.route('/order/update/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
   

    order = Order.query.get_or_404(order_id)
    form = OrderStatusUpdateForm()

    if form.validate_on_submit():
        order.status = form.status.data
        db.session.commit()
        flash('Status pesanan telah diperbarui!', 'success')
        return redirect(url_for('view_orders'))

    return render_template('update_order.jinja', form=form, order=order)

@app.route('/orders')
@login_required
def view_orders():
    if current_user.role != 'Penjual':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('view_orders.jinja', orders=orders)
@app.route('/order/status', methods=['GET'])
@login_required
def view_order_status():
    if current_user.role != 'Pembeli':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('view_order_status.jinja', orders=orders)

@app.route('/produk/cari-katalog', methods=['GET'])
@swag_from('docs/search_katalog.yml')
def search_katalog():
    query = request.args.get('q', '').strip()
    if not query:
        flash('Masukkan kata kunci untuk pencarian.', 'warning')
        return redirect(url_for('katalog_product'))
    
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).order_by(Product.name.asc()).all()
    if not products:
        flash('Tidak ada produk yang ditemukan.', 'info')
        
    return render_template('katalog_product.jinja', products=products)
  
@app.route('/produk/cari-etalase', methods=['GET'])
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
