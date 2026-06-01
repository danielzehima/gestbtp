from functools import wraps
from flask import abort, flash, redirect, request
from flask_login import current_user


def client_data_write(f):
    """Empêche l'ADMIN SaaS de modifier/supprimer les données opérationnelles
    des entreprises clientes (chantiers, rapports, tâches, photos).
    L'admin garde un accès en LECTURE seule pour le support.

    À placer après @login_required (et @role_required le cas échéant)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role.value == 'admin':
            flash("En tant qu'administrateur, vous avez un accès en lecture seule "
                  "aux données des entreprises clientes (pas de modification).", 'warning')
            return redirect(request.referrer or '/dashboard')
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role.value not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    return role_required('admin')(f)
