import re
from flask import Blueprint, redirect, url_for, render_template, request, flash, jsonify
from app.services.email_service import send_email
from flask import current_app

pages_bp = Blueprint('pages', __name__)

EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')


@pages_bp.route('/login')
def login_alias():
    return redirect(url_for('auth.login'))


@pages_bp.route('/register')
def register_alias():
    plan = request.args.get('plan')
    return redirect(url_for('auth.register', plan=plan) if plan else url_for('auth.register'))


@pages_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Accepte AJAX (JSON) ou formulaire classique
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form

        nom = (data.get('nom') or '').strip()
        email = (data.get('email') or '').strip()
        tel = (data.get('telephone') or '').strip()
        message = (data.get('message') or '').strip()

        errors = []
        if len(nom) < 2:
            errors.append("Le nom est requis (2 caractères min).")
        if not EMAIL_RE.match(email):
            errors.append("Adresse email invalide.")
        if len(message) < 10:
            errors.append("Le message doit faire au moins 10 caractères.")

        if errors:
            if request.is_json:
                return jsonify(ok=False, errors=errors), 400
            for e in errors:
                flash(e, 'danger')
            return render_template('pages/contact.html', form_data=data)

        try:
            send_email(
                to=current_app.config['CONTACT_EMAIL'],
                subject=f"[GESTBTP Contact] {nom}",
                body=f"De: {nom} <{email}>\nTéléphone: {tel}\n\n{message}"
            )
        except Exception:
            pass  # ne pas bloquer si mail non configuré

        if request.is_json:
            return jsonify(ok=True, message="Votre message a bien été envoyé. Nous vous répondrons rapidement.")
        flash("Votre message a bien été envoyé. Nous vous répondrons rapidement.", 'success')
        return redirect(url_for('pages.contact'))

    return render_template('pages/contact.html', form_data={})


@pages_bp.route('/privacy')
def privacy():
    return render_template('pages/legal.html',
        titre="Politique de confidentialité",
        contenu=_PRIVACY)


@pages_bp.route('/terms')
def terms():
    return render_template('pages/legal.html',
        titre="Conditions d'utilisation",
        contenu=_TERMS)


@pages_bp.route('/support')
def support():
    return render_template('pages/support.html')


_PRIVACY = """
<h2>1. Collecte des données</h2>
<p>GESTBTP collecte uniquement les données nécessaires au fonctionnement du service : nom, email, téléphone, données de chantier saisies par les utilisateurs.</p>
<h2>2. Utilisation des données</h2>
<p>Vos données servent exclusivement à la gestion de votre compte et à l'exécution du service. Elles ne sont jamais revendues à des tiers.</p>
<h2>3. Conservation</h2>
<p>Les données sont conservées tant que votre compte est actif. Vous pouvez demander leur suppression à tout moment.</p>
<h2>4. Sécurité</h2>
<p>Mots de passe hashés, communications chiffrées HTTPS, sauvegardes régulières.</p>
<h2>5. Vos droits</h2>
<p>Vous disposez d'un droit d'accès, de rectification, de portabilité et de suppression. Contactez-nous à contact@gestbtp.com.</p>
"""

_TERMS = """
<h2>1. Objet</h2>
<p>Les présentes conditions régissent l'utilisation de la plateforme SaaS GESTBTP.</p>
<h2>2. Compte utilisateur</h2>
<p>L'utilisateur s'engage à fournir des informations exactes et à protéger ses identifiants.</p>
<h2>3. Abonnement</h2>
<p>Tout abonnement est mensuel sans engagement. La résiliation prend effet à la fin du mois en cours.</p>
<h2>4. Disponibilité</h2>
<p>GESTBTP s'engage à un taux de disponibilité de 99,5%. La maintenance planifiée sera annoncée 48h à l'avance.</p>
<h2>5. Responsabilité</h2>
<p>GESTBTP n'est pas responsable des données saisies par les utilisateurs ni de l'usage qui en est fait.</p>
<h2>6. Loi applicable</h2>
<p>Les présentes conditions sont soumises au droit ivoirien.</p>
"""
