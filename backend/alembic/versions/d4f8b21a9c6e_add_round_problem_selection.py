"""add round problem selection

Revision ID: d4f8b21a9c6e
Revises: c2a1e6f0b3d7
Create Date: 2026-09-22 12:00:00.000000

Lets the interviewer for a round pick a question from the suggested bank
(interview_rounds.problem_id) or write a free-form one instead
(interview_rounds.custom_problem_text). Neither being set means the round
keeps today's behavior: a deterministic auto-pick once it starts.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd4f8b21a9c6e'
down_revision: str | Sequence[str] | None = 'c2a1e6f0b3d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('interview_rounds', sa.Column('problem_id', sa.UUID(), nullable=True))
    op.add_column('interview_rounds', sa.Column('custom_problem_text', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_interview_rounds_problem_id', 'interview_rounds', 'interview_problems',
        ['problem_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_interview_rounds_problem_id', 'interview_rounds', type_='foreignkey')
    op.drop_column('interview_rounds', 'custom_problem_text')
    op.drop_column('interview_rounds', 'problem_id')
