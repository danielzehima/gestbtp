"""Gestion de l'équipe d'une entreprise (compte/tenant).

Le propriétaire d'une entreprise peut ajouter / retirer des membres, dans la
limite d'utilisateurs autorisée par son forfait (max_utilisateurs).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User, RoleEnum
from app.services.compte_service import get_or_create_compte
from app.utils.plans import can_add_user, plan_limit, get_compte
from app.team.forms import MembreForm

team_bp = Blueprint('team', __name__, url_prefix='/equipe')


def _is_owner(user, compte):
    return compte and compte.owner_id == user.id


@team_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # L'admin opérateur n'a pas d'entreprise : on le renvoie vers les abonnés
    if current_user.role == RoleEnum.ADMIN:
        return redirect(url_for('dashboard.abonnes'))

    compte = get_or_create_compte(current_user)
    owner = _is_owner(current_user, compte)
    form = MembreForm()

    if form.validate_on_submit():
        if not owner:
            flash("Seul le propriétaire de l'entreprise peut ajouter des membres.", 'danger')
            return redirect(url_for('team.index'))
        if not can_add_user(current_user):
            limite = plan_limit(current_user, 'max_utilisateurs')
            flash(f"Limite d'utilisateurs atteinte pour votre forfait ({limite}). "
                  "Passez à un forfait supérieur pour ajouter plus de membres.", 'warning')
            return redirect(url_for('team.index'))
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Cet email est déjà utilisé.", 'danger')
            return redirect(url_for('team.index'))

        membre = User(
            nom=form.nom.data,
            email=form.email.data.lower(),
            telephone=form.telephone.data,
            role=RoleEnum(form.role.data),
            compte_id=compte.id,
        )
        membre.set_password(form.password.data)
        db.session.add(membre)
        db.session.commit()
        flash(f"{membre.nom} a été ajouté à votre équipe.", 'success')
        return redirect(url_for('team.index'))

    membres = compte.membres.order_by(User.date_creation.asc()).all()
    limite = plan_limit(current_user, 'max_utilisateurs')
    return render_template('team/index.html',
                           compte=compte, membres=membres, form=form,
                           owner=owner, limite=limite,
                           places_utilisees=len(membres),
                           peut_ajouter=can_add_user(current_user))


@team_bp.route('/<int:id>/retirer', methods=['POST'])
@login_required
def retirer(id):
    compte = get_compte(current_user)
    if not _is_owner(current_user, compte):
        abort(403)
    membre = User.query.get_or_404(id)
    # garde-fous : pas soi-même, pas un membre d'une autre entreprise, pas le propriétaire
    if membre.id == current_user.id or membre.compte_id != compte.id or membre.id == compte.owner_id:
        flash("Ce membre ne peut pas être retiré.", 'danger')
        return redirect(url_for('team.index'))
    membre.compte_id = None
    membre.actif = False
    db.session.commit()
    flash(f"{membre.nom} a été retiré de l'équipe.", 'info')
    return redirect(url_for('team.index'))
