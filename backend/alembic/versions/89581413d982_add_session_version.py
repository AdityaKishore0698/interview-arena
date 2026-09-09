"""add_session_version

Revision ID: 89581413d982
Revises: 7e93940e4498
Create Date: 2026-08-20 10:45:54.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '89581413d982'
down_revision: str | None = '7e93940e4498'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column('interview_sessions', sa.Column('version', sa.Integer(), server_default='1', nullable=False))

def downgrade() -> None:
    op.drop_column('interview_sessions', 'version')
