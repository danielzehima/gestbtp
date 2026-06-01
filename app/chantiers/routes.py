from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.chantier import Chantier, StatutChantier
from app.models.user import User, RoleEnum
from app.chantiers.forms import ChantierForm
from app.auth.decorators import role_required
from app.utils.plans import (can_create_chantier, chantiers_restants, get_compte,
                             abonnement_requis, current_compte_id)

chantiers_bp = Blueprint('chantiers', __name__)


def _populate_form_choices(form):
    """Listes déroulantes limitées aux MEMBRES de l'entreprise courante."""
    cid = current_compte_id(current_user)
    base = User.query.filter_by(compte_id=cid) if cid else User.query
    form.client_id.choices = [(0, '— Aucun —')] + [
        (u.id, u.nom) for u in base.filter_by(role=RoleEnum.CLIENT).all()
    ]
    form.responsable_id.choices = [(0, '— Aucun —')] + [
        (u.id, u.nom) for u in base.filter(
            User.role.in_([RoleEnum.CONDUCTEUR, RoleEnum.ADMIN])).all()
    ]


def _scoped_chantiers():
    """Requête de base limitée aux chantiers de l'entreprise courante.
    L'admin (opérateur SaaS) voit tout."""
    if current_user.role == RoleEnum.ADMIN:
        return Chantier.query
    cid = current_compte_id(current_user)
    return Chantier.query.filter_by(compte_id=cid) if cid else Chantier.query.filter(db.false())


def _get_chantier_or_404(id):
    """Récupère un chantier en garantissant qu'il appartient à l'entreprise."""
    ch = Chantier.query.get_or_404(id)
    if current_user.role != RoleEnum.ADMIN:
        if ch.compte_id != current_compte_id(current_user):
            abort(404)
    return ch


@chantiers_bp.route('/')
@login_required
@abonnement_requis
def liste():
    statut = request.args.get('statut')
    q = request.args.get('q', '')
    query = _scoped_chantiers()
    if statut:
        query = query.filter_by(statut=StatutChantier(statut))
    if q:
        like = f"%{q}%"
        query = query.filter((Chantier.nom.ilike(like)) | (Chantier.reference.ilike(like)))
    if current_user.role == RoleEnum.CLIENT:
        query = query.filter_by(client_id=current_user.id)
    chantiers = query.order_by(Chantier.date_creation.desc()).all()
    return render_template('chantiers/liste.html', chantiers=chantiers, q=q, statut=statut)


@chantiers_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
def nouveau():
    if not can_create_chantier(current_user):
        flash("Vous avez atteint la limite de chantiers de votre forfait. "
              "Passez à un forfait supérieur pour en créer davantage.", 'warning')
        return redirect(url_for('chantiers.liste'))
    form = ChantierForm()
    _populate_form_choices(form)
    if form.validate_on_submit():
        from app.services.compte_service import get_or_create_compte
        compte = get_or_create_compte(current_user) if not current_user.is_admin else get_compte(current_user)
        cid = compte.id if compte else None
        # Unicité de la référence DANS l'entreprise (pas globalement)
        existe = Chantier.query.filter_by(reference=form.reference.data, compte_id=cid).first()
        if existe:
            flash("Cette référence existe déjà dans votre entreprise.", 'danger')
        else:
            ch = Chantier(
                compte_id=cid,
                nom=form.nom.data, reference=form.reference.data,
                adresse=form.adresse.data,
                client_id=form.client_id.data or None,
                responsable_id=form.responsable_id.data or None,
                budget=form.budget.data or 0,
                statut=StatutChantier(form.statut.data),
                date_debut=form.date_debut.data,
                date_fin_prev=form.date_fin_prev.data,
                description=form.description.data,
            )
            db.session.add(ch)
            db.session.commit()
            flash("Chantier créé.", 'success')
            return redirect(url_for('chantiers.detail', id=ch.id))
    return render_template('chantiers/form.html', form=form, mode='Créer')


@chantiers_bp.route('/<int:id>')
@login_required
def detail(id):
    ch = _get_chantier_or_404(id)
    if current_user.role == RoleEnum.CLIENT and ch.client_id != current_user.id:
        abort(403)
    return render_template('chantiers/detail.html', chantier=ch)


@chantiers_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
def modifier(id):
    ch = _get_chantier_or_404(id)
    form = ChantierForm(obj=ch)
    _populate_form_choices(form)
    if request.method == 'GET':
        form.statut.data = ch.statut.value
        form.client_id.data = ch.client_id or 0
        form.responsable_id.data = ch.responsable_id or 0
    if form.validate_on_submit():
        ch.nom = form.nom.data
        ch.reference = form.reference.data
        ch.adresse = form.adresse.data
        ch.client_id = form.client_id.data or None
        ch.responsable_id = form.responsable_id.data or None
        ch.budget = form.budget.data or 0
        ch.statut = StatutChantier(form.statut.data)
        ch.date_debut = form.date_debut.data
        ch.date_fin_prev = form.date_fin_prev.data
        ch.description = form.description.data
        db.session.commit()
        flash("Chantier mis à jour.", 'success')
        return redirect(url_for('chantiers.detail', id=ch.id))
    return render_template('chantiers/form.html', form=form, mode='Modifier', chantier=ch)


@chantiers_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
def supprimer(id):
    ch = _get_chantier_or_404(id)
    db.session.delete(ch)
    db.session.commit()
    flash("Chantier supprimé.", 'info')
    return redirect(url_for('chantiers.liste'))
