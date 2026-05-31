"""Initiation des paiements via GenuisPay.

NOTE : l'API exacte de GenuisPay (URL d'endpoint et format de payload) doit
être adaptée selon leur documentation. La structure ci-dessous est générique
et isole l'intégration : il suffira d'ajuster `_ENDPOINT` et le payload.
"""
import json
import uuid
import urllib.request
import urllib.error
from flask import current_app, url_for
from app.extensions import db
from app.models.paiement import Paiement, StatutPaiement
from app.utils.plans import PLAN_LIMITS

# Endpoint d'initialisation de paiement chez GenuisPay (à adapter)
_ENDPOINT = '/v1/payments/initialize'


def _new_reference():
    return 'GBTP-' + uuid.uuid4().hex[:16].upper()


def initiate_payment(compte, plan_key, customer_email):
    """Crée une transaction GenuisPay pour faire passer l'entreprise à `plan_key`.

    Retourne (payment_url, paiement). `payment_url` peut être None si GenuisPay
    n'est pas encore configuré : on enregistre alors juste un paiement en attente.
    """
    infos = PLAN_LIMITS.get(plan_key, {})
    montant = infos.get('prix') or 0
    reference = _new_reference()

    paiement = Paiement(
        compte_id=compte.id, reference=reference, plan=plan_key,
        montant=montant, statut=StatutPaiement.EN_ATTENTE,
    )
    db.session.add(paiement)
    db.session.commit()

    api_key = current_app.config.get('GENIUSPAY_API_KEY', '')
    base = current_app.config.get('GENIUSPAY_BASE_URL', '').rstrip('/')
    if not api_key or not base:
        # Non configuré : on ne peut pas rediriger, on retourne juste le paiement en attente
        current_app.logger.info("GenuisPay non configuré : paiement en attente créé sans redirection.")
        return None, paiement

    payload = {
        'amount': float(montant),
        'currency': 'XOF',
        'reference': reference,
        'customer_email': customer_email,
        'description': f"Abonnement GESTBTP {plan_key} - {compte.nom}",
        'callback_url': url_for('payments.webhook', _external=True),
        'return_url': url_for('billing.retour', reference=reference, _external=True),
        'metadata': {'compte_id': compte.id, 'plan': plan_key},
    }
    req = urllib.request.Request(
        base + _ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        current_app.logger.error(f"GenuisPay init échec ({e.code}): {e.read()[:200]}")
        paiement.statut = StatutPaiement.ECHOUE
        db.session.commit()
        return None, paiement

    # On cherche l'URL de paiement dans les champs habituels
    payment_url = (
        body.get('payment_url') or body.get('checkout_url') or body.get('url')
        or (body.get('data') or {}).get('payment_url')
        or (body.get('data') or {}).get('authorization_url')
    )
    provider_ref = body.get('id') or body.get('transaction_id') or (body.get('data') or {}).get('id')
    if provider_ref:
        paiement.provider_ref = str(provider_ref)
        db.session.commit()

    return payment_url, paiement
