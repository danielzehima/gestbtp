from datetime import datetime, date
from enum import Enum
from app.extensions import db


class PrioriteTache(str, Enum):
    FAIBLE = 'faible'
    MOYENNE = 'moyenne'
    HAUTE = 'haute'
    CRITIQUE = 'critique'


class StatutTache(str, Enum):
    A_FAIRE = 'a_faire'
    EN_COURS = 'en_cours'
    TERMINE = 'termine'
    BLOQUE = 'bloque'


class Tache(db.Model):
    __tablename__ = 'taches'

    id = db.Column(db.Integer, primary_key=True)
    chantier_id = db.Column(db.Integer, db.ForeignKey('chantiers.id'), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priorite = db.Column(db.Enum(PrioriteTache), default=PrioriteTache.MOYENNE, nullable=False)
    statut = db.Column(db.Enum(StatutTache), default=StatutTache.A_FAIRE, nullable=False)
    date_limite = db.Column(db.Date)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    responsable = db.relationship('User', foreign_keys=[responsable_id])

    @property
    def en_retard(self):
        return (self.date_limite and self.date_limite < date.today()
                and self.statut != StatutTache.TERMINE)

    def to_dict(self):
        return {
            'id': self.id, 'chantier_id': self.chantier_id,
            'titre': self.titre, 'description': self.description,
            'responsable': self.responsable.nom if self.responsable else None,
            'responsable_id': self.responsable_id,
            'priorite': self.priorite.value, 'statut': self.statut.value,
            'date_limite': self.date_limite.isoformat() if self.date_limite else None,
            'en_retard': self.en_retard,
        }
