"""Paramètres / personnalisation de l'entreprise (identité affichée sur les
devis et factures : logo, coordonnées)."""
from flask import (Blueprint, render_template, redirect, url_for, flash, request,
                   jsonify, current_app)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import RoleEnum
from app.services.compte_service import get_or_create_compte
from app.services.storage_service import is_configured, create_signed_upload_url
from app.auth.decorators import client_data_write

entreprise_bp = Blueprint('entreprise', __name__, url_prefix='/entreprise')


@entreprise_bp.route('/', methods=['GET', 'POST'])
@login_required
def parametres():
    if current_user.role == RoleEnum.ADMIN:
        return redirect(url_for('dashboard.abonnes'))

    compte = get_or_create_compte(current_user)
    owner = compte.owner_id == current_user.id

    if request.method == 'POST':
        if not owner:
            flash("Seul le propriétaire peut modifier les paramètres de l'entreprise.", 'danger')
            return redirect(url_for('entreprise.parametres'))
        compte.raison_sociale = request.form.get('raison_sociale', '').strip() or compte.nom
        compte.adresse = request.form.get('adresse', '').strip()
        compte.telephone = request.form.get('telephone', '').strip()
        compte.email = request.form.get('email', '').strip()
        compte.site_web = request.form.get('site_web', '').strip()
        # Infos légales / fiscales
        compte.rccm = request.form.get('rccm', '').strip()
        compte.nif = request.form.get('nif', '').strip()
        compte.forme_juridique = request.form.get('forme_juridique', '').strip()
        compte.capital = request.form.get('capital', '').strip()
        compte.banque = request.form.get('banque', '').strip()
        compte.iban = request.form.get('iban', '').strip()
        # Couleur d'accent (hex #RRGGBB)
        coul = request.form.get('couleur', '').strip()
        if coul.startswith('#') and len(coul) == 7:
            compte.couleur = coul
        # le logo arrive via l'upload direct (champ caché logo_url)
        logo = request.form.get('logo_url', '').strip()
        if logo:
            compte.logo_url = logo
        db.session.commit()
        flash("Paramètres de l'entreprise enregistrés.", 'success')
        return redirect(url_for('entreprise.parametres'))

    return render_template('entreprise/parametres.html', compte=compte, owner=owner)


@entreprise_bp.route('/logo/sign-upload', methods=['POST'])
@login_required
@client_data_write
def sign_logo_upload():
    """URL d'upload signée pour envoyer le logo directement à Supabase."""
    if not is_configured():
        return jsonify(ok=False, error="Stockage non configuré"), 400
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', 'logo.png')
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ('png', 'jpg', 'jpeg', 'webp'):
        return jsonify(ok=False, error="Format non supporté (png, jpg, webp)"), 400
    try:
        upload_url, public_url = create_signed_upload_url(folder='logos', filename=filename)
        return jsonify(ok=True, upload_url=upload_url, public_url=public_url)
    except Exception as e:
        current_app.logger.error(f"sign logo upload échec: {e}")
        return jsonify(ok=False, error=str(e)), 500
