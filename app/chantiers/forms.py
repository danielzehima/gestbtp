from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class ChantierForm(FlaskForm):
    nom = StringField('Nom du chantier', validators=[DataRequired(), Length(2, 200)])
    reference = StringField('Référence', validators=[DataRequired(), Length(2, 50)])
    adresse = StringField('Adresse')
    client_id = SelectField('Client', coerce=int, validators=[Optional()])
    responsable_id = SelectField('Responsable', coerce=int, validators=[Optional()])
    budget = DecimalField('Budget (€)', places=2, validators=[Optional()])
    statut = SelectField('Statut', choices=[
        ('preparation', 'Préparation'), ('en_cours', 'En cours'),
        ('suspendu', 'Suspendu'), ('termine', 'Terminé'),
    ])
    date_debut = DateField('Date début', validators=[Optional()])
    date_fin_prev = DateField('Date fin prévisionnelle', validators=[Optional()])
    description = TextAreaField('Description')
    submit = SubmitField('Enregistrer')
