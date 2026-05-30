from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import TextAreaField, SelectField, DateField, SubmitField, StringField
from wtforms.validators import DataRequired, Optional


class RapportForm(FlaskForm):
    chantier_id = SelectField('Chantier', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    meteo = SelectField('Météo', choices=[
        ('Ensoleillé', '☀ Ensoleillé'), ('Nuageux', '⛅ Nuageux'),
        ('Pluvieux', '🌧 Pluvieux'), ('Orageux', '⛈ Orageux'),
        ('Neigeux', '❄ Neigeux'), ('Venteux', '💨 Venteux'),
    ])
    travaux_realises = TextAreaField('Travaux réalisés')
    difficultes = TextAreaField('Difficultés rencontrées')
    main_oeuvre = TextAreaField("Main d'œuvre présente")
    observations = TextAreaField('Observations')
    photos = MultipleFileField('Photos', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images uniquement')
    ])
    documents = MultipleFileField('Documents')
    submit = SubmitField('Enregistrer le rapport')
