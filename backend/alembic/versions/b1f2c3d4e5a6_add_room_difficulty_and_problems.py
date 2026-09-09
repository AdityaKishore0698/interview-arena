"""add room difficulty and interview problems

Revision ID: b1f2c3d4e5a6
Revises: a8e9876e9f00
Create Date: 2026-08-29 16:20:00.000000

Adds authoritative human-readable metadata to the interview experience:
- interview_rooms.difficulty (e.g. DSA -> Easy)
- interview_problems: a small seeded bank of problems, keyed by room and
  round slot, so the interviewer is given a real question to ask instead
  of an empty textarea.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b1f2c3d4e5a6'
down_revision: str | Sequence[str] | None = 'a8e9876e9f00'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'interview_rooms',
        sa.Column('difficulty', sa.String(length=20), nullable=False, server_default='Medium'),
    )
    op.execute("UPDATE interview_rooms SET difficulty = 'Easy' WHERE slug = 'dsa'")
    op.execute("UPDATE interview_rooms SET difficulty = 'Hard' WHERE slug = 'system-design'")
    op.execute("UPDATE interview_rooms SET difficulty = 'Medium' WHERE slug = 'oop-lld'")

    op.create_table(
        'interview_problems',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('slot BETWEEN 1 AND 2', name='chk_problem_slot'),
        sa.ForeignKeyConstraint(['room_id'], ['interview_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interview_problems_room_slot', 'interview_problems', ['room_id', 'slot'])

    op.execute(
        """
        INSERT INTO interview_problems (id, room_id, slot, title, prompt, difficulty)
        SELECT gen_random_uuid(), r.id, p.slot, p.title, p.prompt, p.difficulty
        FROM interview_rooms r
        JOIN (
            VALUES
              ('dsa', 1, 'Two Sum',
               'Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target. Assume exactly one solution and that the same element may not be used twice. Discuss the brute-force approach first, then optimise. Follow-up: what changes if the array is sorted?',
               'Easy'),
              ('dsa', 1, 'Valid Anagram',
               'Given two strings s and t, determine whether t is an anagram of s. Talk through the counting approach and its complexity. Follow-up: how would you handle Unicode characters?',
               'Easy'),
              ('dsa', 2, 'Merge Intervals',
               'Given an array of intervals where intervals[i] = [start, end], merge all overlapping intervals and return the non-overlapping intervals that cover all the input. Discuss sorting, the sweep, and edge cases (touching vs overlapping).',
               'Medium'),
              ('dsa', 2, 'Binary Tree Level Order Traversal',
               'Given the root of a binary tree, return the level-order traversal of its node values (left to right, level by level). Discuss BFS with a queue and how to delimit levels.',
               'Medium'),
              ('system-design', 1, 'Design a URL Shortener',
               'Design a service like bit.ly. Cover the API, key generation strategy (hash vs counter vs base62), storage schema, read/write ratio, caching, and how you would handle 100M new URLs per month. Discuss redirect latency and analytics.',
               'Hard'),
              ('system-design', 1, 'Design a Rate Limiter',
               'Design a distributed rate limiter used by an API gateway. Compare token bucket, leaky bucket, and sliding window. Discuss where state lives, race conditions across nodes, and what happens when the store is unavailable.',
               'Hard'),
              ('system-design', 2, 'Design a News Feed',
               'Design the news feed for a social network. Discuss fan-out on write vs fan-out on read, the celebrity problem, feed ranking, pagination, and caching. Estimate storage and QPS.',
               'Hard'),
              ('system-design', 2, 'Design a Chat Service',
               'Design a 1:1 and group chat service. Cover connection management (long poll vs websockets), message delivery guarantees, ordering, presence, storage, and read receipts. Discuss horizontal scaling of the websocket tier.',
               'Hard'),
              ('oop-lld', 1, 'Design a Parking Lot',
               'Design the classes for a parking lot system with multiple levels and spot sizes (motorcycle, compact, large). Model vehicles, spots, tickets, and the pricing strategy. Discuss how you keep spot assignment thread-safe.',
               'Medium'),
              ('oop-lld', 1, 'Design an Elevator System',
               'Design the object model for a building with N elevators. Model requests (internal vs external), the scheduling strategy, and elevator state. Discuss how the controller decides which car serves a request.',
               'Medium'),
              ('oop-lld', 2, 'Design a Deck of Cards',
               'Design the classes for a deck of cards and a simple blackjack game. Model Card, Deck, Hand, and the dealer. Discuss shuffling and how to make the design reusable for other card games.',
               'Easy'),
              ('oop-lld', 2, 'Design a Vending Machine',
               'Design a vending machine using a state machine (idle, has-money, dispensing, out-of-stock). Model products, inventory, coins, and change-making. Discuss how new states or payment methods are added.',
               'Medium')
        ) AS p(slug, slot, title, prompt, difficulty) ON p.slug = r.slug;
        """
    )

    op.alter_column('interview_rooms', 'difficulty', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_interview_problems_room_slot', table_name='interview_problems')
    op.drop_table('interview_problems')
    op.drop_column('interview_rooms', 'difficulty')
