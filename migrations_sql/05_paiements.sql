-- =============================================================
-- GESTBTP — Historique des paiements GenuisPay
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

DO $$ BEGIN
  CREATE TYPE statutpaiement AS ENUM ('en_attente','reussi','echoue');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS paiements (
  id            SERIAL PRIMARY KEY,
  compte_id     INTEGER NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
  reference     VARCHAR(80) UNIQUE NOT NULL,
  provider_ref  VARCHAR(120),
  plan          VARCHAR(20),
  montant       NUMERIC(12,2) DEFAULT 0,
  statut        statutpaiement NOT NULL DEFAULT 'en_attente',
  date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  date_paiement TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_paiements_compte ON paiements(compte_id);
CREATE INDEX IF NOT EXISTS idx_paiements_reference ON paiements(reference);
