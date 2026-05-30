"""
Migration des données SQLite (gestbtp.db) → Supabase PostgreSQL.

Usage :
    1. Crée d'abord les tables dans Supabase (SQL Editor → fichier
       migrations_sql/01_schema_supabase.sql).
    2. Mets ta DATABASE_URL Supabase (pooler 6543) dans .env.
    3. Lance :   python migrate_sqlite_to_supabase.py
"""
import os
import sqlite3
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'gestbtp.db')
PG_URL = os.environ.get('DATABASE_URL')

if not PG_URL or PG_URL.startswith('sqlite'):
    sys.exit("❌ DATABASE_URL Supabase manquant dans .env (postgresql://...).")

if not os.path.exists(SQLITE_PATH):
    sys.exit(f"❌ Fichier SQLite introuvable : {SQLITE_PATH}")

print("→ Connexion SQLite :", SQLITE_PATH)
src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row

print("→ Connexion Supabase Postgres...")
dst_engine = create_engine(PG_URL)

# Ordre important (respect des FK)
TABLES = [
    'users',
    'chantiers',
    'rapports',
    'taches',
    'photos',
    'rapport_photos',
    'rapport_documents',
    'notifications',
]

def quote_cols(cols):
    return ', '.join(f'"{c}"' for c in cols)

with dst_engine.begin() as dst:
    for table in TABLES:
        try:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            print(f"  ⚠ Table {table} absente dans SQLite — skip")
            continue
        if not rows:
            print(f"  · {table:20s} : 0 ligne")
            continue
        cols = rows[0].keys()
        placeholders = ', '.join([f':{c}' for c in cols])
        sql = text(f'INSERT INTO {table} ({quote_cols(cols)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')
        for r in rows:
            dst.execute(sql, dict(r))
        print(f"  ✓ {table:20s} : {len(rows)} ligne(s) migrée(s)")

    # Re-synchroniser les séquences Postgres (sinon les prochains INSERT échouent)
    print("→ Resync des séquences SERIAL...")
    for t in ('users','chantiers','rapports','taches','photos','rapport_documents','notifications'):
        dst.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{t}','id'), "
            f"COALESCE((SELECT MAX(id) FROM {t}), 1))"
        ))
        print(f"  ✓ séquence {t}_id_seq")

src.close()
print("\n✅ Migration terminée avec succès.")
print("   Vérifie dans Supabase → Table Editor.")
