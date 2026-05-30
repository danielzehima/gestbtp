from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')


class RegisterForm(FlaskForm):
    nom = StringField('Nom complet', validators=[DataRequired(), Length(2, 120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telephone = StringField('Téléphone')
    role = SelectField('Rôle', choices=[
        ('conducteur', 'Conducteur de travaux'),
        ('client', 'Client'),
    ])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField('Confirmer', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("S'inscrire")


class ForgotForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Envoyer le lien')


class ResetForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField('Confirmer', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Réinitialiser')
