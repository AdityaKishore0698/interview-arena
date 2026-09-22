"""add profile avatar_url

Revision ID: a3b7c9d1e2f4
Revises: f1a2b3c4d5e6
Create Date: 2026-09-25 09:00:00.000000

A profile photo, stored as a small client-resized data: URI or an https:// URL
in a plain text column — no object storage for a demo app's avatar.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a3b7c9d1e2f4'
down_revision: str | Sequence[str] | None = 'f1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('profiles', sa.Column('avatar_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('profiles', 'avatar_url')
