"""Espace abonnement de l'entreprise : forfait actuel, historique de
paiement, et passage à un forfait supérieur via GenuisPay.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models.user import RoleEnum
from app.models.paiement import Paiement
from app.services.compte_service import get_or_create_compte
from app.services.geniuspay_service import initiate_payment
from app.utils.plans import PLAN_LIMITS, get_compte

billing_bp = Blueprint('billing', __name__, url_prefix='/abonnement')


@billing_bp.route('/')
@login_required
def index():
    if current_user.role == RoleEnum.ADMIN:
        return redirect(url_for('dashboard.abonnes'))

    compte = get_or_create_compte(current_user)
    owner = compte.owner_id == current_user.id
    plan_actuel = compte.plan.value
    paiements = compte.paiements.order_by(Paiement.date_creation.desc()).all()

    # Forfaits proposables (supérieurs au gratuit)
    offres = []
    for key in ('starter', 'pro', 'entreprise'):
        infos = PLAN_LIMITS[key]
        offres.append({
            'key': key, 'label': infos['label'], 'prix': infos['prix'],
            'max_chantiers': infos['max_chantiers'],
            'max_utilisateurs': infos['max_utilisateurs'],
            'export_pdf': infos['export_pdf'],
            'actuel': (key == plan_actuel),
        })

    return render_template('billing/index.html',
                           compte=compte, owner=owner,
                           plan_actuel=plan_actuel,
                           limites=PLAN_LIMITS[plan_actuel],
                           offres=offres, paiements=paiements)


@billing_bp.route('/payer/<plan>', methods=['POST'])
@login_required
def payer(plan):
    compte = get_compte(current_user)
    if not compte or compte.owner_id != current_user.id:
        abort(403)
    if plan not in ('starter', 'pro', 'entreprise'):
        flash("Forfait invalide.", 'danger')
        return redirect(url_for('billing.index'))

    payment_url, paiement = initiate_payment(compte, plan, current_user.email)
    if payment_url:
        return redirect(payment_url)  # redirection vers la page de paiement GenuisPay

    # GenuisPay pas encore configuré : on informe l'utilisateur
    flash("Le paiement en ligne n'est pas encore activé (clés GenuisPay manquantes). "
          f"Votre demande de passage au forfait {plan.capitalize()} a été enregistrée.", 'info')
    return redirect(url_for('billing.index'))


@billing_bp.route('/retour')
@login_required
def retour():
    """Page de retour après paiement (la confirmation réelle vient du webhook)."""
    reference = request.args.get('reference')
    paiement = Paiement.query.filter_by(reference=reference).first() if reference else None
    return render_template('billing/retour.html', paiement=paiement)
