"""seed_rooms

Revision ID: 999999999999
Revises: 524ab1dd6a84
Create Date: 2026-08-19 14:00:00.000000

"""

from alembic import op

revision = '0002'
down_revision = '524ab1dd6a84'

def upgrade() -> None:
    op.execute("""
        INSERT INTO interview_rooms (slug, name, description)
        VALUES 
            ('dsa', 'DSA', 'Data Structures and Algorithms'),
            ('system-design', 'System Design', 'Large Scale System Design'),
            ('oop-lld', 'OOP / LLD', 'Object Oriented Programming and Low-Level Design')
        ON CONFLICT (slug) DO NOTHING;
    """)

def downgrade() -> None:
    op.execute("DELETE FROM interview_rooms WHERE slug IN ('dsa', 'system-design', 'oop-lld');")
