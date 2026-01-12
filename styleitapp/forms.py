from re import M

from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, PasswordField, TextAreaField, RadioField, FileField, SelectField

from wtforms.validators import DataRequired, Email, Length

class CustomerSignupForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()])
    lname = StringField('Last Name', validators=[DataRequired()])
    gender = RadioField('Gender', choices=[('male','Male'),('female','Female')], validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=32)]) 
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=8, max=32)])
    address = StringField('Contact Address', validators=[DataRequired()])
    pic = FileField('Upload profile picture', validators=[DataRequired()])
    state = SelectField('State', choices=[], coerce=str, validators=[DataRequired()])
    lga = StringField('LGA', validators=[DataRequired()])
    Signup = SubmitField('Sign Up')

class CustomerLoginForm(FlaskForm):
    email = StringField("Email: ", validators=[DataRequired(), Email()])
    pwd = PasswordField("Enter Password")
    loginbtn = SubmitField('Login')


class DesignerSignupForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()])
    lname = StringField('Last Name', validators=[DataRequired()])
    businessName = StringField('Business Name', validators=[DataRequired()])
    gender = RadioField('Gender', choices=[('male','Male'),('female','Female')])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=32)]) 
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=8, max=32)])
    address = StringField('Contact Address', validators=[DataRequired()])
    pic = FileField('Upload profile picture', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    lga = StringField('LGA', validators=[DataRequired()])
    Signup = SubmitField('Sign Up')

class DesignerLoginForm(FlaskForm):
    email = StringField("Your Email: ", validators=[DataRequired(), Email()])
    pwd = PasswordField("Enter Password")
    loginbtn = SubmitField('Login')

class AdminLoginForm(FlaskForm):
    email = StringField("Your Email: ", validators=[DataRequired(), Email()])
    pwd = PasswordField("Enter Password")
    loginbtn = SubmitField('Login')

class AdminSignupForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()])
    lname = StringField('Last Name', validators=[DataRequired()])
    secretword = StringField('Secretword', validators=[DataRequired()])
    gender = RadioField('Gender', choices=[('male','Male'),('female','Female')])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=32)]) 
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=8, max=32)])
    address = StringField('Contact Address', validators=[DataRequired()])
    pic = FileField('Upload profile picture', validators=[DataRequired()])
    Signup = SubmitField('Sign Up')