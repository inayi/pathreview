## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/129

**Issue title:** Add a database migration validation step to CI that checks all migrations can be applied cleanly

**Tier:** [ ] Tier 1  [ ] Tier 2  [x] Tier 3

**Problem summary:**
This issue focuses on adding automated schema validation to the project's CI workflow.

What is missing/broken: Currently, database migrations are only verified manually prior to merging, leaving the CI pipeline without a way to automatically detect broken migrations or schema drift.

What a successful fix accomplishes: A proper fix will introduce an automated CI step that provisions a fresh database, runs all schema migrations sequentially, and verifies that the resulting database schema matches the SQLAlchemy models.

Affected codebase areas: This change primarily impacts .github/workflows/ci.yml and requires adding or modifying a validation script under scripts/validate_migrations.sh.

### Issue Fit & Selection Reasoning

#### "Is This Issue Right for Me?" Checklist Evaluation

* **Part 1 — Understanding the Issue:**
  * **Problem & Expected Behavior:** CI needs an automated check to verify that all database migrations apply cleanly to a fresh database and match model definitions before PRs are merged.
  * **Located Code & Scope:** Verified `.github/workflows/ci.yml`, `alembic/`, and existing script entries under `scripts/`.
  * **Before vs. After:** *Before:* Broken migrations or schema drift are only caught manually or after merging. *After:* CI automatically runs migrations against a service container and fails if schema mismatches occur.

* **Part 2 — Tier Fit & Scope Reasoning:**
  * **Tier Selection:** Tier 3 (Infrastructure / CI Pipeline & Database Validation).
  * **Fit Justification:** Prior extensive experience as a build/release engineer and CI/CD pipelines makes this Tier 3 task a direct match for my technical background, while allowing me to focus on database DevOps without getting bogged down in frontend state management.

* **Part 3 — Codebase Readiness & Prerequisites:**
  * **Code & Context:** Reviewed Alembic configuration (`alembic.ini`, `alembic/env.py`) and standard migration commands (`alembic upgrade head`).
  * **Test Awareness:** Inspected `tests/` directory to understand existing testing setups and service container configurations.
  * **Prerequisites:** Familiarity with GitHub Actions service containers (PostgreSQL), Alembic CLI, and SQLAlchemy schema diffing (`alembic check`).

* **Part 4 — Scope & Time Estimation:**
  * **Dependencies & Claims:** No open blockers or blocking issue dependencies identified. Checked cohort ledger claims.
  * **Time Estimate:** **4–6 hours total**
    * *1–2 hrs:* Local script development (`scripts/validate_migrations.sh` running `alembic upgrade head` and `alembic check`).
    * *2–3 hrs:* Configuring PostgreSQL service container and step integration in `.github/workflows/ci.yml`.
    * *1 hr:* Testing edge cases, failure states, and CI run validation.


**Branch name:** feat/129-validate-database-migrations

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger


## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/ascherj/pathreview/commit/57b17b04e4bc5468ff849352aeeedc6319d764d8

**Reproduction summary:**
Added an intentionally broken Alembic migration (`alembic/versions/003_broken_demo_migration.py`, which adds a column to a nonexistent table) and confirmed CI stays green because no job in `.github/workflows/ci.yml` runs `alembic upgrade head` or `alembic check` — proving CI currently lacks migration validation.

**PLAN.md link:** https://github.com/inayi/pathreview/blob/feat/129-validate-database-migrations/PLAN.md

**Walkthrough video (recommended):** [link to your Loom video, ≤2 min — recommended, not graded]

**Blockers or open questions:**

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**
Completed the core PLAN.md sub-tasks: (1) implemented `scripts/validate_migrations.sh`, which runs `alembic upgrade head` against a fresh database then `alembic check` to diff the live schema against `Base.metadata`, failing on any error; (2) added a `validate-migrations` job to `.github/workflows/ci.yml` with a `postgres:16-alpine` service and the async `DATABASE_URL` (`postgresql+asyncpg://…`) that `alembic/env.py` requires; (3) added a `make validate-migrations` target; (4) removed the reproduction migration `alembic/versions/003_broken_demo_migration.py`.

**Next steps:**
Add unit tests for migration-chain integrity and the CI wiring (`tests/unit/test_migrations.py`), run `make check` and `make test-unit` to confirm no new failures, then open the PR.

**Blockers:**
Local venv is Python 3.14 while the project targets 3.11, so dependency install was slow; this only affects local verification, not the CI job (which pins 3.11).

---

### Check-in 2 (end of week)

**PR link:** https://github.com/ascherj/pathreview/pull/363

**Branch:** `feat/129-validate-database-migrations`

**What you built:**
A CI migration-validation step for Issue #129. A new `validate-migrations` job in `.github/workflows/ci.yml` spins up a fresh Postgres service and runs `scripts/validate_migrations.sh`, which applies all Alembic migrations (`alembic upgrade head`) and then verifies the resulting schema matches the SQLAlchemy models (`alembic check`) — failing CI on broken migrations or schema drift, which previously merged unnoticed.

**Tests added or updated:**
Added `tests/unit/test_migrations.py`. It covers migration-chain integrity without a database (exactly one head, one base, an unbroken head→base chain, and every migration defining `upgrade()`/`downgrade()`) and verifies the validation wiring (the script runs `alembic upgrade head` + `alembic check` under `set -euo pipefail`; the CI job exists with a `postgres:16-alpine` service and the async driver URL; and the reproduction migration was removed).

**Self-review confirmation:** [x] make check passes  [x] make test-unit passes

> Documented pre-existing failures: the local dev environment runs Python 3.14 while the project targets 3.11 (`make check` mypy rejects numpy's 3.12+ stubs; ruff/black and 53 unit tests fail in modules unrelated to this change). My changes introduce **no new failures** — baseline without my test file is `53 failed / 375 passed`; with it, `53 failed / 383 passed` (my 8 new tests pass). My added/changed files pass `ruff` and `black` cleanly. CI runs on Python 3.11, where these pre-existing issues do not occur.

**Draft PR feedback received from:** none

## Week 10 — Iteration & reflection

### Reviewer feedback

**Feedback received:** [ ] Yes  [x] No — still awaiting review

**Summary of feedback:**
[What did reviewers comment on? Or note that no review came in.]

**How you responded:**
[What changes did you make, or what did you reply? If no feedback,
leave blank.]

---

### Reflection

**What was harder than you expected?**
- Navigating an unfamiliar production codebase to isolate the exact root cause behind database migration and schema validation failures was more challenging than anticipated. Tracing how Alembic migrations interact asynchronously with SQLAlchemy models and discovering that Alembic's Python package path was shadowed locally required deep debugging rather than just straightforward code reading.

**What did you learn about working in a large codebase?**
- When contributing to an existing codebase vs. building a project from scratch, you cannot rely on mental models or assumptions. You must actively reverse engineer system behavior—such as step-debugging environment scripts or writing reproduction cases—to verify root causes. Validating changes safely requires confirming that fixes address edge cases without introducing regressions to unrelated modules or existing workflows.

**How did AI tools help — and where did they fall short?**
- AI tools were highly effective for high-level architectural mapping, summarizing file roles, and drafting initial boilerplate syntax. However, they fell short when handling subtle environment dependencies—such as async driver configurations (postgresql+asyncpg://) or isolated container testing. AI-generated code required strict human verification to catch subtle hallucinations, syntax misconfigurations, and static test anti-patterns.

**What would you do differently if you started over?**
- If starting over, I would select an issue targeting application or business logic rather than infrastructure/migration tooling. CI database migration testing relies heavily on mimicking production-like state, isolated service containers, and runtime schema diffing. A feature or bug-fix issue would have allowed more direct iteration on unit test behavior without spending significant cycles setting up containerized DB environments.

**What are you most proud of from this module?**
- I am most proud of executing a complete, professional open-source contribution workflow end-to-end. From reproducing the initial issue with a failing test case and detailing a solution plan to configuring a robust CI validation pipeline with dockerized testing and writing a clean PR description, I demonstrated how to deliver production-grade infrastructure changes with high rigor.

