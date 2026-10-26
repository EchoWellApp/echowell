-- Local and CI database provisioning (TRD 15 §4.2, TRD 20 §4.2-§4.3, TRD 16 CIC-015; TRD 24 D-72, D-90).
-- Run once as the PostgreSQL superuser right after the server starts:
--   Compose: mounted into /docker-entrypoint-initdb.d (empty volume only);
--   CI: psql -v ON_ERROR_STOP=1 -f database/roles/provision_login_roles.sql
-- Never run on staging, production or AWS (login roles are created there in the provider console).
-- Passwords come from ECHOWELL_MIGRATOR_DB_PASSWORD, ECHOWELL_APP_DB_PASSWORD and
-- ECHOWELL_READONLY_DB_PASSWORD through psql \getenv and are never printed. Idempotent.
\set ON_ERROR_STOP on

-- Extensions and database time zone: only here, never in Alembic (D-72, PGS-001, PGS-002).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;
SELECT format('ALTER DATABASE %I SET timezone = %L', current_database(), 'UTC') \gexec

-- Group roles (TRD 20 §4.3).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_migrator') THEN
    CREATE ROLE echowell_migrator NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_app') THEN
    CREATE ROLE echowell_app NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_readonly') THEN
    CREATE ROLE echowell_readonly NOLOGIN;
  END IF;
END
$$;

ALTER SCHEMA public OWNER TO echowell_migrator;

-- Login roles, each a member of only its own group role (PGS-040).
\getenv migrator_password ECHOWELL_MIGRATOR_DB_PASSWORD
\getenv app_password ECHOWELL_APP_DB_PASSWORD
\getenv readonly_password ECHOWELL_READONLY_DB_PASSWORD

SELECT format('CREATE ROLE %I LOGIN IN ROLE %I', login, grp)
FROM (VALUES ('echowell_migrator_login', 'echowell_migrator'),
             ('echowell_app_login', 'echowell_app'),
             ('echowell_readonly_login', 'echowell_readonly')) AS r(login, grp)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r.login) \gexec

SELECT format('ALTER ROLE echowell_migrator_login PASSWORD %L', :'migrator_password') \gexec
SELECT format('ALTER ROLE echowell_app_login PASSWORD %L', :'app_password') \gexec
SELECT format('ALTER ROLE echowell_readonly_login PASSWORD %L', :'readonly_password') \gexec
