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
