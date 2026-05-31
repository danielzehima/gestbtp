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
from datetime import datetime
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


def get_compte(user):
    """Entreprise (Compte) à laquelle l'utilisateur est rattaché, ou None."""
    return getattr(user, 'compte', None) if user else None


def get_plan_key(user):
    """Clé du forfait (ex: 'pro'). Source de vérité = le Compte de
    l'entreprise ; repli sur le champ user.plan puis sur 'gratuit'."""
    compte = get_compte(user)
    try:
        if compte and compte.plan:
            return compte.plan.value
        if user and user.plan:
            return user.plan.value
    except Exception:
        pass
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
    """Nombre de chantiers de l'ENTREPRISE (compte) de l'utilisateur.
    Repli : chantiers dont l'utilisateur est responsable (s'il n'a pas de compte)."""
    from app.models.chantier import Chantier
    compte = get_compte(user)
    if compte:
        return Chantier.query.filter_by(compte_id=compte.id).count()
    return Chantier.query.filter_by(responsable_id=user.id).count()


def _count_membres(user):
    """Nombre d'utilisateurs rattachés à l'entreprise (compte)."""
    compte = get_compte(user)
    if compte:
        return compte.membres.count()
    return 1


def can_create_chantier(user):
    """False si l'ENTREPRISE a atteint sa limite de chantiers.
    Les admins (opérateur SaaS) ne sont jamais limités."""
    from app.models.user import RoleEnum
    if user.role == RoleEnum.ADMIN:
        return True
    limite = plan_limit(user, 'max_chantiers')
    if limite is None:
        return True
    return _count_chantiers(user) < limite


def can_add_user(user):
    """False si l'ENTREPRISE a atteint sa limite d'utilisateurs."""
    from app.models.user import RoleEnum
    if user.role == RoleEnum.ADMIN:
        return True
    limite = plan_limit(user, 'max_utilisateurs')
    if limite is None:
        return True
    return _count_membres(user) < limite


def chantiers_restants(user):
    """Nombre de chantiers encore créables pour l'entreprise (None = illimité)."""
    limite = plan_limit(user, 'max_chantiers')
    if limite is None:
        return None
    return max(0, limite - _count_chantiers(user))


# ---------- Accès : essai valide OU abonnement payant ----------
def acces_actif(compte):
    """True si l'entreprise a un accès actif (abonnée ou essai en cours)."""
    if not compte:
        return False
    if compte.est_abonne:
        return True
    if compte.date_fin_essai and datetime.utcnow() < compte.date_fin_essai:
        return True
    return False


def abonnement_requis(f):
    """Bloque l'accès si l'entreprise n'est ni en essai valide ni abonnée.
    À placer APRÈS @login_required.

    Exemple :
        @dashboard_bp.route('/dashboard')
        @login_required
        @abonnement_requis
        def index(): ...
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        from app.models.user import RoleEnum
        # L'admin (opérateur SaaS) n'est jamais bloqué
        if current_user.role == RoleEnum.ADMIN:
            return f(*args, **kwargs)
        compte = get_compte(current_user)
        if acces_actif(compte):
            return f(*args, **kwargs)
        flash("Votre période d'essai est terminée ou un abonnement est requis "
              "pour accéder à cette fonctionnalité.", 'warning')
        return redirect(url_for('billing.paiement'))
    return wrapper


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
