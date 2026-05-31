-- =============================================================
-- GESTBTP — Essai gratuit 14 jours & abonnement (sur l'entreprise)
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

ALTER TABLE comptes ADD COLUMN IF NOT EXISTS est_abonne BOOLEAN DEFAULT FALSE;
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS date_fin_essai TIMESTAMP;

-- Grandfathering : les entreprises déjà créées avant cette règle gardent l'accès
-- (on les considère abonnées pour ne bloquer personne).
UPDATE comptes SET est_abonne = TRUE WHERE est_abonne IS NULL OR est_abonne = FALSE;
