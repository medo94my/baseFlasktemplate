# Import Form and RecaptchaField (optional)
# from flask_wtf import Form # , RecaptchaField

# Import Form elements such as StringField and BooleanField (optional)
from wtforms import Form, PasswordField,validators,StringField,ValidationError,FileField,SubmitField # BooleanField
from flask_wtf import FlaskForm
import email_validator
from flask_wtf.file import FileField, FileRequired, FileAllowed
from app.modules.models import User
from flask_login import current_user
# Import Form validators
# from wtforms.validators import Required, Email, EqualTo


# Define the login form (WTForms)

class LoginForm(FlaskForm):
    email    = StringField('Email', [validators.length(min=4, max=50),validators.DataRequired(message="you forgot your email!!"),validators.email()])
    password = PasswordField('Password', [
                validators.DataRequired(message='Must provide a password. ;-)'),validators.length(min=8, max=50)])
    submit=SubmitField('Signin')



class RegisterForm(FlaskForm):
    name = StringField('Name', [validators.length(min=4, max=50),])
    # username = StringField('Username', [validators.length(min=4, max=25)])
    email = StringField('Email', [validators.length(min=4, max=50),validators.email()])
    password = PasswordField('Password', [validators.DataRequired(message='Must provide a password. ;-)'),validators.length(min=8, max=50)])
    submit=SubmitField('Register')
    # confirm = PasswordField('Confirm Password')
    def validate_email(self ,email):
        user=User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email already exists')
class UpdateUserFrom(FlaskForm):
    email = StringField('Email', [validators.length(min=4, max=50),validators.email()])
    name = StringField('Name', [validators.length(min=4, max=50),])
    profile_picture = FileField('Profile Picture', validators=[ FileAllowed(['jpg', 'png'], 'Images only!')])
    submit=SubmitField('Update')
    def validate_email(self ,email):
        if current_user.email!=email.data:
            user=User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('This email already exists')
