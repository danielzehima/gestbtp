from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.tache import Tache, PrioriteTache, StatutTache
from app.models.chantier import Chantier
from app.models.user import User
from app.taches.forms import TacheForm
from app.auth.decorators import role_required
from app.utils.plans import abonnement_requis, current_compte_id
from app.models.user import RoleEnum
from app.services.notification_service import notify_user

taches_bp = Blueprint('taches', __name__)


def _compte_chantier_ids():
    """IDs des chantiers de l'entreprise courante (None = admin → tous)."""
    if current_user.role == RoleEnum.ADMIN:
        return None
    cid = current_compte_id(current_user)
    return [c.id for c in Chantier.query.filter_by(compte_id=cid).all()]


def _populate(form):
    """Chantiers et responsables limités à l'entreprise courante."""
    if current_user.role == RoleEnum.ADMIN:
        chantiers = Chantier.query.all()
        users = User.query.all()
    else:
        cid = current_compte_id(current_user)
        chantiers = Chantier.query.filter_by(compte_id=cid).all()
        users = User.query.filter_by(compte_id=cid).all()
    form.chantier_id.choices = [(c.id, f"{c.reference} - {c.nom}") for c in chantiers]
    form.responsable_id.choices = [(0, '— Aucun —')] + [(u.id, u.nom) for u in users]


def _get_tache_or_404(id):
    t = Tache.query.get_or_404(id)
    ids = _compte_chantier_ids()
    if ids is not None and t.chantier_id not in ids:
        abort(404)
    return t


@taches_bp.route('/')
@login_required
@abonnement_requis
def liste():
    statut = request.args.get('statut')
    query = Tache.query
    ids = _compte_chantier_ids()
    if ids is not None:
        query = query.filter(Tache.chantier_id.in_(ids)) if ids else query.filter(db.false())
    if statut:
        query = query.filter_by(statut=StatutTache(statut))
    taches = query.order_by(Tache.date_limite.asc().nullslast()).all()
    # Pour vue Kanban
    kanban = {s: [t for t in taches if t.statut == s] for s in StatutTache}
    return render_template('taches/liste.html', taches=taches, kanban=kanban, statut=statut)


@taches_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
def nouveau():
    form = TacheForm()
    _populate(form)
    if form.validate_on_submit():
        t = Tache(
            chantier_id=form.chantier_id.data,
            titre=form.titre.data,
            description=form.description.data,
            responsable_id=form.responsable_id.data or None,
            priorite=PrioriteTache(form.priorite.data),
            statut=StatutTache(form.statut.data),
            date_limite=form.date_limite.data,
        )
        db.session.add(t)
        db.session.commit()
        if t.responsable_id:
            notify_user(t.responsable_id, f"Nouvelle tâche : {t.titre}", t.id)
        flash("Tâche créée.", 'success')
        return redirect(url_for('taches.liste'))
    return render_template('taches/form.html', form=form, mode='Créer')


@taches_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'conducteur')
def modifier(id):
    t = _get_tache_or_404(id)
    form = TacheForm(obj=t)
    _populate(form)
    if request.method == 'GET':
        form.priorite.data = t.priorite.value
        form.statut.data = t.statut.value
        form.responsable_id.data = t.responsable_id or 0
    if form.validate_on_submit():
        t.chantier_id = form.chantier_id.data
        t.titre = form.titre.data
        t.description = form.description.data
        t.responsable_id = form.responsable_id.data or None
        t.priorite = PrioriteTache(form.priorite.data)
        t.statut = StatutTache(form.statut.data)
        t.date_limite = form.date_limite.data
        db.session.commit()
        flash("Tâche mise à jour.", 'success')
        return redirect(url_for('taches.liste'))
    return render_template('taches/form.html', form=form, mode='Modifier', tache=t)


@taches_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
def supprimer(id):
    t = _get_tache_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("Tâche supprimée.", 'info')
    return redirect(url_for('taches.liste'))


@taches_bp.route('/<int:id>/statut', methods=['POST'])
@login_required
@role_required('admin', 'conducteur')
def changer_statut(id):
    """Change le statut d'une tâche (utilisé par le Kanban drag & drop).
    Réponse JSON. Vérifie l'appartenance à l'entreprise via _get_tache_or_404."""
    from flask import jsonify
    t = _get_tache_or_404(id)
    data = request.get_json(silent=True) or {}
    nouveau = data.get('statut', '')
    try:
        t.statut = StatutTache(nouveau)
    except ValueError:
        return jsonify(ok=False, error='statut invalide'), 400
    db.session.commit()
    return jsonify(ok=True, id=t.id, statut=t.statut.value)
