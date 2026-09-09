"""create_session_tables

Revision ID: 7e93940e4498
Revises: 0002
Create Date: 2026-08-20 10:38:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '7e93940e4498'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table('interview_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_rooms.id'), nullable=False),
        sa.Column('mode', sa.String(length=50), nullable=False, server_default='STANDARD'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('abandoned_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table('interview_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('seat', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    op.create_unique_constraint('uq_session_user', 'interview_participants', ['session_id', 'user_id'])
    op.create_unique_constraint('uq_session_seat', 'interview_participants', ['session_id', 'seat'])

def downgrade() -> None:
    op.drop_table('interview_participants')
    op.drop_table('interview_sessions')
