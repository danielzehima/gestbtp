import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.photo import Photo
from app.models.chantier import Chantier
from app.utils.helpers import save_upload, allowed_file
from app.services.storage_service import upload_photo, delete_photo, is_configured
from app.auth.decorators import role_required

photos_bp = Blueprint('photos', __name__)


@photos_bp.route('/')
@login_required
def index():
    """Page Photos globale : liste des chantiers avec leur nombre de photos
    et un aperçu, pour accéder à la galerie de chacun."""
    from app.models.user import RoleEnum
    query = Chantier.query
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
    chantier = Chantier.query.get_or_404(chantier_id)
    photos = Photo.query.filter_by(chantier_id=chantier_id).order_by(Photo.date_upload.desc()).all()
    return render_template('photos/galerie.html', chantier=chantier, photos=photos)


@photos_bp.route('/chantier/<int:chantier_id>/upload', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
def upload(chantier_id):
    chantier = Chantier.query.get_or_404(chantier_id)
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
def supprimer(id):
    photo = Photo.query.get_or_404(id)
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
