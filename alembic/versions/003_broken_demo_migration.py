"""BROKEN DEMO migration to reproduce Issue #129 (CI migration-validation gap).

This migration is INTENTIONALLY BROKEN. It adds a column to a table that does not
exist, so `alembic upgrade head` fails against a real database. It exists solely to
demonstrate that the current CI workflow (.github/workflows/ci.yml) stays green even
with a broken migration present, because no CI job runs `alembic upgrade head` or
`alembic check`.

REMOVE THIS FILE before implementing the actual fix (see PLAN.md) — otherwise the new
migration-validation job would correctly fail.

Revision ID: 003
Revises: 002
Create Date: 2026-07-28 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentionally broken: "nonexistent_table" is not defined in any prior migration,
    # so this raises when applied to a real database.
    op.add_column(
        "nonexistent_table",
        sa.Column("demo_broken_column", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("nonexistent_table", "demo_broken_column")
