# PLAN.md — Issue #129: Add database migration validation to CI

**Issue:** https://github.com/ascherj/pathreview/issues/129
**Branch:** `feat/129-validate-database-migrations`

---

## 1. Understand

**Problem:** Database migrations are only verified manually before merging. The CI
workflow has no way to automatically catch broken migrations or schema drift between
Alembic migrations and the SQLAlchemy models.

**Root cause:** `.github/workflows/ci.yml` defines five jobs — `lint`, `typecheck`,
`test-unit`, `test-integration`, `frontend` — and **none of them ever runs
`alembic upgrade head` or `alembic check`.** Migrations are never applied in CI, so:

- A **broken migration** (e.g. one that references a table/column that does not exist)
  merges with all checks green.
- **Schema drift** — a change in `core/models/` without a corresponding migration — is
  never detected.

The pieces needed for validation already exist:
- `alembic/env.py` sets `target_metadata = Base.metadata` (imported from `core.models`),
  which is exactly what `alembic check` compares the live database against.
- `alembic/env.py` builds an engine via `create_async_engine(settings.database_url)`, so
  online migrations require an **async** driver URL (`postgresql+asyncpg://…`).
- `pyproject.toml` pins `alembic>=1.13.0`, so `alembic check` (added in 1.9.0) is available.

Reproduction of the gap is committed as the intentionally broken migration
`alembic/versions/003_broken_demo_migration.py` (see JOURNAL Week 8) — CI stays green
despite it.

## 2. Map — files to create / modify

- `scripts/validate_migrations.sh` **(create/implement)** — currently an empty placeholder.
  Runs `alembic upgrade head` against a fresh DB, then `alembic check` to compare the
  resulting schema to the models. Exits non-zero on any failure.
- `.github/workflows/ci.yml` **(modify)** — add a `validate-migrations` job with a
  `postgres:16-alpine` service (with a health-check) that installs deps and runs the script.
- `alembic/env.py` **(review only — no change expected)** — already correct: async engine
  plus `target_metadata = Base.metadata`.
- `Makefile` **(optional)** — add a `validate-migrations` target mirroring the script for
  local runs (the Makefile already has a `migrate` target).
- `alembic/versions/003_broken_demo_migration.py` **(delete)** — remove the reproduction
  migration before the real fix lands.

## 3. Plan — concrete steps

1. **Implement `scripts/validate_migrations.sh`.** Start with `set -euo pipefail`. Run
   `alembic upgrade head` to apply every migration to a fresh database, then run
   `alembic check` to diff the live schema against `Base.metadata`. Any non-zero exit from
   either command fails the script.
2. **Add the `validate-migrations` CI job** to `ci.yml`: a `postgres:16-alpine` service
   (user/password/db `pathreview`/`pathreview`/`pathreview_test`, port 5432, `pg_isready`
   health-check), `pip install -e ".[dev]"`, then `bash scripts/validate_migrations.sh`
   with `DATABASE_URL=postgresql+asyncpg://pathreview:pathreview@localhost:5432/pathreview_test`
   (async driver, matching `env.py`).
3. **(Optional) Add a downgrade→upgrade round-trip** in the script to catch irreversible or
   asymmetric migrations.
4. **Remove the demo `003_*` broken migration** so the new job passes on a clean history.
5. **(Optional) Mirror as a `Makefile` `validate-migrations` target** for local execution.

## 4. Inputs & outputs

- **Inputs:** migration scripts in `alembic/versions/`; `Base.metadata` from `core.models`;
  a fresh, empty PostgreSQL database provisioned by the CI service container.
- **Outputs:** exit code **0** when all migrations apply cleanly and the resulting schema
  matches the models; **non-zero** (failing the CI job) when a migration is broken or when
  the schema drifts from the models.

## 5. Risks & unknowns

- **Driver mismatch:** `env.py` uses `create_async_engine`, so the job must use
  `postgresql+asyncpg://…`, unlike the existing `test-integration` job's sync
  `postgresql://…` URL.
- **Service health-check timing:** the migration step must wait for Postgres to be ready
  (health-check retries) to avoid connection-refused flakes.
- **`alembic check` false positives:** dialect-specific defaults, server-side defaults, or
  type normalization can surface as spurious diffs and may need tuning of comparison options.
- **Postgres-only schema:** models use `postgresql.UUID`/`JSON`, so there is no SQLite
  fallback — validation always requires a real Postgres service.

## 6. Edge cases

- **No new migrations:** the job still runs `upgrade head` + `check` and passes as a no-op.
- **Model change without a migration:** `alembic check` exits non-zero — drift is caught.
- **Broken migration:** `alembic upgrade head` raises — the job fails (the exact case #129
  targets).
- **Multiple heads / branched revisions:** `alembic upgrade head` errors on ambiguous heads,
  correctly failing CI.
