-- =============================================================
-- GESTBTP — Réglages globaux du site (clé/valeur)
-- =============================================================
CREATE TABLE IF NOT EXISTS settings (
  key          VARCHAR(80) PRIMARY KEY,
  value        TEXT,
  date_update  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
