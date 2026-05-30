# GESTBTP

SaaS de gestion de chantiers BTP — Flask + PostgreSQL + JWT + ReportLab.

## Stack
Python 3.10+, Flask 3, SQLAlchemy, PostgreSQL, Bootstrap 5, ReportLab.

## Installation

### 1. Cloner / placer le projet
Le projet est dans : `C:\Users\HP\Desktop\APPLI_SAAS_GESTION_BTP`

### 2. Créer un environnement virtuel
```powershell
cd C:\Users\HP\Desktop\APPLI_SAAS_GESTION_BTP
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances
```powershell
pip install -r requirements.txt
```

### 4. Configurer l'environnement
Copier `.env.example` en `.env` et adapter :
```powershell
copy .env.example .env
```
Modifier `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, paramètres mail...

### 5. Initialiser la base
**Option A — SQLite (rapide pour tester)** : ne rien changer dans `.env`, la base sera créée automatiquement.

**Option B — PostgreSQL** : créer la base puis :
```powershell
flask db init
flask db migrate -m "init"
flask db upgrade
```

Créer les tables + admin par défaut :
```powershell
flask init-db
```
**Identifiants admin par défaut** : `admin@gestbtp.com` / `Admin1234!`

### 6. Lancer le serveur
```powershell
python run.py
```
Ouvrir http://localhost:5000

## Structure

```
GESTBTP/
├── app/
│   ├── __init__.py        # Factory Flask
│   ├── extensions.py
│   ├── auth/              # Authentification (login/register/reset)
│   ├── dashboard/         # Tableau de bord + stats
│   ├── chantiers/         # CRUD chantiers
│   ├── journal/           # Rapports journaliers
│   ├── taches/            # Gestion tâches (vue Kanban)
│   ├── photos/            # Upload galerie
│   ├── pdf/               # Génération PDF (ReportLab)
│   ├── api/               # API REST JWT (/api/...)
│   ├── models/            # SQLAlchemy
│   ├── services/          # Email, notifications
│   ├── utils/             # Helpers (uploads, validation)
│   ├── static/            # CSS, JS, uploads/
│   └── templates/         # Jinja2
├── config.py
├── run.py
├── requirements.txt
└── .env.example
```

## Rôles
- **admin** : tout
- **conducteur** : créer/modifier chantiers/rapports/tâches/photos
- **client** : consultation de ses chantiers

## API REST
Toutes les routes sous `/api/*` utilisent JWT (`Authorization: Bearer <token>`).
- `POST /api/auth/login` → token
- `GET /api/chantiers/`, `POST`, `PUT`, `DELETE`
- `GET /api/rapports/`, `POST`, `DELETE`
- `GET /api/taches/`, `POST`, `PUT`, `PATCH /:id/statut`, `DELETE`

## PDF
- `/pdf/rapport/<id>` — rapport journalier
- `/pdf/chantier/<id>` — fiche chantier
- `/pdf/chantier/<id>/taches` — liste tâches

## Sécurité
- CSRF activé (Flask-WTF)
- Mots de passe hashés (Werkzeug)
- JWT côté API
- Décorateurs `@login_required`, `@role_required`

## Déploiement
- Gunicorn : `gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"`
- Définir `FLASK_ENV=production` et les variables d'environnement sécurisées
