# forms.py

from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import DateField, StringField, PasswordField, SubmitField, IntegerField, FileField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange, AnyOf
from app.models import User
from flask_wtf.file import FileAllowed
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

class RegisterForm(ModelForm, FlaskForm):
    class Meta:
        model = User
        include = ['role']
    
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Konfirmasi Password', validators=[DataRequired()])
    name = StringField('Nama Penjual')
    description = TextAreaField('Deskripsi Penjual')
    submit = SubmitField('Daftar')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username sudah digunakan, silahkan gunakan username lain.')
        
    def validate_confirm_password(self, confirm_password):
        if self.errors:
            return
        if self.password.data != confirm_password.data:
            raise ValidationError('Password dan konfirmasi password tidak sama.')
        
    def validate_role(self, role):
        if role.data == 'Penjual':
            if len(self.name.data) < 2 or len(self.name.data) > 50:
                raise ValidationError('Nama Penjual harus antara 2 dan 50 karakter.')
            if len(self.description.data) > 750:
                raise ValidationError('Deskripsi Penjual tidak boleh lebih dari 750 karakter.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ProductForm(FlaskForm):
    name = StringField('Nama Produk', validators=[DataRequired()])
    description = TextAreaField('Deskripsi Produk', validators=[Length(max=750)])
    price = IntegerField('Harga Produk (Rp)', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stok Produk (Unit)', validators=[DataRequired(), NumberRange(min=0)])
    image = FileField('Gambar Produk', validators=[FileAllowed(['jpg', 'png'], 'Format file tidak didukung! Harap unggah gambar dengan format JPG atau PNG.')])
    image_file = StringField('Nama Produk')
    weight = IntegerField('Berat Produk (gram)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Tambah Produk')

class CartUpdateForm(FlaskForm):
    quantity = IntegerField('Jumlah', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Perbarui Kuantitas')

class OrderStatusUpdateForm(FlaskForm):
    status = SelectField('Order Status', choices=[
        ('Menunggu Pembayaran', 'Menunggu Pembayaran'),
        ('Sedang Diproses', 'Sedang Diproses'),
        ('Dikirim', 'Dikirim'),
        ('Selesai', 'Selesai'),
    ], validators=[DataRequired()])
    submit = SubmitField('Update Status')

class RatingForm(FlaskForm):
    rating = SelectField('Rating', choices=[(1, '⭐'), (2, '⭐⭐'), (3, '⭐⭐⭐'), (4, '⭐⭐⭐⭐'), (5, '⭐⭐⭐⭐⭐')], coerce=int, validators=[DataRequired()])
    review = TextAreaField('Review', validators=[Length(max=500)])
    submit = SubmitField('Submit Rating')
    

class DiscussionForm(FlaskForm):
    title = StringField('Judul Diskusi', validators=[DataRequired(), Length(max=25)])
    content = TextAreaField('Isi Diskusi', validators=[DataRequired()])
    submit = SubmitField('Kirim Diskusi')

class CommentForm(FlaskForm):
    content = TextAreaField('Komentar', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Kirim Komentar')

class InfoPageForm(FlaskForm):
    category = SelectField('Kategori', choices=[
        ('Panduan Pembelian', 'Panduan Pembelian'),
        ('FAQ', 'FAQ'),
        ('Kontak Dukungan', 'Kontak Dukungan')
    ], validators=[DataRequired()])
    content = TextAreaField('Konten', validators=[DataRequired()])
    submit = SubmitField('Simpan')
