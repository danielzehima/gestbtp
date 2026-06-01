-- =============================================================
-- GESTBTP — Identité entreprise (en-tête devis/factures)
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

ALTER TABLE comptes ADD COLUMN IF NOT EXISTS logo_url       VARCHAR(500);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS raison_sociale VARCHAR(200);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS adresse        VARCHAR(300);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS telephone      VARCHAR(40);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS email          VARCHAR(120);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS site_web       VARCHAR(120);
