import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.photo import Photo
from app.models.chantier import Chantier
from app.utils.helpers import save_upload, allowed_file
from app.services.storage_service import upload_photo, delete_photo, is_configured
from app.auth.decorators import role_required, client_data_write
from app.utils.plans import abonnement_requis, current_compte_id
from app.models.user import RoleEnum

photos_bp = Blueprint('photos', __name__)


def _get_chantier_or_404(chantier_id):
    """Chantier garanti appartenir à l'entreprise courante (admin = tout)."""
    ch = Chantier.query.get_or_404(chantier_id)
    if current_user.role != RoleEnum.ADMIN:
        if ch.compte_id != current_compte_id(current_user):
            abort(404)
    return ch


@photos_bp.route('/')
@login_required
@abonnement_requis
def index():
    """Page Photos globale : chantiers de l'entreprise avec aperçu photos."""
    if current_user.role == RoleEnum.ADMIN:
        query = Chantier.query
    else:
        cid = current_compte_id(current_user)
        query = Chantier.query.filter_by(compte_id=cid)
        if current_user.role == RoleEnum.CLIENT:
            query = query.filter_by(client_id=current_user.id)
    chantiers = query.order_by(Chantier.date_creation.desc()).all()
    data = []
    for c in chantiers:
        photos = Photo.query.filter_by(chantier_id=c.id).order_by(Photo.date_upload.desc()).all()
        data.append({'chantier': c, 'count': len(photos), 'apercu': photos[:4]})
    return render_template('photos/index.html', data=data)


@photos_bp.route('/chantier/<int:chantier_id>')
@login_required
def galerie(chantier_id):
    chantier = _get_chantier_or_404(chantier_id)
    photos = Photo.query.filter_by(chantier_id=chantier_id).order_by(Photo.date_upload.desc()).all()
    return render_template('photos/galerie.html', chantier=chantier, photos=photos)


@photos_bp.route('/chantier/<int:chantier_id>/upload', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
@client_data_write
def upload(chantier_id):
    chantier = _get_chantier_or_404(chantier_id)
    count = 0
    errors = 0
    for f in request.files.getlist('photos'):
        if f and f.filename and allowed_file(f.filename, current_app.config['ALLOWED_PHOTO_EXTENSIONS']):
            try:
                nom = f.filename
                if is_configured():
                    # Stockage permanent dans Supabase Storage
                    chemin = upload_photo(f, folder='chantiers')
                else:
                    # Repli local (développement sans Supabase)
                    fname, _ = save_upload(f, os.path.join(current_app.config['UPLOAD_FOLDER'], 'chantiers'))
                    chemin = f"uploads/chantiers/{fname}"
                photo = Photo(
                    chantier_id=chantier_id,
                    chemin_fichier=chemin,
                    nom_fichier=nom,
                    legende=request.form.get('legende'),
                    uploader_id=current_user.id,
                )
                db.session.add(photo)
                count += 1
            except Exception as exc:
                current_app.logger.error(f"Upload photo échoué: {exc}")
                errors += 1
    db.session.commit()
    if count:
        flash(f"{count} photo(s) ajoutée(s).", 'success')
    if errors:
        flash(f"{errors} photo(s) n'ont pas pu être envoyées.", 'danger')
    return redirect(url_for('photos.galerie', chantier_id=chantier_id))


@photos_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
@client_data_write
def supprimer(id):
    photo = Photo.query.get_or_404(id)
    _get_chantier_or_404(photo.chantier_id)  # garantit l'appartenance à l'entreprise
    chantier_id = photo.chantier_id
    cf = photo.chemin_fichier or ''
    try:
        if cf.startswith('http'):
            delete_photo(cf)  # Supabase Storage
        else:
            full = os.path.join('app', 'static', cf)  # ancien fichier local
            if os.path.exists(full):
                os.remove(full)
    except Exception:
        pass
    db.session.delete(photo)
    db.session.commit()
    flash("Photo supprimée.", 'info')
    return redirect(url_for('photos.galerie', chantier_id=chantier_id))
