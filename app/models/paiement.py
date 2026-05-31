"""Historique des paiements / transactions GenuisPay par entreprise."""
from datetime import datetime
from enum import Enum
from app.extensions import db
from app.models.user import enum_values


class StatutPaiement(str, Enum):
    EN_ATTENTE = 'en_attente'
    REUSSI = 'reussi'
    ECHOUE = 'echoue'


class Paiement(db.Model):
    __tablename__ = 'paiements'

    id = db.Column(db.Integer, primary_key=True)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes.id'), nullable=False)
    reference = db.Column(db.String(80), unique=True, nullable=False, index=True)  # notre référence
    provider_ref = db.Column(db.String(120))                                       # référence GenuisPay
    plan = db.Column(db.String(20))                                                # forfait visé
    montant = db.Column(db.Numeric(12, 2), default=0)
    statut = db.Column(
        db.Enum(StatutPaiement, name='statutpaiement', values_callable=enum_values),
        default=StatutPaiement.EN_ATTENTE, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_paiement = db.Column(db.DateTime)

    compte = db.relationship('Compte', backref=db.backref('paiements', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id, 'reference': self.reference, 'plan': self.plan,
            'montant': float(self.montant or 0), 'statut': self.statut.value,
            'date': self.date_creation.isoformat() if self.date_creation else None,
        }
