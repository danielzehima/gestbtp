import os
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, jwt, login_manager, mail, csrf, cors


def create_app(config_name='development'):
    # Robustesse : on normalise la valeur (FLASK_ENV peut arriver en
    # majuscules depuis Vercel, ex 'PRODUCTION') et on retombe sur
    # 'production' si la clé est inconnue, pour ne jamais planter au boot.
    key = (config_name or 'development').strip().lower()
    if key not in config_by_name:
        key = 'production'
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_by_name[key])

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Création dossiers upload.
    # Sur un hébergement serverless (Vercel), le système de fichiers du projet
    # est en LECTURE SEULE -> on bascule les uploads vers /tmp (seul dossier
    # inscriptible) et on protège la création contre une erreur fatale au boot.
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    for sub in ('chantiers', 'documents'):
        path = os.path.join(app.config['UPLOAD_FOLDER'], sub)
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            # Filesystem en lecture seule : on ignore, l'app doit quand même démarrer
            pass

    # Import des modèles (pour Alembic / create_all)
    from app.models import user, chantier, rapport, tache, photo, notification  # noqa

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # Blueprints HTML
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.chantiers.routes import chantiers_bp
    from app.journal.routes import journal_bp
    from app.taches.routes import taches_bp
    from app.photos.routes import photos_bp
    from app.pdf.routes import pdf_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(chantiers_bp, url_prefix='/chantiers')
    app.register_blueprint(journal_bp, url_prefix='/journal')
    app.register_blueprint(taches_bp, url_prefix='/taches')
    app.register_blueprint(photos_bp, url_prefix='/photos')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')

    # Blueprints API REST (CSRF désactivé pour API JWT)
    from app.api.auth_api import auth_api
    from app.api.chantiers_api import chantiers_api
    from app.api.rapports_api import rapports_api
    from app.api.taches_api import taches_api

    for bp in (auth_api, chantiers_api, rapports_api, taches_api):
        csrf.exempt(bp)
        app.register_blueprint(bp)

    # Context processor global
    @app.context_processor
    def inject_globals():
        return {
            'COMPANY_NAME': app.config['COMPANY_NAME'],
            'COLOR_PRIMARY': app.config['COMPANY_COLOR_PRIMARY'],
            'SOCIAL': app.config['SOCIAL_LINKS'],
            'DEMO_VIDEO_URL': app.config['DEMO_VIDEO_URL'],
            'CONTACT_EMAIL': app.config['CONTACT_EMAIL'],
            'CONTACT_PHONE': app.config['CONTACT_PHONE'],
            'CONTACT_ADDR': app.config['CONTACT_ADDR'],
        }

    # Alias courts /login /register et pages publiques
    from app.pages.routes import pages_bp
    csrf.exempt(pages_bp)
    app.register_blueprint(pages_bp)

    # Handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    return app
