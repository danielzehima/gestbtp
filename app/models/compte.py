"""Compte = entreprise BTP cliente (tenant). C'est l'entité qui porte
l'ABONNEMENT. Les utilisateurs (équipe) et les chantiers lui sont rattachés,
et les limites de forfait s'appliquent au total de l'entreprise.
"""
from datetime import datetime
from app.extensions import db
from app.models.user import PlanEnum, StatutAboEnum, enum_values


class Compte(db.Model):
    __tablename__ = 'comptes'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)            # nom de l'entreprise
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # propriétaire / contact principal

    # Abonnement (source de vérité pour la facturation)
    plan = db.Column(
        db.Enum(PlanEnum, name='planenum', values_callable=enum_values),
        default=PlanEnum.GRATUIT, nullable=False)
    statut_abo = db.Column(
        db.Enum(StatutAboEnum, name='statutaboenum', values_callable=enum_values),
        default=StatutAboEnum.ACTIF, nullable=False)
    date_souscription = db.Column(db.DateTime, default=datetime.utcnow)
    revenu_genere = db.Column(db.Numeric(12, 2), default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Membres de l'entreprise (équipe)
    membres = db.relationship(
        'User', backref='compte', lazy='dynamic',
        foreign_keys='User.compte_id')
    owner = db.relationship('User', foreign_keys=[owner_id])

    @property
    def nb_membres(self):
        return self.membres.count()

    @property
    def nb_chantiers(self):
        from app.models.chantier import Chantier
        return Chantier.query.filter_by(compte_id=self.id).count()

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom,
            'plan': self.plan.value, 'statut_abo': self.statut_abo.value,
            'revenu_genere': float(self.revenu_genere or 0),
            'nb_membres': self.nb_membres, 'nb_chantiers': self.nb_chantiers,
        }
