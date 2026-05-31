"""Gestion des comptes-entreprises (tenants)."""
from app.extensions import db
from app.models.compte import Compte


def get_or_create_compte(user, nom=None):
    """Retourne l'entreprise (Compte) de l'utilisateur, en la créant si besoin.
    L'utilisateur devient propriétaire du compte fraîchement créé."""
    if getattr(user, 'compte_id', None) and user.compte:
        return user.compte

    compte = Compte(
        nom=nom or f"Entreprise de {user.nom}",
        owner_id=user.id,
    )
    # On reprend l'éventuel abonnement déjà posé sur l'utilisateur (compat.)
    if getattr(user, 'plan', None):
        compte.plan = user.plan
    if getattr(user, 'statut_abo', None):
        compte.statut_abo = user.statut_abo
    db.session.add(compte)
    db.session.flush()  # pour obtenir compte.id
    user.compte_id = compte.id
    db.session.commit()
    return compte
