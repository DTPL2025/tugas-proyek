from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FileField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange, AnyOf
from app.models import User
from flask_wtf.file import FileAllowed

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
    image = FileField('Gambar Produk', validators=[FileAllowed(['jpg', 'png'])])
    weight = IntegerField('Berat Produk (gram)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Tambah Produk')