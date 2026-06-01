-- =============================================================
-- GESTBTP — Devis & Factures BTP
-- À exécuter dans Supabase → SQL Editor → Run
-- =============================================================

DO $$ BEGIN CREATE TYPE typedocument AS ENUM ('devis','facture');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN CREATE TYPE statutdocument AS ENUM ('brouillon','envoye','accepte','refuse','paye','annule');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS documents (
  id              SERIAL PRIMARY KEY,
  compte_id       INTEGER NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
  chantier_id     INTEGER REFERENCES chantiers(id) ON DELETE SET NULL,
  type            typedocument NOT NULL DEFAULT 'devis',
  numero          VARCHAR(40) NOT NULL,
  client_nom      VARCHAR(200) NOT NULL,
  client_adresse  VARCHAR(300),
  client_email    VARCHAR(120),
  client_tel      VARCHAR(40),
  date_emission   DATE DEFAULT CURRENT_DATE,
  date_echeance   DATE,
  statut          statutdocument NOT NULL DEFAULT 'brouillon',
  tva_taux        NUMERIC(5,2) DEFAULT 18,
  notes           TEXT,
  conditions      TEXT,
  date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_documents_compte ON documents(compte_id);

CREATE TABLE IF NOT EXISTS lignes_document (
  id            SERIAL PRIMARY KEY,
  document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  position      INTEGER DEFAULT 0,
  designation   VARCHAR(300) NOT NULL,
  quantite      NUMERIC(12,2) DEFAULT 1,
  prix_unitaire NUMERIC(14,2) DEFAULT 0,
  unite         VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_lignes_document ON lignes_document(document_id);
