"""Add admin-managed categories to immutable question versions.

Revision ID: 20260918_0012
Revises: 20260918_0011
"""

import re
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260918_0012"
down_revision = "20260918_0011"
branch_labels = None
depends_on = None


def category_slug(name: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "category"
    slug = base
    suffix = 2
    while slug in used:
        slug = f"{base}-{suffix}"
        suffix += 1
    used.add(slug)
    return slug


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_categories_name", "categories", ["name"])
    op.add_column(
        "question_versions",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    bind = op.get_bind()
    topics = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT DISTINCT topic FROM question_versions ORDER BY topic")
        )
    ]
    used_slugs: set[str] = set()
    for topic in topics:
        category_id = uuid4()
        name = topic.strip()
        bind.execute(
            sa.text(
                "INSERT INTO categories (id, name, slug) VALUES (:id, :name, :slug)"
            ),
            {"id": category_id, "name": name, "slug": category_slug(name, used_slugs)},
        )
        bind.execute(
            sa.text("UPDATE question_versions SET category_id = :id WHERE topic = :topic"),
            {"id": category_id, "topic": topic},
        )
    op.alter_column("question_versions", "category_id", nullable=False)
    op.create_foreign_key(
        "fk_question_versions_category_id",
        "question_versions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_question_versions_category_id", "question_versions", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_question_versions_category_id", table_name="question_versions")
    op.drop_constraint("fk_question_versions_category_id", "question_versions", type_="foreignkey")
    op.drop_column("question_versions", "category_id")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
