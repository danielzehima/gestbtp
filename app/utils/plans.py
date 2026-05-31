"""Définition des forfaits SaaS et application de leurs limites.

C'est ICI qu'on règle ce que chaque forfait autorise. Pour changer une
limite, il suffit de modifier le dictionnaire PLAN_LIMITS.

Utilisation typique :
    from app.utils.plans import can_create_chantier, require_feature

    # Dans une route, avant de créer un chantier :
    if not can_create_chantier(current_user):
        flash("Limite de chantiers atteinte pour votre forfait.", 'warning')
        return redirect(...)

    # Pour bloquer une fonctionnalité premium :
    @require_feature('export_pdf')
    def export(...): ...
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


# None = illimité
PLAN_LIMITS = {
    'gratuit': {
        'label': 'Gratuit',
        'prix': 0,
        'max_chantiers': 1,
        'max_utilisateurs': 1,
        'export_pdf': False,
        'support_prioritaire': False,
    },
    'starter': {
        'label': 'Starter',
        'prix': 5000,
        'max_chantiers': 3,
        'max_utilisateurs': 5,
        'export_pdf': True,
        'support_prioritaire': False,
    },
    'pro': {
        'label': 'Pro',
        'prix': 15000,
        'max_chantiers': None,
        'max_utilisateurs': 25,
        'export_pdf': True,
        'support_prioritaire': True,
    },
    'entreprise': {
        'label': 'Entreprise',
        'prix': None,
        'max_chantiers': None,
        'max_utilisateurs': None,
        'export_pdf': True,
        'support_prioritaire': True,
    },
}

DEFAULT_PLAN = 'gratuit'


def get_plan_key(user):
    """Retourne la clé du forfait de l'utilisateur (ex: 'pro')."""
    try:
        return user.plan.value if user and user.plan else DEFAULT_PLAN
    except Exception:
        return DEFAULT_PLAN


def plan_config(user):
    return PLAN_LIMITS.get(get_plan_key(user), PLAN_LIMITS[DEFAULT_PLAN])


def plan_limit(user, key):
    """Valeur d'une limite (None = illimité)."""
    return plan_config(user).get(key)


def feature_enabled(user, feature):
    """True si la fonctionnalité est incluse dans le forfait."""
    return bool(plan_config(user).get(feature))


def _count_chantiers(user):
    """Nombre de chantiers rattachés à l'utilisateur (comme responsable)."""
    from app.models.chantier import Chantier
    return Chantier.query.filter_by(responsable_id=user.id).count()


def can_create_chantier(user):
    """False si l'utilisateur a atteint la limite de chantiers de son forfait.
    Les admins ne sont jamais limités."""
    from app.models.user import RoleEnum
    if user.role == RoleEnum.ADMIN:
        return True
    limite = plan_limit(user, 'max_chantiers')
    if limite is None:
        return True
    return _count_chantiers(user) < limite


def chantiers_restants(user):
    """Nombre de chantiers encore créables (None = illimité)."""
    limite = plan_limit(user, 'max_chantiers')
    if limite is None:
        return None
    return max(0, limite - _count_chantiers(user))


# ---------- Décorateur pour bloquer une fonctionnalité premium ----------
def require_feature(feature, redirect_endpoint='dashboard.index'):
    """Bloque l'accès à une route si le forfait n'inclut pas `feature`.

    Exemple :
        @pdf_bp.route('/rapport/<int:id>')
        @login_required
        @require_feature('export_pdf')
        def rapport(id): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            from app.models.user import RoleEnum
            if current_user.role != RoleEnum.ADMIN and not feature_enabled(current_user, feature):
                flash("Cette fonctionnalité nécessite un forfait supérieur. "
                      "Passez à un forfait payant pour en profiter.", 'warning')
                return redirect(url_for(redirect_endpoint))
            return f(*args, **kwargs)
        return wrapper
    return decorator
