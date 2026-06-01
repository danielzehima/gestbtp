"""Planning / calendrier des chantiers et échéances de tâches.

Affiche, sur un calendrier interactif :
- les chantiers sur leur période (date_debut -> date_fin_prev)
- les échéances de tâches (date_limite)
Tout est scopé par entreprise (isolation multi-tenant).
"""
from datetime import timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.chantier import Chantier, StatutChantier
from app.models.tache import Tache, StatutTache
from app.models.user import RoleEnum
from app.utils.plans import abonnement_requis, current_compte_id

planning_bp = Blueprint('planning', __name__, url_prefix='/planning')

# Couleurs par statut de chantier (cohérentes avec les badges)
COULEUR_CHANTIER = {
    'preparation': '#F59E0B',
    'en_cours': '#16A34A',
    'suspendu': '#9A3412',
    'termine': '#3B82F6',
}
# Couleurs par priorité de tâche
COULEUR_TACHE = {
    'faible': '#9CA3AF',
    'moyenne': '#F59E0B',
    'haute': '#EA580C',
    'critique': '#DC2626',
}


def _scoped_chantiers():
    if current_user.role == RoleEnum.ADMIN:
        return Chantier.query.all()
    cid = current_compte_id(current_user)
    return Chantier.query.filter_by(compte_id=cid).all() if cid else []


@planning_bp.route('/')
@login_required
@abonnement_requis
def index():
    return render_template('planning/index.html')


@planning_bp.route('/events')
@login_required
def events():
    """Renvoie les événements au format FullCalendar (JSON)."""
    chantiers = _scoped_chantiers()
    ch_ids = [c.id for c in chantiers]
    events = []

    # 1) Chantiers (barres sur leur période)
    for c in chantiers:
        if not c.date_debut:
            continue
        # FullCalendar : la date de fin est exclusive -> +1 jour pour inclure le dernier
        fin = (c.date_fin_prev + timedelta(days=1)) if c.date_fin_prev else (c.date_debut + timedelta(days=1))
        events.append({
            'id': f"ch-{c.id}",
            'title': f"🏗️ {c.nom}",
            'start': c.date_debut.isoformat(),
            'end': fin.isoformat(),
            'color': COULEUR_CHANTIER.get(c.statut.value, '#FF6B00'),
            'url': f"/chantiers/{c.id}",
            'extendedProps': {'type': 'chantier', 'statut': c.statut.value},
        })

    # 2) Échéances de tâches (points sur la date limite)
    if ch_ids:
        taches = Tache.query.filter(Tache.chantier_id.in_(ch_ids),
                                    Tache.date_limite.isnot(None)).all()
    else:
        taches = []
    for t in taches:
        termine = (t.statut == StatutTache.TERMINE)
        events.append({
            'id': f"t-{t.id}",
            'title': ("✓ " if termine else "📌 ") + t.titre,
            'start': t.date_limite.isoformat(),
            'allDay': True,
            'color': '#16A34A' if termine else COULEUR_TACHE.get(t.priorite.value, '#FF6B00'),
            'extendedProps': {'type': 'tache', 'statut': t.statut.value,
                              'priorite': t.priorite.value, 'chantier': t.chantier.nom},
        })

    return jsonify(events)
