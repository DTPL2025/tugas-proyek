from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange
from app.models import User
from flask_wtf.file import FileAllowed

class RegisterForm(ModelForm, FlaskForm):
    class Meta:
        model = User
        include = ['username', 'role']

    password = PasswordField('Password', validators=[DataRequired()],
                             render_kw={"placeholder": "Password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')],
                                     render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Sign Up')
    
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField('Password', validators=[DataRequired()],
                             render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    price = IntegerField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    image = FileField('Product Image', validators=[FileAllowed(['jpg', 'png'])])
    weight = IntegerField('Weight (gr)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Product')