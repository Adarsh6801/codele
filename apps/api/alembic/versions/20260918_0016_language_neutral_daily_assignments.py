"""Make active daily assignments language-neutral.

Revision ID: 20260918_0016
Revises: 20260918_0015
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0016"
down_revision = "20260918_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical duplicate schedules are retained because submissions and hint
    # use records may point at them. One deterministic record (Python first,
    # then earliest created) becomes the language-neutral active assignment.
    op.drop_constraint(
        "uq_daily_assignment_date_level_language", "daily_assignments", type_="unique"
    )
    op.alter_column("daily_assignments", "language", nullable=True)
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 row_number() OVER (
                   PARTITION BY assignment_date, level
                   ORDER BY CASE WHEN language = 'python' THEN 0 ELSE 1 END, created_at, id
                 ) AS row_number
          FROM daily_assignments
        )
        UPDATE daily_assignments
        SET language = NULL
        FROM ranked
        WHERE daily_assignments.id = ranked.id AND ranked.row_number = 1
        """
    )
    op.create_index(
        "uq_daily_assignment_date_level_active",
        "daily_assignments",
        ["assignment_date", "level"],
        unique=True,
        postgresql_where=sa.text("language IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_daily_assignment_date_level_active", table_name="daily_assignments")
    op.execute("UPDATE daily_assignments SET language = 'python' WHERE language IS NULL")
    op.alter_column("daily_assignments", "language", nullable=False)
    op.create_unique_constraint(
        "uq_daily_assignment_date_level_language",
        "daily_assignments",
        ["assignment_date", "level", "language"],
    )
