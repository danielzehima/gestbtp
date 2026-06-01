-- =============================================================
-- GESTBTP — Infos légales/fiscales + couleur d'accent (entreprise)
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

ALTER TABLE comptes ADD COLUMN IF NOT EXISTS rccm            VARCHAR(60);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS nif             VARCHAR(60);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS forme_juridique VARCHAR(60);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS capital         VARCHAR(60);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS banque          VARCHAR(120);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS iban            VARCHAR(80);
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS couleur         VARCHAR(7) DEFAULT '#FF6B00';
