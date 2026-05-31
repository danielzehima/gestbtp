-- =============================================================
-- GESTBTP — Ajout du forfait "gratuit" au type ENUM planenum
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

-- Ajoute la valeur 'gratuit' au type enum (sans erreur si déjà présente).
ALTER TYPE planenum ADD VALUE IF NOT EXISTS 'gratuit' BEFORE 'starter';

-- (Optionnel) Mettre les comptes sans plan défini sur 'gratuit' :
-- UPDATE users SET plan = 'gratuit' WHERE plan IS NULL;
