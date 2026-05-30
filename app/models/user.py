from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# Force SQLAlchemy à stocker/lire les VALEURS minuscules des enums
# (ex: 'admin') au lieu des NOMS (ex: 'ADMIN'), pour coller aux types
# ENUM PostgreSQL/Supabase et aux données existantes.
def enum_values(enum_cls):
    return [e.value for e in enum_cls]


class RoleEnum(str, Enum):
    ADMIN = 'admin'
    CONDUCTEUR = 'conducteur'
    CLIENT = 'client'


class PlanEnum(str, Enum):
    STARTER = 'starter'
    PRO = 'pro'
    ENTREPRISE = 'entreprise'


class StatutAboEnum(str, Enum):
    ACTIF = 'actif'
    SUSPENDU = 'suspendu'
    ANNULE = 'annule'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(RoleEnum, name='roleenum', values_callable=enum_values),
        nullable=False, default=RoleEnum.CLIENT)
    telephone = db.Column(db.String(30))
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(255))
    reset_expires = db.Column(db.DateTime)

    # Champs d'abonnement SaaS
    plan = db.Column(
        db.Enum(PlanEnum, name='planenum', values_callable=enum_values),
        default=PlanEnum.STARTER)
    statut_abo = db.Column(
        db.Enum(StatutAboEnum, name='statutaboenum', values_callable=enum_values),
        default=StatutAboEnum.ACTIF)
    date_souscription = db.Column(db.DateTime, default=datetime.utcnow)
    revenu_genere = db.Column(db.Numeric(10, 2), default=0)

    chantiers_responsable = db.relationship(
        'Chantier', backref='responsable', lazy='dynamic',
        foreign_keys='Chantier.responsable_id'
    )
    chantiers_client = db.relationship(
        'Chantier', backref='client', lazy='dynamic',
        foreign_keys='Chantier.client_id'
    )

    def set_password(self, password: str):
        self.mot_de_passe = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.mot_de_passe, password)

    @property
    def is_admin(self):
        return self.role == RoleEnum.ADMIN

    @property
    def is_conducteur(self):
        return self.role == RoleEnum.CONDUCTEUR

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'email': self.email,
            'role': self.role.value, 'telephone': self.telephone,
            'actif': self.actif,
            'plan': self.plan.value if self.plan else None,
            'statut_abo': self.statut_abo.value if self.statut_abo else None,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
        }

    def __repr__(self):
        return f'<User {self.email}>'
