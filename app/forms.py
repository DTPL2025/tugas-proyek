from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.models import User

class UserForm(ModelForm):
    class Meta:
        model = User
        include = ['username', 'password', 'role']

class RegisterForm(UserForm, FlaskForm):
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')],
                                     render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Sign Up')
