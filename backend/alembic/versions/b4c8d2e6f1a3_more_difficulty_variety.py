"""more difficulty variety in the problem bank

Revision ID: b4c8d2e6f1a3
Revises: a3b7c9d1e2f4
Create Date: 2026-09-26 09:00:00.000000

The previous expansion (f1a2b3c4d5e6) gave each room 8 questions per slot,
but within a given room/slot they were almost all the same difficulty (e.g.
every dsa/slot-1 question was Easy, every system-design question was Hard).
Adds 4 more per slot, chosen specifically to fill in the missing difficulty
levels, so the interviewer has a real choice of difficulty within a room,
not just a choice of topic.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b4c8d2e6f1a3'
down_revision: str | Sequence[str] | None = 'a3b7c9d1e2f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PROBLEMS = [
    # dsa/1 was all Easy — add Medium/Hard
    ('dsa', 1, 'Group Anagrams',
     'Given an array of strings, group the anagrams together. Discuss using a sorted or character-count string as a hash key, and the overall time complexity.',
     'Medium'),
    ('dsa', 1, 'Product of Array Except Self',
     'Return an array where each element is the product of all other elements, without using division. Discuss the prefix/suffix product technique and doing it in O(1) extra space.',
     'Medium'),
    ('dsa', 1, 'Longest Palindromic Substring',
     'Find the longest palindromic substring in a string. Discuss expand-around-center versus dynamic programming, and their time/space trade-offs.',
     'Medium'),
    ('dsa', 1, 'Trapping Rain Water',
     'Given an elevation map, compute how much water it can trap after raining. Discuss the two-pointer approach and why it avoids needing extra arrays.',
     'Hard'),
    # dsa/2 was all Medium — add Easy/Hard
    ('dsa', 2, 'Merge Two Sorted Lists',
     'Merge two sorted linked lists into one sorted list. Discuss the iterative approach with a dummy head node and how it generalises to merging k lists.',
     'Easy'),
    ('dsa', 2, 'Valid Palindrome',
     'Given a string, determine if it is a palindrome considering only alphanumeric characters and ignoring case. Discuss the two-pointer approach.',
     'Easy'),
    ('dsa', 2, 'Serialize and Deserialize a Binary Tree',
     'Design an algorithm to serialize a binary tree to a string and deserialize it back. Discuss pre-order traversal with null markers and why the choice of traversal matters.',
     'Hard'),
    ('dsa', 2, 'N-Queens',
     'Place N queens on an N×N chessboard so no two attack each other; return all distinct solutions. Discuss backtracking with column/diagonal occupancy tracking.',
     'Hard'),
    # system-design/1 was all Hard — add Medium
    ('system-design', 1, 'Design Pastebin',
     'Design a service for sharing text snippets, like Pastebin. Cover ID generation, storage, optional expiry, and read-heavy caching.',
     'Medium'),
    ('system-design', 1, 'Design a Key-Value Store',
     'Design a simple distributed key-value store. Discuss partitioning, replication, and the consistency trade-offs of your read/write path.',
     'Medium'),
    ('system-design', 1, 'Design a Unique ID Generator',
     'Design a service that generates unique, roughly time-sortable IDs at scale, like Twitter\'s Snowflake. Discuss clock skew and coordination between nodes.',
     'Medium'),
    ('system-design', 1, 'Design a Load Balancer',
     'Design a load balancer for a fleet of application servers. Discuss health checks, load-balancing algorithms, and how it handles a backend going down.',
     'Medium'),
    # system-design/2 was all Hard — add Medium
    ('system-design', 2, 'Design a Polling/Voting System',
     'Design a system for live polls with many concurrent votes. Discuss preventing duplicate votes, real-time result updates, and handling a sudden spike.',
     'Medium'),
    ('system-design', 2, 'Design a URL Health Monitoring Service',
     'Design a service that periodically checks a list of URLs and alerts on downtime. Discuss scheduling checks at scale, avoiding false positives, and alert delivery.',
     'Medium'),
    ('system-design', 2, 'Design a Notification Delivery System',
     'Design a system that reliably delivers notifications across push, email, and SMS. Discuss retries, provider fallback, and per-user rate limiting.',
     'Medium'),
    ('system-design', 2, 'Design a Leaderboard Service',
     'Design a real-time leaderboard for a game with millions of players. Discuss using a sorted set for ranking, updating scores at scale, and pagination.',
     'Medium'),
    # oop-lld/1 was all Medium — add Easy/Hard
    ('oop-lld', 1, 'Design a Stack With getMin() in O(1)',
     'Design a stack that supports push, pop, and retrieving the minimum element, all in O(1). Discuss the auxiliary-stack technique.',
     'Easy'),
    ('oop-lld', 1, 'Design a Simple Calculator',
     'Design the classes for a calculator supporting +, -, *, / with undo. Discuss the command pattern and how it makes undo straightforward.',
     'Easy'),
    ('oop-lld', 1, 'Design an In-Memory File System',
     'Design the classes for an in-memory file system supporting directories, files, and path operations. Discuss the composite pattern for files vs. directories.',
     'Hard'),
    ('oop-lld', 1, 'Design a Thread-Safe Bounded Blocking Queue',
     'Design a fixed-capacity queue safe for concurrent producers and consumers, blocking when full or empty. Discuss the synchronization primitives you would use and why.',
     'Hard'),
    # oop-lld/2 had Easy/Medium already — round it out with genuine Hard
    ('oop-lld', 2, 'Design a Concurrent LRU Cache',
     'Design an LRU cache that is safe under concurrent reads and writes. Discuss where contention happens and how you would minimise lock scope.',
     'Hard'),
    ('oop-lld', 2, 'Design a Text Editor with Undo/Redo',
     'Design the classes for a text editor supporting undo/redo of edits. Discuss the command pattern and how you would bound memory for a long edit history.',
     'Hard'),
    ('oop-lld', 2, 'Design an Auction System',
     'Model bidders, items, and bids for an online auction with a hard end time. Discuss how you would handle two bids arriving at nearly the same moment.',
     'Medium'),
    ('oop-lld', 2, 'Design a Snake Game',
     'Design the classes for the classic Snake game: movement, growth on eating food, and collision detection. Discuss how the board and snake body are represented.',
     'Medium'),
]


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, slug FROM interview_rooms")).mappings().all()
    room_id_by_slug = {r['slug']: r['id'] for r in rows}

    insert_stmt = sa.text(
        "INSERT INTO interview_problems (id, room_id, slot, title, prompt, difficulty) "
        "VALUES (gen_random_uuid(), :room_id, :slot, :title, :prompt, :difficulty)"
    )
    for slug, slot, title, prompt, difficulty in NEW_PROBLEMS:
        room_id = room_id_by_slug.get(slug)
        if room_id is None:
            continue
        conn.execute(insert_stmt, {"room_id": room_id, "slot": slot, "title": title, "prompt": prompt, "difficulty": difficulty})


def downgrade() -> None:
    conn = op.get_bind()
    delete_stmt = sa.text("DELETE FROM interview_problems WHERE title = :title AND slot = :slot")
    for _slug, slot, title, _prompt, _difficulty in NEW_PROBLEMS:
        conn.execute(delete_stmt, {"title": title, "slot": slot})
