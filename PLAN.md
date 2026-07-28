## Solution plan

**Issue:** Add a database migration validation step to CI that checks all migrations can be applied cleanly — https://github.com/ascherj/pathreview/issues/129

### Understand

**Root cause:** `.github/workflows/ci.yml` defines five jobs — `lint`, `typecheck`,
`test-unit`, `test-integration`, `frontend` — and **none of them ever runs
`alembic upgrade head` or `alembic check`.** Migrations are never applied in CI.

**Expected vs. actual behavior:**
- *Actual:* A broken migration (e.g. one referencing a table/column that does not exist)
  or schema drift between `core/models/` and `alembic/versions/` merges with all checks
  green. Migrations are only verified manually before merge.
- *Expected:* CI provisions a fresh database, applies all migrations sequentially, and
  fails if a migration errors or if the resulting schema does not match the SQLAlchemy
  models.

The building blocks for validation already exist: `alembic/env.py:24` sets the URL at
runtime (`config.set_main_option("sqlalchemy.url", settings.database_url)`),
`alembic/env.py:27` sets `target_metadata = Base.metadata` (imported from `core.models`) —
exactly what `alembic check` compares the live database against — and `pyproject.toml`
pins `alembic>=1.13.0`, so `alembic check` is available.

### Map

Files/modules expected to be involved (with the specific lines/functions in play):
- `scripts/validate_migrations.sh` — currently an empty placeholder; will hold the
  validation logic (`alembic upgrade head` → `alembic check`).
- `.github/workflows/ci.yml` — no alembic step exists today; the existing
  `test-integration` job (lines 48–83) already models the Postgres service pattern to copy.
  Add a new `validate-migrations` job with its own `postgres:16-alpine` service.
- `alembic/env.py` — review only; already correct. `run_async_migrations()` (line 61) builds
  the engine via `create_async_engine(settings.database_url)` (line 63), so the CI
  `DATABASE_URL` must use the async driver `postgresql+asyncpg://…`; `target_metadata`
  is set at line 27.
- `core/config.py` — `database_url` default (line 11) is `postgresql+asyncpg://…`; the CI
  env var overrides it.
- `core/models/__init__.py` (re-exports `Base` + all four models) and `core/database.py:30`
  (`Base = declarative_base()`) — the metadata `alembic check` validates against.
- `Makefile` — has a `migrate:` target (`alembic upgrade head`, lines 63–64) but no
  `validate-migrations`; optionally add one mirroring the script for local runs.
- `alembic/versions/003_broken_demo_migration.py` — the reproduction migration; delete before
  the real fix lands.

### Plan

1. **Implement `scripts/validate_migrations.sh`.** Begin with `set -euo pipefail`. Run
   `alembic upgrade head` to apply every migration to a fresh database, then run
   `alembic check` to diff the live schema against `Base.metadata`. A non-zero exit from
   either command fails the script.
2. **Add a `validate-migrations` job to `ci.yml`** with a `postgres:16-alpine` service
   (user/password/db `pathreview`/`pathreview`/`pathreview_test`, port 5432, `pg_isready`
   health-check), `pip install -e ".[dev]"`, then `bash scripts/validate_migrations.sh`
   with `DATABASE_URL=postgresql+asyncpg://pathreview:pathreview@localhost:5432/pathreview_test`.
3. **(Optional) Add a downgrade→upgrade round-trip** in the script to catch irreversible or
   asymmetric migrations.
4. **Remove the demo `003_broken_demo_migration.py`** so the new job passes on clean history.
5. **(Optional) Mirror as a `Makefile` `validate-migrations` target** for local execution.

### Inputs & outputs

- **Inputs:** migration scripts in `alembic/versions/`; `Base.metadata` from `core.models`;
  a fresh, empty PostgreSQL database provisioned by the CI service container; the async
  `DATABASE_URL` env var.
- **Outputs / what changes:** a new CI job and an executable `scripts/validate_migrations.sh`.
  The job exits **0** when all migrations apply cleanly and the schema matches the models,
  and **non-zero** (failing CI) when a migration is broken or the schema drifts.

**Definition of done (test specification):** the fix is complete when all of the following hold:
1. Against a fresh DB with all valid migrations, `bash scripts/validate_migrations.sh` exits `0`
   (both `alembic upgrade head` and `alembic check` succeed).
2. With `alembic/versions/003_broken_demo_migration.py` present, the script exits non-zero
   (`alembic upgrade head` raises on the nonexistent table) — this is the exact reproduction
   case, so the script must catch what current CI misses.
3. Adding a column to a model in `core/models/` without a matching migration makes the script
   exit non-zero (`alembic check` reports the diff).
4. The `validate-migrations` job appears in the GitHub Actions run and is red for cases 2–3,
   green for case 1.

### Risks & unknowns

- **Driver mismatch** — `alembic/env.py` uses `create_async_engine`, so the job must use
  `postgresql+asyncpg://…`, unlike the existing `test-integration` job's sync
  `postgresql://…` URL. Wrong driver = connection failure.
- **Service health-check timing** — the migration step must wait for the Postgres service in
  `ci.yml` to be ready (health-check retries) to avoid connection-refused flakes.
- **`alembic check` false positives** — dialect defaults, server-side defaults, or type
  normalization in `alembic/env.py`'s comparison can surface spurious diffs; may need
  `compare_type` / `compare_server_default` tuning in `env.py`'s `context.configure`.
- **Postgres-only schema** — models use `postgresql.UUID`/`JSON` (see `core/models/`), so
  there is no SQLite fallback; validation always requires a real Postgres service.

### Edge cases

- **No new migrations:** the job still runs `upgrade head` + `check` and passes as a no-op.
- **Model change without a migration:** `alembic check` exits non-zero — drift is caught.
- **Broken migration:** `alembic upgrade head` raises — the job fails (the case #129 targets).
- **Multiple heads / branched revisions:** `alembic upgrade head` errors on ambiguous heads,
  correctly failing CI.
