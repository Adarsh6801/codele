"""Seed the built-in Phase 5 badge catalog.

Revision ID: 20260917_0008
Revises: 20260917_0007
"""

from alembic import op


revision = "20260917_0008"
down_revision = "20260917_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fixed IDs make this deployment seed deterministic. The code remains the
    # public identity and the unique key protects installations that were
    # already bootstrapped by the application service.
    op.execute(
        """
        INSERT INTO badges (id, code, name, description, icon, criteria_json) VALUES
        ('50000000-0000-0000-0000-000000000001', 'first_solve', 'First Commit', 'Complete your first daily challenge.', '⌘', '{"solves": 1}'::jsonb),
        ('50000000-0000-0000-0000-000000000002', 'topic_specialist', 'Topic Specialist', 'Solve five daily challenges in one topic.', '◎', '{"topic_solves": 5}'::jsonb),
        ('50000000-0000-0000-0000-000000000003', 'streak_3', '3-Day Streak', 'Keep your daily practice alive for 3 days.', '🔥', '{"streak_days": 3}'::jsonb),
        ('50000000-0000-0000-0000-000000000004', 'streak_7', '7-Day Streak', 'Keep your daily practice alive for 7 days.', '🔥', '{"streak_days": 7}'::jsonb),
        ('50000000-0000-0000-0000-000000000005', 'streak_14', '14-Day Streak', 'Keep your daily practice alive for 14 days.', '🔥', '{"streak_days": 14}'::jsonb),
        ('50000000-0000-0000-0000-000000000006', 'streak_30', '30-Day Streak', 'Keep your daily practice alive for 30 days.', '🔥', '{"streak_days": 30}'::jsonb),
        ('50000000-0000-0000-0000-000000000007', 'streak_50', '50-Day Streak', 'Keep your daily practice alive for 50 days.', '🔥', '{"streak_days": 50}'::jsonb),
        ('50000000-0000-0000-0000-000000000008', 'streak_100', '100-Day Streak', 'Keep your daily practice alive for 100 days.', '🔥', '{"streak_days": 100}'::jsonb),
        ('50000000-0000-0000-0000-000000000009', 'streak_365', '365-Day Streak', 'Keep your daily practice alive for 365 days.', '🔥', '{"streak_days": 365}'::jsonb)
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM user_badges
        USING badges
        WHERE user_badges.badge_id = badges.id
          AND badges.id::text LIKE '50000000-0000-0000-0000-0000000000%'
        """
    )
    op.execute("DELETE FROM badges WHERE id::text LIKE '50000000-0000-0000-0000-0000000000%'")
