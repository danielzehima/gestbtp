from datetime import datetime, date
from app.extensions import db


class Rapport(db.Model):
    __tablename__ = 'rapports'

    id = db.Column(db.Integer, primary_key=True)
    chantier_id = db.Column(db.Integer, db.ForeignKey('chantiers.id'), nullable=False)
    auteur_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.Date, default=date.today, nullable=False)
    meteo = db.Column(db.String(50))
    travaux_realises = db.Column(db.Text)
    difficultes = db.Column(db.Text)
    main_oeuvre = db.Column(db.Text)
    observations = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    auteur = db.relationship('User', foreign_keys=[auteur_id])
    photos = db.relationship('Photo', secondary='rapport_photos', backref='rapports')
    documents = db.relationship('RapportDocument', backref='rapport', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'chantier_id': self.chantier_id,
            'auteur': self.auteur.nom if self.auteur else None,
            'date': self.date.isoformat() if self.date else None,
            'meteo': self.meteo, 'travaux_realises': self.travaux_realises,
            'difficultes': self.difficultes, 'main_oeuvre': self.main_oeuvre,
            'observations': self.observations,
        }


rapport_photos = db.Table(
    'rapport_photos',
    db.Column('rapport_id', db.Integer, db.ForeignKey('rapports.id'), primary_key=True),
    db.Column('photo_id', db.Integer, db.ForeignKey('photos.id'), primary_key=True),
)


class RapportDocument(db.Model):
    __tablename__ = 'rapport_documents'
    id = db.Column(db.Integer, primary_key=True)
    rapport_id = db.Column(db.Integer, db.ForeignKey('rapports.id'), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin = db.Column(db.String(500), nullable=False)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
