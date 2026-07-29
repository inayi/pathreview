"""Unit tests for Alembic migration integrity and CI validation wiring (Issue #129).

These tests do not require a database. They parse the migration scripts statically
(via `ast`, avoiding the local ``alembic/`` package that shadows the installed one
when importing from the repo root) and assert the validation plumbing — the shell
script and the CI job — is wired correctly, so broken migrations or a missing CI
step are caught at unit-test time as well as in the dedicated migration job.
"""

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"


class MigrationInfo(NamedTuple):
    path: Path
    revision: str
    down_revision: str | None
    has_upgrade: bool
    has_downgrade: bool


def _string_or_none(node: ast.AST) -> str | None:
    """Return the string value of a literal assignment, or None for `None`."""
    if isinstance(node, ast.Constant):
        return node.value  # str or None
    return None


def _parse_migration(path: Path) -> MigrationInfo:
    """Statically extract revision metadata and function defs from a migration file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    revision: str | None = None
    down_revision: str | None = None
    func_names: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "revision":
                    revision = _string_or_none(node.value)
                elif isinstance(target, ast.Name) and target.id == "down_revision":
                    down_revision = _string_or_none(node.value)

    assert revision is not None, f"{path.name} does not define a `revision` string"
    return MigrationInfo(
        path=path,
        revision=revision,
        down_revision=down_revision,
        has_upgrade="upgrade" in func_names,
        has_downgrade="downgrade" in func_names,
    )


@pytest.fixture(scope="module")
def migrations() -> list[MigrationInfo]:
    files = sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")
    assert files, "No migration files found in alembic/versions/"
    return [_parse_migration(p) for p in files]


@pytest.mark.unit
class TestMigrationChainIntegrity:
    """The migration history must be a single, linear, well-formed chain."""

    def test_exactly_one_base(self, migrations: list[MigrationInfo]):
        """Exactly one initial migration should have `down_revision = None`."""
        bases = [m.revision for m in migrations if m.down_revision is None]
        assert len(bases) == 1, f"Expected exactly one base revision, found: {bases}"

    def test_exactly_one_head(self, migrations: list[MigrationInfo]):
        """A head is a revision no other migration builds on. Multiple heads mean
        branched migrations that `alembic upgrade head` cannot resolve."""
        revisions = {m.revision for m in migrations}
        referenced = {m.down_revision for m in migrations if m.down_revision}
        heads = revisions - referenced
        assert len(heads) == 1, f"Expected exactly one head, found: {heads}"

    def test_down_revisions_reference_known_revisions(self, migrations: list[MigrationInfo]):
        """Every non-base migration must chain to an existing revision (no gaps)."""
        revisions = {m.revision for m in migrations}
        for m in migrations:
            if m.down_revision is None:
                continue
            assert (
                m.down_revision in revisions
            ), f"{m.path.name} references unknown down_revision {m.down_revision!r}"

    def test_revisions_are_unique(self, migrations: list[MigrationInfo]):
        """Duplicate revision ids make the head ambiguous."""
        ids = [m.revision for m in migrations]
        assert len(ids) == len(set(ids)), f"Duplicate revision ids: {ids}"

    def test_every_migration_defines_upgrade_and_downgrade(self, migrations: list[MigrationInfo]):
        for m in migrations:
            assert m.has_upgrade, f"{m.path.name} missing upgrade()"
            assert m.has_downgrade, f"{m.path.name} missing downgrade()"


@pytest.mark.unit
class TestValidationWiring:
    """The validation script and CI job that enforce migration health must exist."""

    def test_validate_script_runs_upgrade_and_check(self):
        """scripts/validate_migrations.sh must run `alembic upgrade head` + `alembic check`."""
        script = REPO_ROOT / "scripts" / "validate_migrations.sh"
        assert script.is_file(), "scripts/validate_migrations.sh is missing"
        text = script.read_text(encoding="utf-8")
        assert "alembic upgrade head" in text
        assert "alembic check" in text
        assert "set -euo pipefail" in text  # fail fast on any error

    def test_ci_has_validate_migrations_job_with_async_url(self):
        """CI must invoke the script with a Postgres service and the async driver URL."""
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "validate-migrations:" in workflow
        assert "scripts/validate_migrations.sh" in workflow
        # env.py uses create_async_engine, so the async driver is required.
        assert "postgresql+asyncpg://" in workflow
        assert "postgres:16-alpine" in workflow

    def test_no_broken_demo_migration_present(self):
        """The Issue #129 reproduction migration must be removed by the fix."""
        demo = VERSIONS_DIR / "003_broken_demo_migration.py"
        assert not demo.exists(), "Remove the reproduction migration before merging"
