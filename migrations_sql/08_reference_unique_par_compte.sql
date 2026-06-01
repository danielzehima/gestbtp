-- =============================================================
-- GESTBTP — Référence chantier unique PAR ENTREPRISE (et non globale)
-- Corrige le 500 lors de la création d'un chantier dont la référence
-- existe déjà chez une autre entreprise.
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

-- Supprime l'ancienne contrainte d'unicité globale
ALTER TABLE chantiers DROP CONSTRAINT IF EXISTS chantiers_reference_key;

-- Unicité de la référence au sein d'une même entreprise uniquement
CREATE UNIQUE INDEX IF NOT EXISTS uq_chantier_ref_par_compte
  ON chantiers (compte_id, reference);
