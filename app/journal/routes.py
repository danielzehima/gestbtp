import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.rapport import Rapport, RapportDocument
from app.models.chantier import Chantier
from app.models.photo import Photo
from app.journal.forms import RapportForm
from app.utils.helpers import save_upload, allowed_file
from app.auth.decorators import role_required, client_data_write
from app.utils.plans import abonnement_requis, current_compte_id
from app.models.user import RoleEnum

journal_bp = Blueprint('journal', __name__)


def _compte_chantier_ids():
    """IDs des chantiers de l'entreprise courante (None = admin → tous)."""
    if current_user.role == RoleEnum.ADMIN:
        return None
    cid = current_compte_id(current_user)
    return [c.id for c in Chantier.query.filter_by(compte_id=cid).all()]


def _get_rapport_or_404(id):
    r = Rapport.query.get_or_404(id)
    ids = _compte_chantier_ids()
    if ids is not None and r.chantier_id not in ids:
        abort(404)
    return r


@journal_bp.route('/')
@login_required
@abonnement_requis
def liste():
    date_filter = request.args.get('date')
    query = Rapport.query
    ids = _compte_chantier_ids()
    if ids is not None:
        query = query.filter(Rapport.chantier_id.in_(ids)) if ids else query.filter(db.false())
    if date_filter:
        query = query.filter_by(date=date_filter)
    rapports = query.order_by(Rapport.date.desc()).all()
    return render_template('journal/liste.html', rapports=rapports, date_filter=date_filter)


def _chantier_choices():
    """Chantiers de l'entreprise courante uniquement."""
    if current_user.role == RoleEnum.ADMIN:
        chantiers = Chantier.query.all()
    else:
        cid = current_compte_id(current_user)
        chantiers = Chantier.query.filter_by(compte_id=cid).all()
    return [(c.id, f"{c.reference} - {c.nom}") for c in chantiers]


@journal_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
@client_data_write
def nouveau():
    form = RapportForm()
    form.chantier_id.choices = _chantier_choices()
    if form.validate_on_submit():
        rapport = Rapport(
            chantier_id=form.chantier_id.data,
            auteur_id=current_user.id,
            date=form.date.data,
            meteo=form.meteo.data,
            travaux_realises=form.travaux_realises.data,
            difficultes=form.difficultes.data,
            main_oeuvre=form.main_oeuvre.data,
            observations=form.observations.data,
        )
        db.session.add(rapport)
        db.session.flush()

        # Photos -> Supabase Storage (avec repli local en dev)
        from app.services.storage_service import upload_photo, is_configured
        photo_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chantiers')
        for f in form.photos.data or []:
            if f and f.filename and allowed_file(f.filename, current_app.config['ALLOWED_PHOTO_EXTENSIONS']):
                try:
                    if is_configured():
                        chemin = upload_photo(f, folder='chantiers')
                    else:
                        fname, _ = save_upload(f, photo_folder)
                        chemin = f"uploads/chantiers/{fname}"
                    photo = Photo(
                        chantier_id=form.chantier_id.data,
                        chemin_fichier=chemin,
                        nom_fichier=f.filename,
                        uploader_id=current_user.id,
                    )
                    db.session.add(photo)
                    db.session.flush()
                    rapport.photos.append(photo)
                except Exception as exc:
                    current_app.logger.error(f"Upload photo rapport échoué: {exc}")

        # Documents
        doc_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
        for f in form.documents.data or []:
            if f and f.filename:
                fname, _ = save_upload(f, doc_folder)
                doc = RapportDocument(
                    rapport_id=rapport.id, nom_fichier=f.filename,
                    chemin=f"uploads/documents/{fname}",
                )
                db.session.add(doc)

        db.session.commit()
        flash("Rapport créé.", 'success')
        return redirect(url_for('journal.detail', id=rapport.id))
    return render_template('journal/form.html', form=form)


@journal_bp.route('/<int:id>')
@login_required
def detail(id):
    rapport = _get_rapport_or_404(id)
    return render_template('journal/detail.html', rapport=rapport)


@journal_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
@client_data_write
def modifier(id):
    rapport = _get_rapport_or_404(id)
    form = RapportForm(obj=rapport)
    form.chantier_id.choices = _chantier_choices()
    if request.method == 'GET':
        form.chantier_id.data = rapport.chantier_id
        form.meteo.data = rapport.meteo

    if form.validate_on_submit():
        rapport.chantier_id = form.chantier_id.data
        rapport.date = form.date.data
        rapport.meteo = form.meteo.data
        rapport.travaux_realises = form.travaux_realises.data
        rapport.difficultes = form.difficultes.data
        rapport.main_oeuvre = form.main_oeuvre.data
        rapport.observations = form.observations.data

        # Photos ajoutées (les anciennes restent attachées)
        from app.services.storage_service import upload_photo, is_configured
        photo_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chantiers')
        for f in form.photos.data or []:
            if f and f.filename and allowed_file(f.filename, current_app.config['ALLOWED_PHOTO_EXTENSIONS']):
                try:
                    if is_configured():
                        chemin = upload_photo(f, folder='chantiers')
                    else:
                        fname, _ = save_upload(f, photo_folder)
                        chemin = f"uploads/chantiers/{fname}"
                    photo = Photo(
                        chantier_id=rapport.chantier_id,
                        chemin_fichier=chemin,
                        nom_fichier=f.filename,
                        uploader_id=current_user.id,
                    )
                    db.session.add(photo)
                    db.session.flush()
                    rapport.photos.append(photo)
                except Exception as exc:
                    current_app.logger.error(f"Upload photo rapport échoué: {exc}")

        # Documents ajoutés
        doc_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
        for f in form.documents.data or []:
            if f and f.filename:
                fname, _ = save_upload(f, doc_folder)
                doc = RapportDocument(
                    rapport_id=rapport.id, nom_fichier=f.filename,
                    chemin=f"uploads/documents/{fname}",
                )
                db.session.add(doc)

        db.session.commit()
        flash("Rapport mis à jour.", 'success')
        return redirect(url_for('journal.detail', id=rapport.id))
    return render_template('journal/form.html', form=form, mode='Modifier', rapport=rapport)


@journal_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
@client_data_write
def supprimer(id):
    rapport = _get_rapport_or_404(id)
    db.session.delete(rapport)
    db.session.commit()
    flash("Rapport supprimé.", 'info')
    return redirect(url_for('journal.liste'))
