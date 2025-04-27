# routes.py

from datetime import datetime, date
import os, time, secrets
from flask import url_for, render_template, flash, redirect, request, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, bcrypt
from app.forms import LoginForm, RatingForm, RegisterForm, ProductForm, CartUpdateForm, OrderStatusUpdateForm, InfoPageForm, DiscussionForm, CommentForm
from app.models import Rating, User, Product, Cart, Order, Discussion, Comment, InfoPage, OrderDetail, Event
from flasgger import swag_from
from sqlalchemy.orm import joinedload
from sqlalchemy import func, distinct
from werkzeug.utils import secure_filename

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
    jumlah_penjual = User.query.filter_by(role='Penjual').count()
    jumlah_pembeli = User.query.filter_by(role='Pembeli').count()
    total_produk = Product.query.count()

    return render_template('home.jinja',
                       jumlah_penjual=jumlah_penjual,
                       jumlah_pembeli=jumlah_pembeli,
                       total_produk=total_produk)


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

    # 🔥 Cek stok produk sebelum lanjut
    if product.stock <= 0:
        flash('Gagal menambahkan ke keranjang: Stok produk habis.', 'danger')
        return redirect(url_for('katalog_product'))

    # Cari produk di cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        # Kalau sudah ada di cart, cek apakah stok mencukupi untuk nambah 1
        if product.stock < 1:
            flash('Tidak dapat menambahkan lebih banyak produk: Stok tidak cukup.', 'danger')
            return redirect(url_for('katalog_product'))
        cart_item.quantity += 1
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)

    # 🔥 Kurangi stok produk
    product.stock -= 1

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
        new_quantity = form.quantity.data
        old_quantity = cart_item.quantity
        product = Product.query.get(cart_item.product_id)

        if not product:
            flash('Produk tidak ditemukan.', 'danger')
            return redirect(url_for('view_cart'))

        quantity_diff = new_quantity - old_quantity

        if quantity_diff > 0:
            # User mau tambah quantity ➔ cek stok cukup tidak
            if product.stock < quantity_diff:
                flash('Stok produk tidak cukup untuk memperbarui jumlah.', 'danger')
                return redirect(url_for('view_cart'))
            product.stock -= quantity_diff
        elif quantity_diff < 0:
            # User mau mengurangi quantity ➔ kembalikan stok
            product.stock += abs(quantity_diff)

        cart_item.quantity = new_quantity
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

    # 🔥 Tambah stok produk kembali
    product = Product.query.get(cart_item.product_id)
    if product:
        product.stock += cart_item.quantity

    # Hapus item dari cart
    db.session.delete(cart_item)
    db.session.commit()
    flash('Produk berhasil dihapus dari keranjang dan stok dikembalikan.', 'success')
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
    if current_user.role != 'Penjual':  # Hanya penjual yang boleh akses
        flash('Akses ditolak. Halaman ini hanya untuk Penjual.', 'danger')
        return redirect(url_for('home'))

    status_filter = request.args.get('status')

    # 🔥 Cari semua order_detail produk milik penjual ini
    order_ids = db.session.query(OrderDetail.order_id).join(Product).filter(
        Product.seller_id == current_user.id
    ).distinct().all()

    # order_ids = list of tuple, ambil id nya
    order_ids = [oid[0] for oid in order_ids]

    if not order_ids:
        orders = []  # Kalau gak ada, kosongkan
    else:
        query = Order.query.options(joinedload(Order.user)).filter(Order.id.in_(order_ids))
        if status_filter:
            query = query.filter(Order.status == status_filter)
        orders = query.all()

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

@app.route('/produk/<int:product_id>', methods=['GET', 'POST'])
@swag_from('docs/detail_product.yml')
def detail_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Forms
    form = RatingForm()
    discussion_form = DiscussionForm()
    comment_form = CommentForm()

    has_ordered = False
    previous_rating = None

    if current_user.is_authenticated:
        has_ordered = db.session.query(OrderDetail).join(Order).filter(
            Order.user_id == current_user.id,
            OrderDetail.product_id == product_id
        ).count() > 0

        previous_rating = Rating.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    # 🔥 Handle Form POST
    if request.method == 'POST':
        if 'rating' in request.form:
            # Form Rating
            if form.validate_on_submit() and has_ordered:
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
                flash('Ulasan Anda telah dikirim!', 'success')
                return redirect(url_for('detail_product', product_id=product_id))

        elif 'title' in request.form:
            # Form Diskusi
            if discussion_form.validate_on_submit():
                new_discussion = Discussion(
                    title=discussion_form.title.data,
                    content=discussion_form.content.data,
                    product_id=product_id,
                    user_id=current_user.id
                )
                db.session.add(new_discussion)
                db.session.commit()
                flash('Diskusi berhasil diposting!', 'success')
                return redirect(url_for('detail_product', product_id=product_id))

        elif 'discussion_id' in request.form:
            # Form Komentar
            if comment_form.validate_on_submit():
                discussion_id = request.form.get('discussion_id')
                new_comment = Comment(
                    content=comment_form.content.data,
                    discussion_id=discussion_id,
                    user_id=current_user.id
                )
                db.session.add(new_comment)
                db.session.commit()
                flash('Komentar berhasil diposting!', 'success')
                return redirect(url_for('detail_product', product_id=product_id))

    # 🔥 Handle GET (load halaman)
    filter_diskusi = request.args.get('filter_diskusi', 'terbaru')

    if filter_diskusi == 'populer':
        discussions = db.session.query(Discussion).filter_by(product_id=product_id)\
            .outerjoin(Comment).group_by(Discussion.id)\
            .order_by(db.func.count(Comment.id).desc(), Discussion.created_at.desc()).all()
    else:
        discussions = Discussion.query.filter_by(product_id=product_id)\
            .order_by(Discussion.created_at.desc()).all()

    ratings = Rating.query.filter_by(product_id=product_id).all()
    average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
    rating_count = len(ratings)
    info_pages = InfoPage.query.filter_by(product_id=product_id).all()

    return render_template(
        'detail_product.jinja',
        product=product,
        form=form,
        ratings=ratings,
        average_rating=average_rating,
        rating_count=rating_count,
        has_ordered=has_ordered,
        previous_rating=previous_rating,
        discussion_form=discussion_form,
        comment_form=comment_form,
        discussions=discussions,
        info_pages=info_pages,
        filter_diskusi=filter_diskusi
    )



    # Tangani form diskusi
    if discussion_form.validate_on_submit() and 'title' in request.form:
        if current_user.is_authenticated:
            new_discussion = Discussion(
                title=discussion_form.title.data,
                content=discussion_form.content.data,
                product_id=product_id,
                user_id=current_user.id
            )
            db.session.add(new_discussion)
            db.session.commit()
            flash('Diskusi berhasil diposting!', 'success')
            return redirect(url_for('detail_product', product_id=product_id))

    # Tangani form komentar
    if comment_form.validate_on_submit() and 'discussion_id' in request.form:
        if current_user.is_authenticated:
            discussion_id = request.form.get('discussion_id')
            new_comment = Comment(
                content=comment_form.content.data,
                discussion_id=discussion_id,
                user_id=current_user.id
            )
            db.session.add(new_comment)
            db.session.commit()
            flash('Komentar berhasil diposting!', 'success')
            return redirect(url_for('detail_product', product_id=product_id))

    # Hitung statistik rating
    ratings = Rating.query.filter_by(product_id=product_id).all()
    average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
    rating_count = len(ratings)

    # Ambil semua diskusi produk
    discussions = Discussion.query.filter_by(product_id=product_id).all()

    # Ambil info pages (kalau ada)
    info_pages = InfoPage.query.filter_by(product_id=product_id).all()

    return render_template(
        'detail_product.jinja',
        product=product,
        form=form,
        ratings=ratings,
        average_rating=average_rating,
        rating_count=rating_count,
        has_ordered=has_ordered,
        previous_rating=previous_rating,
        discussion_form=discussion_form,
        comment_form=comment_form,
        discussions=discussions,
        info_pages=info_pages
    )

  
# Route for deleting a discussion
@app.route('/discussion/delete/<int:discussion_id>', methods=['POST'])
@login_required
def delete_discussion(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)

    if discussion.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus diskusi ini.', 'danger')
        return redirect(url_for('detail_product', product_id=discussion.product_id))

    # Hapus semua komentar di diskusi ini
    Comment.query.filter_by(discussion_id=discussion.id).delete()

    # Hapus diskusi
    db.session.delete(discussion)
    db.session.commit()
    flash('Diskusi dan semua komentarnya berhasil dihapus.', 'success')
    return redirect(url_for('detail_product', product_id=discussion.product_id))

# Route for editing a discussion
@app.route('/discussion/edit/<int:discussion_id>', methods=['GET', 'POST'])
@login_required
def edit_discussion(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)

    # Ensure the user is the owner of the discussion
    if discussion.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk mengedit diskusi ini.', 'danger')
        return redirect(url_for('detail_product', product_id=discussion.product_id))

    form = DiscussionForm(obj=discussion)
    if form.validate_on_submit():
        discussion.title = form.title.data
        discussion.content = form.content.data
        db.session.commit()
        flash('Diskusi berhasil diperbarui!', 'success')
        return redirect(url_for('detail_product', product_id=discussion.product_id))

    return render_template('edit_discussion.jinja', form=form, discussion=discussion)
@app.route('/comment/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Pastikan hanya pemilik komentar yang bisa menghapus
    if comment.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus komentar ini.', 'danger')
        return redirect(url_for('home'))

    product_id = comment.discussion.product.id  # Ambil id produk lewat diskusi

    db.session.delete(comment)
    db.session.commit()
    flash('Komentar berhasil dihapus.', 'success')
    return redirect(url_for('detail_product', product_id=product_id))

@app.route('/info_page')
def info_page():
    category = request.args.get('category')
    query = request.args.get('q')
    product_id = request.args.get('product_id')

    info_query = InfoPage.query

    if product_id:
        info_query = info_query.filter_by(product_id=product_id)

    if category:
        info_query = info_query.filter_by(category=category)

    if query:
        info_query = info_query.filter(InfoPage.content.ilike(f'%{query}%'))

    info_pages = info_query.all()

    return render_template('info_page.jinja', info_pages=info_pages, query=query or '', category=category)

@app.route('/product/<int:product_id>/info/create', methods=['GET', 'POST'])
def create_info_page(product_id):
    form = InfoPageForm()
    if form.validate_on_submit():
        new_info = InfoPage(
            product_id=product_id,
            category=form.category.data,
            content=form.content.data
        )
        db.session.add(new_info)
        db.session.commit()
        flash('Informasi berhasil ditambahkan.', 'success')
        return redirect(url_for('detail_product', product_id=product_id))
    return render_template('create_info_page.jinja', form=form, product_id=product_id)

# EDIT
@app.route('/info/edit/<int:info_id>', methods=['GET', 'POST'])
def edit_info_page(info_id):
    info = InfoPage.query.get_or_404(info_id)
    form = InfoPageForm(obj=info)  # pre-fill form

    if form.validate_on_submit():
        info.category = form.category.data
        info.content = form.content.data
        db.session.commit()
        flash('Informasi berhasil diperbarui.', 'success')
        return redirect(url_for('detail_product', product_id=info.product_id))

    return render_template('edit_info_page.jinja', form=form, info=info)

# DELETE
@app.route('/info/delete/<int:info_id>', methods=['POST'])
def delete_info_page(info_id):
    info = InfoPage.query.get_or_404(info_id)
    product_id = info.product_id
    db.session.delete(info)
    db.session.commit()
    flash('Informasi berhasil dihapus.', 'success')
    return redirect(url_for('detail_product', product_id=product_id))

@app.route('/event/load_all')
def load_all_events():
    today = date.today()

    try:
        # Event sedang berlangsung
        current_events = Event.query.filter(
            Event.tanggal_mulai <= today,
            Event.tanggal_berakhir >= today
        ).order_by(Event.tanggal_mulai.asc()).all()

        # Event yang akan datang
        upcoming_events = Event.query.filter(
            Event.tanggal_mulai > today
        ).order_by(Event.tanggal_mulai.asc()).all()

        def serialize(event):
            return {
                'id': event.id,
                'judul_acara': event.judul_acara,
                'deskripsi_acara': event.deskripsi_acara,
                'gambar_acara': event.gambar_acara,
                'tanggal_mulai': event.tanggal_mulai.strftime('%Y-%m-%d'),
                'tanggal_berakhir': event.tanggal_berakhir.strftime('%Y-%m-%d'),
            }

        return jsonify({
            'bulan_ini': [serialize(e) for e in current_events],
            'tahun_ini': [serialize(e) for e in upcoming_events]
        })
    except Exception as e:
        return jsonify({'error': 'Gagal memuat data'}), 500


@app.route('/event')
def event_page():
    try:
        today = date.today()

        # Event yang sedang berlangsung
        current_events = Event.query.filter(
            Event.tanggal_mulai <= today,
            Event.tanggal_berakhir >= today
        ).order_by(Event.tanggal_mulai.asc()).all()

        # Event yang akan datang
        upcoming_events = Event.query.filter(
            Event.tanggal_mulai > today
        ).order_by(Event.tanggal_mulai.asc()).all()

        return render_template("event.jinja", bulan_ini=current_events, tahun_ini=upcoming_events)
    except Exception as e:
        return render_template("event.jinja", error="Gagal memuat data event.")


@app.route('/event/create', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        judul = request.form['judul_acara']
        deskripsi = request.form['deskripsi_acara']
        tanggal_mulai = datetime.strptime(request.form['tanggal_mulai'], "%Y-%m-%d").date()
        tanggal_berakhir = datetime.strptime(request.form['tanggal_berakhir'], "%Y-%m-%d").date()
        file = request.files['gambar_acara']

        # Simpan file
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.root_path, 'static', 'event_images')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        # Simpan ke database
        event = Event(
            judul_acara=judul,
            deskripsi_acara=deskripsi,
            tanggal_mulai=tanggal_mulai,
            tanggal_berakhir=tanggal_berakhir,
            gambar_acara=filename
        )
        db.session.add(event)
        db.session.commit()
        flash('Event berhasil ditambahkan!', 'success')
        return redirect(url_for('event_page'))

    return render_template('create_event.jinja')

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.jinja', event=event)

@app.route('/dashboard/analytics')
@login_required
def analytic_pembeli():
    if current_user.role != 'Penjual':
        flash('Halaman ini hanya dapat diakses oleh Penjual.', 'danger')
        return redirect(url_for('home'))

    produk_penjual = Product.query.filter_by(seller_id=current_user.id).all()
    data = []
    total_omset = 0
    total_penjualan = 0

    for produk in produk_penjual:
        jumlah_pembeli = db.session.query(
            func.count(distinct(Order.user_id))
        ).join(OrderDetail, Order.id == OrderDetail.order_id
        ).filter(
            OrderDetail.product_id == produk.id,
            Order.status == 'Selesai'
        ).scalar()

        jumlah_terjual = db.session.query(
            func.coalesce(func.sum(OrderDetail.quantity), 0)
        ).join(Order, Order.id == OrderDetail.order_id
        ).filter(
            OrderDetail.product_id == produk.id,
            Order.status == 'Selesai'
        ).scalar()

        omset = db.session.query(
            func.coalesce(func.sum(OrderDetail.quantity * OrderDetail.price), 0)
        ).join(Order, Order.id == OrderDetail.order_id
        ).filter(
            OrderDetail.product_id == produk.id,
            Order.status == 'Selesai'
        ).scalar()

        average_rating = db.session.query(func.avg(Rating.rating)).filter(Rating.product_id == produk.id).scalar()
        rating_count = db.session.query(func.count(Rating.rating)).filter(Rating.product_id == produk.id).scalar()

        total_omset += omset or 0
        total_penjualan += jumlah_terjual or 0

        data.append({
            'id': produk.id,
            'name': produk.name,
            'image_file': produk.image_file,
            'description': produk.description,
            'price': produk.price,
            'stock': produk.stock,
            'jumlah_pembeli': jumlah_pembeli or 0,
            'jumlah_terjual': jumlah_terjual or 0,
            'omset': omset or 0,
            'average_rating': round(average_rating or 0, 1),
            'rating_count': rating_count or 0
        })

    return render_template(
        'dashboard_analytic.jinja',
        products=data,
        total_omset=total_omset,
        total_penjualan=total_penjualan
    )

@app.route('/informasi')
def view_informasi():
    category = request.args.get('category')
    query = request.args.get('q')

    info_query = InfoPage.query

    if category:
        info_query = info_query.filter_by(category=category)

    if query:
        info_query = info_query.filter(InfoPage.content.ilike(f'%{query}%'))

    info_pages = info_query.all()

    return render_template('view_informasi.jinja', info_pages=info_pages, query=query or '', category=category)
