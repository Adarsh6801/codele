"""Seed common authoring categories for a fresh Codele installation.

Revision ID: 20260918_0014
Revises: 20260918_0013
"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260918_0014"
down_revision = "20260918_0013"
branch_labels = None
depends_on = None

CORE_CATEGORIES = (
    ("Arrays", "arrays", "Traversal, indexing, and array transformations."),
    ("Linked Lists", "linked-lists", "Singly and doubly linked list operations."),
    ("Trees", "trees", "Binary trees, traversal, and tree-based search."),
    ("Recursion", "recursion", "Recursive decomposition and backtracking foundations."),
)


def upgrade() -> None:
    bind = op.get_bind()
    for name, slug, description in CORE_CATEGORIES:
        bind.execute(
            sa.text(
                """
                INSERT INTO categories (id, name, slug, description)
                VALUES (:id, :name, :slug, :description)
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": uuid4(), "name": name, "slug": slug, "description": description},
        )


def downgrade() -> None:
    # Seed rows may have been edited or assigned by an administrator, so a
    # downgrade deliberately preserves user-controlled category records.
    pass
