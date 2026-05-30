from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from flask_login import current_user as _cu
from app.models.chantier import Chantier, StatutChantier
from app.models.rapport import Rapport
from app.models.tache import Tache, StatutTache

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
