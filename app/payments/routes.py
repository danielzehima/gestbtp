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

# En-tête HTTP où GenuisPay place la signature (adapter au nom réel fourni
# dans votre tableau de bord GenuisPay si différent).
SIGNATURE_HEADER = 'X-Geniuspay-Signature'


def _verify_signature(raw_body: bytes, received_signature: str) -> bool:
    """Recalcule la signature HMAC-SHA256 du corps brut et la compare,
    en temps constant, à celle envoyée par GenuisPay."""
    secret = current_app.config.get('GENIUSPAY_WEBHOOK_SECRET', '')
    if not secret or not received_signature:
        return False
    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    # Tolère un éventuel préfixe "sha256="
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

    # 1) Sécurité : vérification de la signature
    if not _verify_signature(raw, signature):
        current_app.logger.warning("Webhook GenuisPay : signature invalide.")
        return jsonify(ok=False, error='invalid signature'), 401

    # 2) Lecture du contenu
    data = request.get_json(silent=True) or {}
    event = (data.get('event') or data.get('type') or '').lower()
    status = (data.get('status') or '').lower()

    # On ne traite que les paiements réussis
    success = (status in ('success', 'paid', 'completed', 'successful')) or \
              (event in ('payment.success', 'payment.completed', 'charge.success'))
    if not success:
        # On accuse réception pour éviter que GenuisPay ne réessaie indéfiniment
        return jsonify(ok=True, ignored=True, reason='event non traité'), 200

    # 3) Identification du client (par email ou référence)
    customer = data.get('customer') or {}
    email = (data.get('email') or customer.get('email') or '').lower().strip()
    user = User.query.filter_by(email=email).first() if email else None
    if not user:
        current_app.logger.warning(f"Webhook GenuisPay : client introuvable ({email}).")
        return jsonify(ok=False, error='customer not found'), 404

    # 4) Mise à jour de l'abonnement AU NIVEAU DE L'ENTREPRISE (compte)
    from app.services.compte_service import get_or_create_compte
    compte = get_or_create_compte(user)

    nouveau_plan = _map_plan(data.get('plan') or data.get('plan_code'))
    if nouveau_plan:
        compte.plan = nouveau_plan
        user.plan = nouveau_plan  # on garde le champ user synchronisé (compat.)
    compte.statut_abo = StatutAboEnum.ACTIF
    user.statut_abo = StatutAboEnum.ACTIF
    compte.date_souscription = datetime.utcnow()

    # Cumul du revenu généré (sur l'entreprise)
    montant = data.get('amount') or data.get('montant') or 0
    try:
        compte.revenu_genere = (compte.revenu_genere or 0) + Decimal(str(montant))
    except (InvalidOperation, TypeError):
        pass

    # 5) Historique : valider (ou créer) la transaction correspondante
    from app.models.paiement import Paiement, StatutPaiement
    reference = data.get('reference') or data.get('ref')
    paiement = Paiement.query.filter_by(reference=reference).first() if reference else None
    if paiement:
        paiement.statut = StatutPaiement.REUSSI
        paiement.date_paiement = datetime.utcnow()
        paiement.provider_ref = data.get('id') or paiement.provider_ref
    else:
        # paiement non initié depuis l'app (ou référence absente) : on trace quand même
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
        f"Webhook GenuisPay : {user.email} (entreprise {compte.nom}) "
        f"-> plan={compte.plan.value}, +{montant}")

    return jsonify(ok=True, user=user.email, compte=compte.nom, plan=compte.plan.value), 200
