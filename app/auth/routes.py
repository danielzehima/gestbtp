import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User, RoleEnum
from app.auth.forms import LoginForm, RegisterForm, ForgotForm, ResetForm
from app.services.email_service import send_email

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data) and user.actif:
            login_user(user)
            flash(f"Bienvenue {user.nom} !", 'success')
            return redirect(request.args.get('next') or url_for('dashboard.index'))
        flash("Identifiants invalides.", 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    from datetime import datetime, timedelta
    from app.models.user import PlanEnum
    # plan choisi : 'essai' (défaut), 'starter' ou 'pro'
    plan = (request.values.get('plan') or 'essai').strip().lower()
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            return render_template('auth/register.html', form=form, plan=plan,
                                   erreur="Cet email est déjà utilisé. Connectez-vous ou utilisez une autre adresse.")
        user = User(
            nom=form.nom.data, email=form.email.data.lower(),
            telephone=form.telephone.data, role=RoleEnum(form.role.data),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Création de l'entreprise (compte/tenant) dont l'utilisateur est propriétaire
        from app.services.compte_service import get_or_create_compte
        compte = get_or_create_compte(user)

        if plan in ('starter', 'pro'):
            # SOUSCRIPTION DIRECTE : on vise le plan, pas d'essai -> page de paiement
            compte.plan = PlanEnum(plan)
            compte.est_abonne = False
            db.session.commit()
            login_user(user)
            return redirect(url_for('billing.paiement', plan=plan))

        # ESSAI GRATUIT 14 JOURS (avantages Starter)
        compte.plan = PlanEnum.STARTER
        compte.est_abonne = False
        compte.date_fin_essai = datetime.utcnow() + timedelta(days=14)
        db.session.commit()
        login_user(user)
        flash("🎉 Votre essai gratuit de 14 jours a démarré ! Profitez de toutes "
              "les fonctionnalités du forfait Starter.", 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html', form=form, plan=plan)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Vous êtes déconnecté.", 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            user.reset_token = secrets.token_urlsafe(32)
            user.reset_expires = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()
            link = url_for('auth.reset', token=user.reset_token, _external=True)
            send_email(user.email, "GESTBTP - Réinitialisation",
                       f"Cliquez pour réinitialiser : {link}\n(Valide 2 heures)")
        flash("Si l'email existe, un lien a été envoyé.", 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot.html', form=form)


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_expires or user.reset_expires < datetime.utcnow():
        flash("Lien invalide ou expiré.", 'danger')
        return redirect(url_for('auth.login'))
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_expires = None
        db.session.commit()
        flash("Mot de passe modifié.", 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset.html', form=form)
