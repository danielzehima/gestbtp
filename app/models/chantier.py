from datetime import datetime
from enum import Enum
from app.extensions import db
from app.models.user import enum_values


class StatutChantier(str, Enum):
    PREPARATION = 'preparation'
    EN_COURS = 'en_cours'
    SUSPENDU = 'suspendu'
    TERMINE = 'termine'


class Chantier(db.Model):
    __tablename__ = 'chantiers'

    id = db.Column(db.Integer, primary_key=True)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes.id'))  # entreprise propriétaire
    nom = db.Column(db.String(200), nullable=False)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    adresse = db.Column(db.String(255))
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    responsable_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    budget = db.Column(db.Numeric(14, 2), default=0)
    statut = db.Column(
        db.Enum(StatutChantier, name='statutchantier', values_callable=enum_values),
        default=StatutChantier.PREPARATION, nullable=False)
    date_debut = db.Column(db.Date)
    date_fin_prev = db.Column(db.Date)
    description = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    rapports = db.relationship('Rapport', backref='chantier', lazy='dynamic', cascade='all, delete-orphan')
    taches = db.relationship('Tache', backref='chantier', lazy='dynamic', cascade='all, delete-orphan')
    photos = db.relationship('Photo', backref='chantier', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'reference': self.reference,
            'adresse': self.adresse,
            'client_id': self.client_id, 'responsable_id': self.responsable_id,
            'client': self.client.nom if self.client else None,
            'responsable': self.responsable.nom if self.responsable else None,
            'budget': float(self.budget) if self.budget else 0,
            'statut': self.statut.value,
            'date_debut': self.date_debut.isoformat() if self.date_debut else None,
            'date_fin_prev': self.date_fin_prev.isoformat() if self.date_fin_prev else None,
            'description': self.description,
        }

    def __repr__(self):
        return f'<Chantier {self.reference} - {self.nom}>'
