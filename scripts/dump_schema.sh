#!/usr/bin/env bash
# Regenerate database/schema.sql from a freshly migrated database (TRD 20 PGS-016, PGS-017; FEAT-008).
# Usage: scripts/dump_schema.sh [database-url]   (default: $DATABASE_MIGRATION_URL)
# The file is generated, never edited by hand, and regenerated in every PR that changes a migration.
# tests/integration/test_schema_reference.py applies the same normalisation (drop the SET/set_config
# preamble, pg_dump's \restrict lines and the per-column pg_attver options that newer pg_dump
# clients print) and fails on any difference.
set -euo pipefail
url="${1:-${DATABASE_MIGRATION_URL:?set DATABASE_MIGRATION_URL or pass a database URL}}"
url="${url/postgresql+psycopg:\/\//postgresql://}"
out="$(dirname "$0")/../database/schema.sql"
pg_dump --schema-only --no-owner --no-comments --dbname="$url" \
  | grep -v -E '^(SET |SELECT pg_catalog\.set_config|\\restrict |\\unrestrict |-- Dumped (from|by) )' \
  | grep -v -E '^ALTER TABLE ONLY [^ ]+ ALTER COLUMN [^ ]+ SET \(pg_attver=[0-9]+\);$' \
  | cat -s > "$out"
echo "wrote $out"
