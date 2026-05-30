-- =============================================================
-- GESTBTP — Schéma PostgreSQL pour Supabase
-- À exécuter dans Supabase → SQL Editor → New query → Run
-- =============================================================

-- Nettoyage si tu réexécutes (commenté par sécurité)
-- DROP TABLE IF EXISTS notifications, rapport_documents, rapport_photos,
--   photos, taches, rapports, chantiers, users CASCADE;
-- DROP TYPE IF EXISTS roleenum, statutchantier, prioritetache, statuttache;

-- ============ ENUMS ============
DO $$ BEGIN
  CREATE TYPE roleenum AS ENUM ('admin','conducteur','client');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE statutchantier AS ENUM ('preparation','en_cours','suspendu','termine');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE prioritetache AS ENUM ('faible','moyenne','haute','critique');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE statuttache AS ENUM ('a_faire','en_cours','termine','bloque');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ============ USERS ============
CREATE TABLE IF NOT EXISTS users (
  id              SERIAL PRIMARY KEY,
  nom             VARCHAR(120) NOT NULL,
  email           VARCHAR(120) UNIQUE NOT NULL,
  mot_de_passe    VARCHAR(255) NOT NULL,
  role            roleenum NOT NULL DEFAULT 'client',
  telephone       VARCHAR(30),
  actif           BOOLEAN DEFAULT TRUE,
  date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  reset_token     VARCHAR(255),
  reset_expires   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============ CHANTIERS ============
CREATE TABLE IF NOT EXISTS chantiers (
  id              SERIAL PRIMARY KEY,
  nom             VARCHAR(200) NOT NULL,
  reference       VARCHAR(50) UNIQUE NOT NULL,
  adresse         VARCHAR(255),
  client_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
  responsable_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
  budget          NUMERIC(14,2) DEFAULT 0,
  statut          statutchantier NOT NULL DEFAULT 'preparation',
  date_debut      DATE,
  date_fin_prev   DATE,
  description     TEXT,
  date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chantiers_reference ON chantiers(reference);
CREATE INDEX IF NOT EXISTS idx_chantiers_statut ON chantiers(statut);

-- ============ RAPPORTS ============
CREATE TABLE IF NOT EXISTS rapports (
  id                SERIAL PRIMARY KEY,
  chantier_id       INTEGER NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
  auteur_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
  date              DATE NOT NULL DEFAULT CURRENT_DATE,
  meteo             VARCHAR(50),
  travaux_realises  TEXT,
  difficultes       TEXT,
  main_oeuvre       TEXT,
  observations      TEXT,
  date_creation     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rapports_chantier ON rapports(chantier_id);
CREATE INDEX IF NOT EXISTS idx_rapports_date ON rapports(date);

-- ============ TACHES ============
CREATE TABLE IF NOT EXISTS taches (
  id              SERIAL PRIMARY KEY,
  chantier_id     INTEGER NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
  responsable_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
  titre           VARCHAR(200) NOT NULL,
  description     TEXT,
  priorite        prioritetache NOT NULL DEFAULT 'moyenne',
  statut          statuttache NOT NULL DEFAULT 'a_faire',
  date_limite     DATE,
  date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_taches_chantier ON taches(chantier_id);
CREATE INDEX IF NOT EXISTS idx_taches_statut ON taches(statut);

-- ============ PHOTOS ============
CREATE TABLE IF NOT EXISTS photos (
  id              SERIAL PRIMARY KEY,
  chantier_id     INTEGER NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
  chemin_fichier  VARCHAR(500) NOT NULL,
  nom_fichier     VARCHAR(255),
  legende         VARCHAR(255),
  uploader_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
  date_upload     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_photos_chantier ON photos(chantier_id);

-- ============ RAPPORT_PHOTOS (jonction) ============
CREATE TABLE IF NOT EXISTS rapport_photos (
  rapport_id  INTEGER REFERENCES rapports(id) ON DELETE CASCADE,
  photo_id    INTEGER REFERENCES photos(id) ON DELETE CASCADE,
  PRIMARY KEY (rapport_id, photo_id)
);

-- ============ RAPPORT_DOCUMENTS ============
CREATE TABLE IF NOT EXISTS rapport_documents (
  id            SERIAL PRIMARY KEY,
  rapport_id    INTEGER NOT NULL REFERENCES rapports(id) ON DELETE CASCADE,
  nom_fichier   VARCHAR(255) NOT NULL,
  chemin        VARCHAR(500) NOT NULL,
  date_upload   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ NOTIFICATIONS ============
CREATE TABLE IF NOT EXISTS notifications (
  id              SERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tache_id        INTEGER REFERENCES taches(id) ON DELETE CASCADE,
  message         VARCHAR(500) NOT NULL,
  lue             BOOLEAN DEFAULT FALSE,
  date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);

-- ============ Compte admin par défaut ============
-- mot de passe = Admin1234! (hash Werkzeug pbkdf2:sha256)
INSERT INTO users (nom, email, mot_de_passe, role)
VALUES (
  'Administrateur',
  'admin@gestbtp.com',
  'pbkdf2:sha256:600000$placeholder$REPLACEMEAFTERMIGRATION',
  'admin'
)
ON CONFLICT (email) DO NOTHING;
-- ⚠ Le hash ci-dessus est un placeholder. Le vrai compte sera créé par
-- l'application au premier `flask init-db`, OU sera importé depuis ta base SQLite
-- existante avec le script python migrate_sqlite_to_supabase.py.
