"""add user session_version

Revision ID: e7c4a1f9d2b8
Revises: d4f8b21a9c6e
Create Date: 2026-09-23 09:00:00.000000

Enforces one active session per account: every login (password or Google)
and every logout bumps users.session_version and embeds the new value in the
issued JWT's "sv" claim. get_current_user rejects a token whose "sv" no
longer matches the column, so signing in on a second device invalidates
whatever token was issued to the first. A token with no "sv" claim (issued
before this migration) is treated as version 0, matching the column's
default, so already-logged-in users keep working until they log in again.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e7c4a1f9d2b8'
down_revision: str | Sequence[str] | None = 'd4f8b21a9c6e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('session_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'session_version')
