## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/129

**Issue title:** Add a database migration validation step to CI that checks all migrations can be applied cleanly

**Tier:** [ ] Tier 1  [ ] Tier 2  [x] Tier 3

**Problem summary:**
This issue focuses on adding automated schema validation to the project's CI workflow.

What is missing/broken: Currently, database migrations are only verified manually prior to merging, leaving the CI pipeline without a way to automatically detect broken migrations or schema drift.

What a successful fix accomplishes: A proper fix will introduce an automated CI step that provisions a fresh database, runs all schema migrations sequentially, and verifies that the resulting database schema matches the SQLAlchemy models.

Affected codebase areas: This change primarily impacts .github/workflows/ci.yml and requires adding or modifying a validation script under scripts/validate_migrations.sh.

**Branch name:** feat/129-validate-database-migrations

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger