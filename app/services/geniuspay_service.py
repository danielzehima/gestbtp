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

# Base GeniusPay (config GENIUSPAY_BASE_URL) = https://geniuspay.ci/api/v1/merchant
# Endpoint de création de paiement
_ENDPOINT = '/payments'


def _new_reference():
    return 'GBTP-' + uuid.uuid4().hex[:16].upper()


def initiate_payment(compte, plan_key, customer_email):
    """Crée une transaction GeniusPay pour faire passer l'entreprise à `plan_key`.

    Retourne (payment_url, paiement, error). `payment_url` None + error None =
    non configuré (paiement en attente). error renseigné = échec avec détail.
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
    api_secret = current_app.config.get('GENIUSPAY_SECRET_KEY', '')
    base = current_app.config.get('GENIUSPAY_BASE_URL', '').rstrip('/')
    if not api_key or not api_secret or not base:
        current_app.logger.info("GeniusPay non configuré : paiement en attente créé sans redirection.")
        return None, paiement, None

    # Payload GeniusPay : montant entier (FCFA), client, métadonnées.
    # En omettant payment_method, l'API renvoie une checkout_url.
    payload = {
        'amount': int(montant),
        'customer': {'email': customer_email},
        'description': f"Abonnement GESTBTP {plan_key} - {compte.nom}",
        'metadata': {
            'compte_id': compte.id,
            'plan': plan_key,
            'ref_interne': reference,
        },
    }
    req = urllib.request.Request(
        base + _ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers={
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:400]
        current_app.logger.error(f"GeniusPay init échec HTTP ({e.code}): {detail}")
        paiement.statut = StatutPaiement.ECHOUE
        db.session.commit()
        return None, paiement, f"GeniusPay a répondu {e.code} : {detail}"
    except Exception as e:
        current_app.logger.error(f"GeniusPay init erreur: {e!r}")
        paiement.statut = StatutPaiement.ECHOUE
        db.session.commit()
        return None, paiement, f"Connexion à GeniusPay impossible : {e}"

    data = body.get('data', body) or {}
    payment_url = data.get('checkout_url') or body.get('checkout_url')
    # La référence GeniusPay (MTX-...) devient la référence officielle du paiement
    mtx = data.get('reference') or body.get('reference')
    if mtx:
        paiement.provider_ref = str(mtx)
        paiement.reference = str(mtx)
        db.session.commit()

    if not payment_url:
        return None, paiement, f"Réponse GeniusPay sans checkout_url : {str(body)[:300]}"

    return payment_url, paiement, None
