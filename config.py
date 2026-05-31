import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    _db_url = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'gestbtp.db')
    )
    # Supabase / Heroku donnent parfois "postgres://" — SQLAlchemy 2.x veut "postgresql://"
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Pool optimisé pour Supabase pooler / serverless Vercel
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.environ.get('UPLOAD_FOLDER', 'app/static/uploads'))
    # Vercel limite le corps des requêtes serverless à ~4,5 Mo.
    # On reste sous cette limite (les images sont compressées côté navigateur).
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 4 * 1024 * 1024))
    ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@gestbtp.com')

    WTF_CSRF_ENABLED = True

    COMPANY_NAME = "GESTBTP"
    COMPANY_COLOR_PRIMARY = "#FF6B00"
    COMPANY_COLOR_DARK = "#111111"

    # Réseaux sociaux (modifier les URLs ici)
    SOCIAL_LINKS = {
        'facebook':  'https://facebook.com/gestbtp',
        'linkedin':  'https://linkedin.com/company/gestbtp',
        'whatsapp':  'https://wa.me/2250700000000',
        'twitter':   'https://twitter.com/gestbtp',
        'youtube':   'https://youtube.com/@gestbtp',
    }
    DEMO_VIDEO_URL = 'https://www.youtube.com/embed/dQw4w9WgXcQ'  # remplacer par la vraie démo
    CONTACT_EMAIL  = 'contact@gestbtp.com'
    CONTACT_PHONE  = '+225 07 00 00 00 00'
    CONTACT_ADDR   = 'Abidjan, Côte d\'Ivoire'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
