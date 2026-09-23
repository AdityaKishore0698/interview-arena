"""add user streaks

Revision ID: c2a1e6f0b3d7
Revises: b1f2c3d4e5a6
Create Date: 2026-09-22 10:00:00.000000

Adds user_streaks: one row per user tracking a daily login streak (advanced
by POST /auth/streaks/checkin) and a daily interview streak (advanced when a
registered-user session reaches COMPLETED). Rows are created lazily on first
check-in, not at signup.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c2a1e6f0b3d7'
down_revision: str | Sequence[str] | None = 'b1f2c3d4e5a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_streaks',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('login_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_login_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('login_streak_last_date', sa.Date(), nullable=True),
        sa.Column('interview_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_interview_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('interview_streak_last_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_streaks')
