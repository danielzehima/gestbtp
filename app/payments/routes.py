"""Intégration de l'agrégateur de paiement GenuisPay.

Route principale : Webhook qui écoute les notifications de paiement de
GenuisPay et met à jour automatiquement l'abonnement du client.

Sécurité : la signature HMAC-SHA256 de chaque requête est vérifiée avec
le secret partagé (GENIUSPAY_WEBHOOK_SECRET) avant tout traitement.
"""
import hmac
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.user import User, PlanEnum, StatutAboEnum

payments_bp = Blueprint('payments', __name__, url_prefix='/api/paiements/genuispay')

# En-têtes des webhooks GeniusPay
SIGNATURE_HEADER = 'X-Webhook-Signature'
TIMESTAMP_HEADER = 'X-Webhook-Timestamp'
EVENT_HEADER = 'X-Webhook-Event'


def _verify_signature(raw_body: bytes, timestamp: str, received_signature: str) -> bool:
    """Vérifie la signature GeniusPay.
    Format : HMAC-SHA256(timestamp + "." + payload, secret)."""
    secret = current_app.config.get('GENIUSPAY_WEBHOOK_SECRET', '')
    if not secret or not received_signature or not timestamp:
        return False
    signed = f"{timestamp}.".encode('utf-8') + raw_body
    expected = hmac.new(secret.encode('utf-8'), signed, hashlib.sha256).hexdigest()
    received = received_signature.split('=', 1)[-1].strip()
    return hmac.compare_digest(expected, received)


def _map_plan(value: str):
    """Convertit le libellé de plan reçu en PlanEnum (insensible à la casse)."""
    if not value:
        return None
    try:
        return PlanEnum(value.strip().lower())
    except ValueError:
        return None


@payments_bp.post('/webhook')
def webhook():
    raw = request.get_data()  # corps brut, indispensable pour vérifier la signature
    signature = request.headers.get(SIGNATURE_HEADER, '')
    timestamp = request.headers.get(TIMESTAMP_HEADER, '')
    event_header = (request.headers.get(EVENT_HEADER, '') or '').lower()

    # 1) Sécurité : vérification de la signature GeniusPay
    if not _verify_signature(raw, timestamp, signature):
        current_app.logger.warning("Webhook GeniusPay : signature invalide.")
        return jsonify(ok=False, error='invalid signature'), 401

    # 2) Lecture du contenu (data peut être imbriqué)
    payload = request.get_json(silent=True) or {}
    d = payload.get('data') or payload
    event = event_header or (payload.get('event') or payload.get('type') or '').lower()
    status = (d.get('status') or payload.get('status') or '').lower()
    metadata = d.get('metadata') or payload.get('metadata') or {}

    # On ne traite que les paiements réussis
    success = (status in ('success', 'paid', 'completed', 'successful')) or \
              (event in ('payment.success', 'payment.completed', 'charge.success'))
    if not success:
        return jsonify(ok=True, ignored=True, reason='event non traité'), 200

    # 3) Identification de l'entreprise : via metadata.compte_id (fiable),
    #    sinon via l'email du client.
    from app.models.compte import Compte
    compte = None
    user = None
    if metadata.get('compte_id'):
        compte = Compte.query.get(metadata.get('compte_id'))
        user = compte.owner if compte else None
    if not compte:
        customer = d.get('customer') or {}
        email = (d.get('email') or customer.get('email') or '').lower().strip()
        user = User.query.filter_by(email=email).first() if email else None
        if not user:
            current_app.logger.warning("Webhook GeniusPay : entreprise/client introuvable.")
            return jsonify(ok=False, error='account not found'), 404

    # 4) Mise à jour de l'abonnement AU NIVEAU DE L'ENTREPRISE (compte)
    if not compte:
        from app.services.compte_service import get_or_create_compte
        compte = get_or_create_compte(user)

    nouveau_plan = _map_plan(metadata.get('plan') or d.get('plan') or d.get('plan_code'))
    if nouveau_plan:
        compte.plan = nouveau_plan
        if user:
            user.plan = nouveau_plan  # champ user synchronisé (compat.)
    compte.statut_abo = StatutAboEnum.ACTIF
    if user:
        user.statut_abo = StatutAboEnum.ACTIF
    compte.date_souscription = datetime.utcnow()

    # Cumul du revenu généré (sur l'entreprise)
    montant = d.get('amount') or d.get('montant') or 0
    try:
        compte.revenu_genere = (compte.revenu_genere or 0) + Decimal(str(montant))
    except (InvalidOperation, TypeError):
        pass

    # 5) Historique : valider (ou créer) la transaction correspondante
    from app.models.paiement import Paiement, StatutPaiement
    reference = d.get('reference') or metadata.get('ref_interne')
    paiement = Paiement.query.filter_by(reference=reference).first() if reference else None
    if paiement:
        paiement.statut = StatutPaiement.REUSSI
        paiement.date_paiement = datetime.utcnow()
    else:
        paiement = Paiement(
            compte_id=compte.id,
            reference=reference or f"EXT-{datetime.utcnow().timestamp():.0f}",
            plan=compte.plan.value,
            montant=Decimal(str(montant)) if str(montant).replace('.', '', 1).isdigit() else 0,
            statut=StatutPaiement.REUSSI,
            date_paiement=datetime.utcnow(),
        )
        db.session.add(paiement)

    db.session.commit()
    current_app.logger.info(
        f"Webhook GeniusPay : entreprise {compte.nom} -> plan={compte.plan.value}, +{montant}")

    return jsonify(ok=True, compte=compte.nom, plan=compte.plan.value), 200
