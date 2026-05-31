from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class MembreForm(FlaskForm):
    nom = StringField('Nom complet', validators=[DataRequired(), Length(2, 120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telephone = StringField('Téléphone', validators=[Optional()])
    role = SelectField('Rôle', choices=[
        ('conducteur', 'Conducteur de travaux'),
        ('client', 'Client'),
    ])
    password = PasswordField('Mot de passe initial', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Ajouter le membre')
