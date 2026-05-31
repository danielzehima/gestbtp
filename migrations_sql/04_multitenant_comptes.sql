-- =============================================================
-- GESTBTP — Multi-tenant : table comptes (entreprises) + rattachements
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

CREATE TABLE IF NOT EXISTS comptes (
  id                SERIAL PRIMARY KEY,
  nom               VARCHAR(200) NOT NULL,
  owner_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
  plan              planenum NOT NULL DEFAULT 'gratuit',
  statut_abo        statutaboenum NOT NULL DEFAULT 'actif',
  date_souscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  revenu_genere     NUMERIC(12,2) DEFAULT 0,
  date_creation     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rattachement des utilisateurs et chantiers à une entreprise
ALTER TABLE users     ADD COLUMN IF NOT EXISTS compte_id INTEGER REFERENCES comptes(id) ON DELETE SET NULL;
ALTER TABLE chantiers ADD COLUMN IF NOT EXISTS compte_id INTEGER REFERENCES comptes(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_compte ON users(compte_id);
CREATE INDEX IF NOT EXISTS idx_chantiers_compte ON chantiers(compte_id);
