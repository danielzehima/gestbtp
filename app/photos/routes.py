import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.photo import Photo
from app.models.chantier import Chantier
from app.utils.helpers import save_upload, allowed_file
from app.auth.decorators import role_required

photos_bp = Blueprint('photos', __name__)


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
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chantiers')
    count = 0
    for f in request.files.getlist('photos'):
        if f and f.filename and allowed_file(f.filename, current_app.config['ALLOWED_PHOTO_EXTENSIONS']):
            fname, _ = save_upload(f, folder)
            photo = Photo(
                chantier_id=chantier_id,
                chemin_fichier=f"uploads/chantiers/{fname}",
                nom_fichier=f.filename,
                legende=request.form.get('legende'),
                uploader_id=current_user.id,
            )
            db.session.add(photo)
            count += 1
    db.session.commit()
    flash(f"{count} photo(s) ajoutée(s).", 'success')
    return redirect(url_for('photos.galerie', chantier_id=chantier_id))


@photos_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
def supprimer(id):
    photo = Photo.query.get_or_404(id)
    chantier_id = photo.chantier_id
    try:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'].replace('app/static/uploads', 'app/static'),
                            photo.chemin_fichier.replace('uploads/', 'uploads/'))
        full = os.path.join('app', 'static', photo.chemin_fichier)
        if os.path.exists(full):
            os.remove(full)
    except Exception:
        pass
    db.session.delete(photo)
    db.session.commit()
    flash("Photo supprimée.", 'info')
    return redirect(url_for('photos.galerie', chantier_id=chantier_id))
