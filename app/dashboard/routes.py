from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models.chantier import Chantier, StatutChantier
from app.models.rapport import Rapport
from app.models.tache import Tache, StatutTache, PrioriteTache
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


def _scoped_bases():
    """Retourne (chantier_query, rapport_query, tache_query) limités à
    l'entreprise courante (admin = tout)."""
    cid = current_compte_id(current_user)
    if current_user.role == RoleEnum.ADMIN:
        return Chantier.query, Rapport.query, Tache.query
    ch_ids = [c.id for c in Chantier.query.filter_by(compte_id=cid).all()]
    ch_q = Chantier.query.filter_by(compte_id=cid)
    rap_q = Rapport.query.filter(Rapport.chantier_id.in_(ch_ids)) if ch_ids else Rapport.query.filter(db.false())
    tache_q = Tache.query.filter(Tache.chantier_id.in_(ch_ids)) if ch_ids else Tache.query.filter(db.false())
    return ch_q, rap_q, tache_q


@dashboard_bp.route('/api/dashboard/stats')
@login_required
def stats_json():
    """Données agrégées pour les graphiques du dashboard (scopées entreprise)."""
    ch_q, rap_q, tache_q = _scoped_bases()

    # 1) Chantiers par statut (donut)
    chantiers_statut = {s.value: ch_q.filter_by(statut=s).count() for s in StatutChantier}

    # 2) Tâches par statut (barres)
    taches_statut = {s.value: tache_q.filter_by(statut=s).count() for s in StatutTache}

    # 3) Tâches par priorité
    taches_priorite = {p.value: tache_q.filter_by(priorite=p).count() for p in PrioriteTache}

    # 4) Taux d'avancement global (% tâches terminées)
    total_taches = tache_q.count()
    terminees = tache_q.filter_by(statut=StatutTache.TERMINE).count()
    avancement = round(terminees / total_taches * 100) if total_taches else 0

    # 5) Activité 30 derniers jours (rapports + tâches créés par jour)
    today = date.today()
    jours = [(today - timedelta(days=i)) for i in range(29, -1, -1)]
    labels = [j.strftime('%d/%m') for j in jours]
    rapports_jour, taches_jour = [], []
    for j in jours:
        debut = j
        fin = j + timedelta(days=1)
        rapports_jour.append(rap_q.filter(Rapport.date_creation >= debut,
                                          Rapport.date_creation < fin).count())
        taches_jour.append(tache_q.filter(Tache.date_creation >= debut,
                                          Tache.date_creation < fin).count())

    return jsonify({
        'chantiers_statut': chantiers_statut,
        'taches_statut': taches_statut,
        'taches_priorite': taches_priorite,
        'avancement': avancement,
        'activite': {'labels': labels, 'rapports': rapports_jour, 'taches': taches_jour},
    })


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
