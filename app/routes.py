from datetime import datetime
import os
import secrets
from flask import url_for, render_template, flash, redirect, request
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, RatingForm, RegisterForm, ProductForm, CartUpdateForm, OrderStatusUpdateForm
from app.models import Rating, User, Product, Cart, Order
from flasgger import swag_from
from app.models import OrderDetail
from app.models import Order, OrderDetail
from app.forms import OrderStatusUpdateForm
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
import os, time, secrets

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
    query = request.args.get('q', '').strip()
    if query:
        products = Product.query.filter(Product.name.ilike(f'%{query}%')).order_by(Product.name.asc()).all()
    else:
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
    query = request.args.get('q', '').strip()  # Ambil parameter pencarian dari query string
    if query:
        products = Product.query.filter(
            Product.seller_id == current_user.id,
            Product.name.ilike(f'%{query}%')
        ).all()
    else:
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

@app.route('/produk/<int:product_id>', methods=['GET', 'POST'])
@swag_from('docs/detail_product.yml')
def detail_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = RatingForm()

    has_ordered = False
    previous_rating = None

    if current_user.is_authenticated:
        # Check if the user has ordered this product
        has_ordered = db.session.query(OrderDetail).join(Order).filter(
            Order.user_id == current_user.id,
            OrderDetail.product_id == product_id
        ).count() > 0
        # Check if the user has already rated this product
        previous_rating = Rating.query.filter_by(user_id=current_user.id, product_id=product_id).first()

        if form.validate_on_submit() and has_ordered:
            # Check if the user has already rated this product
            existing_rating = Rating.query.filter_by(user_id=current_user.id, product_id=product_id).first()
            if existing_rating:
                existing_rating.rating = form.rating.data
                existing_rating.review = form.review.data
            else:
                new_rating = Rating(
                    user_id=current_user.id,
                    product_id=product_id,
                    rating=form.rating.data,
                    review=form.review.data
                )
                db.session.add(new_rating)
            db.session.commit()
            flash('Your rating has been submitted!', 'success')
            return redirect(url_for('detail_product', product_id=product_id))

        form.rating.data = previous_rating.rating if previous_rating else None
        form.review.data = previous_rating.review if previous_rating else None

    # Calculate rating statistics
    ratings = Rating.query.filter_by(product_id=product_id).all()
    average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
    rating_count = len(ratings)

    return render_template('detail_product.jinja', product=product, form=form, ratings=ratings, average_rating=average_rating, rating_count=rating_count, has_ordered=has_ordered, previous_rating=previous_rating)

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

def save_payment_proof(uploaded_file):
    import os, secrets, time
    from werkzeug.utils import secure_filename

    if not uploaded_file:
        return None

    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    filename = secure_filename(uploaded_file.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        return None  # Bisa diganti return error kalau perlu

    random_hex = secrets.token_hex(4)
    timestamp = int(time.time())
    new_filename = f"bukti_{timestamp}_{random_hex}{ext}"

    # ✅ Path folder tujuan
    upload_dir = os.path.join(app.root_path, 'static', 'bukti_pembayaran')

    # ✅ Auto-buat folder jika belum ada
    os.makedirs(upload_dir, exist_ok=True)

    # ✅ Path lengkap file
    upload_path = os.path.join(upload_dir, new_filename)

    # ✅ Simpan file
    uploaded_file.save(upload_path)

    return new_filename

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        address = request.form['address']
        payment_method = request.form['payment_method']
        bukti_file = request.files.get('bukti_pembayaran')

        # Simpan file jika metode transfer
        nama_file_bukti = save_payment_proof(bukti_file) if payment_method == 'transfer' else None

        # Buat dan simpan order
        order = Order(
            user_id=current_user.id,
            address=address,
            payment_method=payment_method,
            status='Menunggu Pembayaran',
            bukti_pembayaran=nama_file_bukti
        )
        db.session.add(order)
        db.session.commit()

        # Simpan detail order
        for item in cart_items:
            order_detail = OrderDetail(
                order_id=order.id,
                product_id=item.product.id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_detail)

        # Kosongkan keranjang
        db.session.query(Cart).filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash('Pesanan Anda telah diproses! Kami akan mengonfirmasi pesanan Anda segera.', 'success')
        return redirect(url_for('home'))

    return render_template('checkout.jinja', cart_items=cart_items)

@app.route('/order/manage')
@login_required
def manage_orders():
    if current_user.role != 'Penjual':  # Hanya penjual yang boleh mengakses halaman ini
        flash('Akses ditolak. Halaman ini hanya untuk Penjual.', 'danger')
        return redirect(url_for('home'))

    status_filter = request.args.get('status')

    if status_filter:
        orders = Order.query.options(joinedload(Order.user)).filter_by(status=status_filter).all()
    else:
        orders = Order.query.options(joinedload(Order.user)).all()

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
    if current_user.role == 'Penjual':
        orders = Order.query.options(joinedload(Order.user)).all()  # Penjual melihat semua pesanan
    else:
        orders = Order.query.options(joinedload(Order.user)).filter_by(user_id=current_user.id).all()  # Pembeli hanya lihat miliknya
    return render_template('view_orders.jinja', orders=orders)

@app.route('/order/status', methods=['GET'])
@login_required
def view_order_status():
    if current_user.role != 'Pembeli':
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('view_order_status.jinja', orders=orders)
