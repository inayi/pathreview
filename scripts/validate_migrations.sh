#!/usr/bin/env bash
#
# validate_migrations.sh — Validate Alembic migrations against the SQLAlchemy models.
#
# Applies every migration to a fresh database and then verifies that the resulting
# schema matches the models declared in core/models/. Intended to run in CI (and
# locally) so that broken migrations or schema drift fail fast instead of merging.
#
# Steps:
#   1. `alembic upgrade head` — apply all migrations in order to a clean database.
#      Fails if any migration raises (e.g. references a missing table/column).
#   2. `alembic check`        — diff the live schema against `Base.metadata`
#      (wired via alembic/env.py). Fails if a model change lacks a matching migration.
#
# Requirements:
#   - A reachable, EMPTY PostgreSQL database.
#   - DATABASE_URL must use the async driver, e.g.
#       postgresql+asyncpg://user:pass@host:5432/dbname
#     because alembic/env.py builds the engine with create_async_engine().
#
# Exit codes:
#   0  — all migrations applied cleanly and the schema matches the models.
#   non-zero — a migration failed to apply, or the schema drifted from the models.

set -euo pipefail

# Run from the repository root so alembic.ini and the alembic/ package resolve.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL is not set. Point it at an empty PostgreSQL database" >&2
    echo "       using the async driver, e.g. postgresql+asyncpg://user:pass@host:5432/db" >&2
    exit 1
fi

echo "==> Applying all migrations to a fresh database (alembic upgrade head)"
alembic upgrade head

echo "==> Checking schema matches SQLAlchemy models (alembic check)"
alembic check

echo "==> Migration validation passed: schema is in sync with the models."
