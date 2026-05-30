-- =============================================================
-- GESTBTP — Ajout des champs d'abonnement SaaS sur la table users
-- À exécuter dans Supabase → SQL Editor → Run
-- (à lancer APRÈS 01_schema_supabase.sql)
-- =============================================================

-- Nouveaux types ENUM
DO $$ BEGIN
  CREATE TYPE planenum AS ENUM ('starter','pro','entreprise');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE statutaboenum AS ENUM ('actif','suspendu','annule');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Nouvelles colonnes (IF NOT EXISTS = ré-exécutable sans erreur)
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan planenum DEFAULT 'starter';
ALTER TABLE users ADD COLUMN IF NOT EXISTS statut_abo statutaboenum DEFAULT 'actif';
ALTER TABLE users ADD COLUMN IF NOT EXISTS date_souscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS revenu_genere NUMERIC(10,2) DEFAULT 0;
