"""Devis & Factures BTP : créés par une entreprise pour SES clients.
Rattachés à l'entreprise (compte) et éventuellement à un chantier.
"""
from datetime import datetime, date
from enum import Enum
from app.extensions import db
from app.models.user import enum_values


class TypeDocument(str, Enum):
    DEVIS = 'devis'
    FACTURE = 'facture'


class StatutDocument(str, Enum):
    BROUILLON = 'brouillon'
    ENVOYE = 'envoye'
    ACCEPTE = 'accepte'      # devis accepté
    REFUSE = 'refuse'        # devis refusé
    PAYE = 'paye'            # facture payée
    ANNULE = 'annule'


class Document(db.Model):
    """Un devis ou une facture."""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes.id'), nullable=False)
    chantier_id = db.Column(db.Integer, db.ForeignKey('chantiers.id'))  # optionnel
    type = db.Column(db.Enum(TypeDocument, name='typedocument', values_callable=enum_values),
                     nullable=False, default=TypeDocument.DEVIS)
    numero = db.Column(db.String(40), nullable=False)            # ex: DEV-2026-0001

    # Client (texte libre : nom + coordonnées)
    client_nom = db.Column(db.String(200), nullable=False)
    client_adresse = db.Column(db.String(300))
    client_email = db.Column(db.String(120))
    client_tel = db.Column(db.String(40))

    date_emission = db.Column(db.Date, default=date.today)
    date_echeance = db.Column(db.Date)
    statut = db.Column(db.Enum(StatutDocument, name='statutdocument', values_callable=enum_values),
                       nullable=False, default=StatutDocument.BROUILLON)
    tva_taux = db.Column(db.Numeric(5, 2), default=18)           # % (18% Côte d'Ivoire par défaut)
    notes = db.Column(db.Text)
    conditions = db.Column(db.Text)                              # conditions de paiement / mentions
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    chantier = db.relationship('Chantier')
    compte = db.relationship('Compte')
    lignes = db.relationship('LigneDocument', backref='document',
                             cascade='all, delete-orphan', order_by='LigneDocument.position')

    # ----- Calculs -----
    @property
    def total_ht(self):
        return sum((l.total_ligne for l in self.lignes), 0)

    @property
    def montant_tva(self):
        return round(float(self.total_ht) * float(self.tva_taux or 0) / 100, 2)

    @property
    def total_ttc(self):
        return round(float(self.total_ht) + self.montant_tva, 2)

    @property
    def est_facture(self):
        return self.type == TypeDocument.FACTURE


class LigneDocument(db.Model):
    """Ligne d'un devis/facture (désignation, qté, prix unitaire)."""
    __tablename__ = 'lignes_document'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    position = db.Column(db.Integer, default=0)
    designation = db.Column(db.String(300), nullable=False)
    quantite = db.Column(db.Numeric(12, 2), default=1)
    prix_unitaire = db.Column(db.Numeric(14, 2), default=0)
    unite = db.Column(db.String(20))                            # m², ml, u, forfait...

    @property
    def total_ligne(self):
        return round(float(self.quantite or 0) * float(self.prix_unitaire or 0), 2)
