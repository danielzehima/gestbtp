from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models.chantier import Chantier, StatutChantier
from app.models.rapport import Rapport
from app.models.tache import Tache, StatutTache
from app.models.user import User, RoleEnum, PlanEnum, StatutAboEnum
from app.models.compte import Compte
from app.auth.decorators import role_required
from app.utils.plans import abonnement_requis, current_compte_id
from app.extensions import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')


@dashboard_bp.route('/dashboard')
@login_required
@abonnement_requis
def index():
    from app.models.user import RoleEnum
    cid = current_compte_id(current_user)

    # Bases de requêtes limitées à l'entreprise (admin = tout voir)
    if current_user.role == RoleEnum.ADMIN:
        ch_q = Chantier.query
        rap_q = Rapport.query
        tache_q = Tache.query
    else:
        ch_ids = [c.id for c in Chantier.query.filter_by(compte_id=cid).all()]
        ch_q = Chantier.query.filter_by(compte_id=cid)
        rap_q = Rapport.query.filter(Rapport.chantier_id.in_(ch_ids)) if ch_ids else Rapport.query.filter(db.false())
        tache_q = Tache.query.filter(Tache.chantier_id.in_(ch_ids)) if ch_ids else Tache.query.filter(db.false())

    total = ch_q.count()
    actifs = ch_q.filter_by(statut=StatutChantier.EN_COURS).count()
    termines = ch_q.filter_by(statut=StatutChantier.TERMINE).count()
    nb_rapports = rap_q.count()
    nb_retard = tache_q.filter(
        Tache.date_limite < date.today(),
        Tache.statut != StatutTache.TERMINE
    ).count()

    derniers_rapports = rap_q.order_by(Rapport.date_creation.desc()).limit(5).all()
    taches_urgentes = tache_q.filter(
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
    """Liste des ENTREPRISES abonnées (comptes/tenants)."""
    q = request.args.get('q', '')
    plan_filter = request.args.get('plan', '')
    statut_filter = request.args.get('statut', '')

    query = Compte.query
    if q:
        query = query.filter(Compte.nom.ilike(f"%{q}%"))
    if plan_filter:
        query = query.filter_by(plan=PlanEnum(plan_filter))
    if statut_filter:
        query = query.filter_by(statut_abo=StatutAboEnum(statut_filter))

    comptes = query.order_by(Compte.date_souscription.desc().nullslast()).all()

    total_revenu = db.session.query(func.sum(Compte.revenu_genere)).scalar() or 0

    def count_plan(p):
        return Compte.query.filter_by(plan=p).count()

    stats = {
        'total_comptes': Compte.query.count(),
        'gratuit': count_plan(PlanEnum.GRATUIT),
        'starter': count_plan(PlanEnum.STARTER),
        'pro': count_plan(PlanEnum.PRO),
        'entreprise': count_plan(PlanEnum.ENTREPRISE),
        'revenu': float(total_revenu),
    }

    return render_template('dashboard/abonnes.html',
                           comptes=comptes,
                           stats=stats,
                           q=q,
                           plan_filter=plan_filter,
                           statut_filter=statut_filter)


@dashboard_bp.route('/abonnes/<int:id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_status(id):
    compte = Compte.query.get_or_404(id)
    if compte.statut_abo == StatutAboEnum.ACTIF:
        compte.statut_abo = StatutAboEnum.SUSPENDU
        flash(f"L'abonnement de {compte.nom} a été suspendu.", 'warning')
    else:
        compte.statut_abo = StatutAboEnum.ACTIF
        flash(f"L'abonnement de {compte.nom} a été réactivé.", 'success')
    db.session.commit()
    return redirect(url_for('dashboard.abonnes'))
