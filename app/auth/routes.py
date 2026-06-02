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
    from flask import current_app
    form = ForgotForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            user.reset_token = secrets.token_urlsafe(32)
            user.reset_expires = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()
            link = url_for('auth.reset', token=user.reset_token, _external=True)

            texte = (f"Bonjour {user.nom},\n\n"
                     f"Vous avez demandé à réinitialiser votre mot de passe GESTBTP.\n"
                     f"Cliquez sur ce lien (valide 2 heures) :\n{link}\n\n"
                     f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.")
            html = f"""
            <div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:auto">
              <div style="background:#FF6B00;padding:18px;border-radius:12px 12px 0 0;text-align:center">
                <h1 style="color:#fff;margin:0;font-size:22px">GESTBTP</h1>
              </div>
              <div style="border:1px solid #eee;border-top:none;padding:24px;border-radius:0 0 12px 12px">
                <p>Bonjour <strong>{user.nom}</strong>,</p>
                <p>Vous avez demandé à réinitialiser votre mot de passe.</p>
                <p style="text-align:center;margin:24px 0">
                  <a href="{link}" style="background:#FF6B00;color:#fff;text-decoration:none;
                     padding:12px 28px;border-radius:10px;font-weight:600;display:inline-block">
                     Réinitialiser mon mot de passe</a>
                </p>
                <p style="color:#888;font-size:13px">Ce lien est valable 2 heures. Si vous n'êtes pas
                à l'origine de cette demande, ignorez simplement cet email.</p>
                <p style="color:#aaa;font-size:12px;word-break:break-all">{link}</p>
              </div>
            </div>"""

            ok = send_email(user.email, "GESTBTP — Réinitialisation de mot de passe", texte, html)

            # En développement (sans Resend configuré), on affiche le lien à l'écran
            if not ok and current_app.debug:
                flash(f"[DEV] Email non envoyé. Lien de réinitialisation : {link}", 'warning')
                return render_template('auth/forgot.html', form=form)

        flash("Si cette adresse existe, un email de réinitialisation vient d'être envoyé.", 'info')
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
