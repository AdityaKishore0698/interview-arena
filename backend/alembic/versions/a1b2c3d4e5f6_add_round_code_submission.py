"""add round code submission

Revision ID: a1b2c3d4e5f6
Revises: b4c8d2e6f1a3
Create Date: 2026-09-23 09:00:00.000000

The code editor is optional and interviewee-only: when the interviewer asks
them to code the solution, they can open it, write in any supported
language, and submit — at which point the interviewer can see it too. This
stores that single latest submission per round (not a run history), kept
alongside feedback so it shows up later in interview history.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = 'b4c8d2e6f1a3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('interview_rounds', sa.Column('submitted_code', sa.Text(), nullable=True))
    op.add_column('interview_rounds', sa.Column('submitted_language', sa.String(length=30), nullable=True))
    op.add_column('interview_rounds', sa.Column('code_submitted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_rounds', 'code_submitted_at')
    op.drop_column('interview_rounds', 'submitted_language')
    op.drop_column('interview_rounds', 'submitted_code')
