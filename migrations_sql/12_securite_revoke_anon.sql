-- =============================================================
-- GESTBTP — Sécurité base de données
-- Révoque l'accès des rôles publics (anon / authenticated) à toutes les
-- tables métier. Seul le rôle de service (postgres, utilisé par l'app Flask
-- via DATABASE_URL) garde l'accès.
--
-- Pourquoi : la clé publique Supabase (anon) pouvait lire/écrire/supprimer
-- via l'API REST. L'app Flask n'en a pas besoin (elle passe par postgres),
-- donc on coupe cet accès.
-- À exécuter dans Supabase → SQL Editor → Run.
-- =============================================================

-- 1) Retirer les droits déjà accordés sur les tables existantes
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

-- 2) Empêcher que de futures tables/séquences leur soient ouvertes par défaut
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;

-- 3) Retirer l'accès au schéma lui-même (par sécurité)
REVOKE USAGE ON SCHEMA public FROM anon, authenticated;

-- Note : le rôle 'postgres' (et 'service_role') conservent tous leurs droits,
-- donc l'application Flask continue de fonctionner normalement.
