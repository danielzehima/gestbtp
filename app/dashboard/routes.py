from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models.chantier import Chantier, StatutChantier
from app.models.rapport import Rapport
from app.models.tache import Tache, StatutTache
from app.models.user import User, RoleEnum, PlanEnum, StatutAboEnum
from app.auth.decorators import role_required
from app.extensions import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')


@dashboard_bp.route('/dashboard')
@login_required
def index():
    total = Chantier.query.count()
    actifs = Chantier.query.filter_by(statut=StatutChantier.EN_COURS).count()
    termines = Chantier.query.filter_by(statut=StatutChantier.TERMINE).count()
    nb_rapports = Rapport.query.count()
    nb_retard = Tache.query.filter(
        Tache.date_limite < date.today(),
        Tache.statut != StatutTache.TERMINE
    ).count()

    derniers_rapports = Rapport.query.order_by(Rapport.date_creation.desc()).limit(5).all()
    taches_urgentes = Tache.query.filter(
        Tache.statut != StatutTache.TERMINE
    ).order_by(Tache.date_limite.asc().nullslast()).limit(5).all()

    stats = {
        'total': total, 'actifs': actifs, 'termines': termines,
        'rapports': nb_rapports, 'retard': nb_retard,
    }
    return render_template('dashboard/index.html',
                           stats=stats,
                           derniers_rapports=derniers_rapports,
                           taches_urgentes=taches_urgentes)


@dashboard_bp.route('/abonnes')
@login_required
@role_required('admin')
def abonnes():
    q = request.args.get('q', '')
    plan_filter = request.args.get('plan', '')
    statut_filter = request.args.get('statut', '')

    # L'admin voit TOUS les abonnés clients (y compris les Gratuits)
    query = User.query.filter_by(role=RoleEnum.CLIENT)

    if q:
        like_str = f"%{q}%"
        query = query.filter((User.nom.ilike(like_str)) | (User.email.ilike(like_str)))
    if plan_filter:
        query = query.filter_by(plan=PlanEnum(plan_filter))
    if statut_filter:
        query = query.filter_by(statut_abo=StatutAboEnum(statut_filter))

    clients = query.order_by(User.date_souscription.desc().nullslast()).all()

    total_revenu = db.session.query(func.sum(User.revenu_genere)) \
        .filter_by(role=RoleEnum.CLIENT).scalar() or 0

    def count_plan(p):
        return User.query.filter_by(role=RoleEnum.CLIENT, plan=p).count()

    stats = {
        'total_clients': User.query.filter_by(role=RoleEnum.CLIENT).count(),
        'gratuit': count_plan(PlanEnum.GRATUIT),
        'starter': count_plan(PlanEnum.STARTER),
        'pro': count_plan(PlanEnum.PRO),
        'entreprise': count_plan(PlanEnum.ENTREPRISE),
        'revenu': float(total_revenu),
    }

    return render_template('dashboard/abonnes.html',
                           clients=clients,
                           stats=stats,
                           q=q,
                           plan_filter=plan_filter,
                           statut_filter=statut_filter)


@dashboard_bp.route('/abonnes/<int:id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_status(id):
    client = User.query.get_or_404(id)
    if client.statut_abo == StatutAboEnum.ACTIF:
        client.statut_abo = StatutAboEnum.SUSPENDU
        flash(f"L'abonnement de {client.nom} a été suspendu.", 'warning')
    else:
        client.statut_abo = StatutAboEnum.ACTIF
        flash(f"L'abonnement de {client.nom} a été réactivé.", 'success')
    db.session.commit()
    return redirect(url_for('dashboard.abonnes'))
