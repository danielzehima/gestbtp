"""Espace abonnement de l'entreprise : forfait actuel, historique de
paiement, et passage à un forfait supérieur via GenuisPay.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import RoleEnum
from app.models.paiement import Paiement, StatutPaiement
from app.services.compte_service import get_or_create_compte
from app.services.geniuspay_service import initiate_payment
from app.utils.plans import PLAN_LIMITS, get_compte, acces_actif

# Pas de url_prefix : on expose à la fois /abonnement (gestion) et /paiement (blocage)
billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/abonnement')
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


@billing_bp.route('/abonnement/payer/<plan>', methods=['POST'])
@login_required
def payer(plan):
    compte = get_compte(current_user)
    if not compte or compte.owner_id != current_user.id:
        abort(403)
    if plan not in ('starter', 'pro', 'entreprise'):
        flash("Forfait invalide.", 'danger')
        return redirect(url_for('billing.index'))

    payment_url, paiement, error = initiate_payment(compte, plan, current_user.email)
    if payment_url:
        return redirect(payment_url)  # redirection vers la page de paiement GeniusPay

    if error:
        flash(f"Le paiement n'a pas pu être initié. {error}", 'danger')
    else:
        flash("Le paiement en ligne n'est pas encore activé (clés GeniusPay manquantes). "
              f"Votre demande de passage au forfait {plan.capitalize()} a été enregistrée.", 'info')
    return redirect(url_for('billing.index'))


@billing_bp.route('/abonnement/retour')
@login_required
def retour():
    """Page de retour après paiement (la confirmation réelle vient du webhook)."""
    reference = request.args.get('reference')
    paiement = Paiement.query.filter_by(reference=reference).first() if reference else None
    return render_template('billing/retour.html', paiement=paiement)


@billing_bp.route('/paiement')
@login_required
def paiement():
    """Page affichée quand l'essai est terminé / un abonnement est requis.
    Présente les forfaits payants + (le cas échéant) l'option d'essai gratuit."""
    if current_user.role == RoleEnum.ADMIN:
        return redirect(url_for('dashboard.index'))

    compte = get_or_create_compte(current_user)
    # Si l'accès est déjà actif (abonné ou essai en cours), pas besoin de bloquer
    if acces_actif(compte):
        return redirect(url_for('dashboard.index'))

    offres = []
    for key in ('starter', 'pro'):
        infos = PLAN_LIMITS[key]
        offres.append({'key': key, 'label': infos['label'], 'prix': infos['prix'],
                       'max_chantiers': infos['max_chantiers'],
                       'max_utilisateurs': infos['max_utilisateurs'],
                       'export_pdf': infos['export_pdf']})

    # L'essai n'est proposable que si l'entreprise n'en a jamais eu
    essai_disponible = (compte.date_fin_essai is None)
    essai_termine = (compte.date_fin_essai is not None and not compte.en_essai)

    return render_template('billing/paiement.html',
                           compte=compte, offres=offres,
                           owner=(compte.owner_id == current_user.id),
                           essai_disponible=essai_disponible,
                           essai_termine=essai_termine)


@billing_bp.route('/paiement/essai', methods=['POST'])
@login_required
def demarrer_essai():
    """Le visiteur en souscription directe change d'avis et veut d'abord
    l'essai gratuit de 14 jours (uniquement s'il n'en a jamais eu)."""
    from datetime import datetime, timedelta
    compte = get_or_create_compte(current_user)
    if compte.owner_id != current_user.id:
        abort(403)
    if compte.date_fin_essai is not None:
        flash("Votre entreprise a déjà bénéficié de l'essai gratuit.", 'warning')
        return redirect(url_for('billing.paiement'))
    from app.models.user import PlanEnum
    compte.plan = PlanEnum.STARTER
    compte.date_fin_essai = datetime.utcnow() + timedelta(days=14)
    compte.est_abonne = False
    db.session.commit()
    flash("🎉 Essai gratuit de 14 jours activé !", 'success')
    return redirect(url_for('dashboard.index'))


@billing_bp.route('/facture/<int:paiement_id>')
@login_required
def facture(paiement_id):
    """Télécharge la facture PDF d'un paiement d'abonnement (réussi)."""
    p = Paiement.query.get_or_404(paiement_id)
    compte = get_or_create_compte(current_user)
    # L'abonné ne peut télécharger que SES factures (admin = tout)
    if current_user.role != RoleEnum.ADMIN and p.compte_id != compte.id:
        abort(404)
    if p.statut != StatutPaiement.REUSSI:
        flash("La facture n'est disponible que pour un paiement réussi.", 'warning')
        return redirect(url_for('billing.index'))
    from app.billing.invoice_pdf import abonnement_invoice_pdf
    buf = abonnement_invoice_pdf(p, p.compte or compte)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"facture-abonnement-{p.reference}.pdf")
