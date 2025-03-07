from flask import render_template, redirect, url_for
from flask_login import current_user, login_required
from app import app, db, bcrypt
from app.forms import RegisterForm
from app.models import User

@app.route('/')
def home():
    return render_template('home.jinja')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.jinja', form=form)