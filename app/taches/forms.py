from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class TacheForm(FlaskForm):
    chantier_id = SelectField('Chantier', coerce=int, validators=[DataRequired()])
    titre = StringField('Titre', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description')
    responsable_id = SelectField('Responsable', coerce=int, validators=[Optional()])
    priorite = SelectField('Priorité', choices=[
        ('faible', 'Faible'), ('moyenne', 'Moyenne'),
        ('haute', 'Haute'), ('critique', 'Critique'),
    ])
    statut = SelectField('Statut', choices=[
        ('a_faire', 'À faire'), ('en_cours', 'En cours'),
        ('termine', 'Terminé'), ('bloque', 'Bloqué'),
    ])
    date_limite = DateField('Date limite', validators=[Optional()])
    submit = SubmitField('Enregistrer')
