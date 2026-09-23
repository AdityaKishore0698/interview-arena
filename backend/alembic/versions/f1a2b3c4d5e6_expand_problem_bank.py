"""expand problem bank

Revision ID: f1a2b3c4d5e6
Revises: e7c4a1f9d2b8
Create Date: 2026-09-24 09:00:00.000000

The original seed (b1f2c3d4e5a6) gave each room/slot just 2 questions, which
made the interviewer's suggestion list too thin to be useful. Adds 6 more per
room/slot (36 new rows; 48 total), so there's a real bank to search through.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: str | Sequence[str] | None = 'e7c4a1f9d2b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (room_slug, slot, title, prompt, difficulty)
NEW_PROBLEMS = [
    ('dsa', 1, 'Reverse a Linked List',
     'Reverse a singly linked list, both iteratively and recursively. Discuss the pointer-juggling invariant and why the recursive version uses O(n) stack space.',
     'Easy'),
    ('dsa', 1, 'Valid Parentheses',
     'Given a string of brackets ()[]{}, determine if it is valid. Talk through the stack-based approach and how it generalises to other matching problems.',
     'Easy'),
    ('dsa', 1, 'Maximum Subarray',
     'Find the contiguous subarray with the largest sum. Walk through Kadane\'s algorithm and why it works, then discuss how to also return the subarray\'s indices.',
     'Easy'),
    ('dsa', 1, 'Best Time to Buy and Sell Stock',
     'Given an array of daily prices, find the maximum profit from a single buy and a later sell. Discuss the single-pass, track-the-minimum approach and its complexity.',
     'Easy'),
    ('dsa', 1, 'Contains Duplicate',
     'Given an array, determine if any value appears at least twice. Compare the sorting approach, the hash-set approach, and their space/time trade-offs.',
     'Easy'),
    ('dsa', 1, 'First Unique Character in a String',
     'Find the first non-repeating character in a string and return its index. Discuss counting passes vs a single pass with an ordered structure.',
     'Easy'),
    ('dsa', 2, 'LRU Cache',
     'Design and implement a Least Recently Used cache with O(1) get and put. Discuss the hash map + doubly linked list combination and why each piece is needed.',
     'Medium'),
    ('dsa', 2, 'Number of Islands',
     'Given a 2D grid of \'1\'s (land) and \'0\'s (water), count the islands. Discuss DFS vs BFS flood fill, and how you would avoid mutating the input grid.',
     'Medium'),
    ('dsa', 2, 'Course Schedule',
     'Given prerequisites as directed edges, determine if it is possible to finish all courses. Discuss cycle detection via topological sort (Kahn\'s algorithm or DFS colouring).',
     'Medium'),
    ('dsa', 2, 'Longest Substring Without Repeating Characters',
     'Find the length of the longest substring without repeating characters. Discuss the sliding-window technique and how the window\'s left edge advances.',
     'Medium'),
    ('dsa', 2, 'Kth Largest Element in an Array',
     'Find the kth largest element in an unsorted array. Compare sorting, a min-heap of size k, and quickselect, and discuss their complexities.',
     'Medium'),
    ('dsa', 2, 'Word Search',
     'Given a 2D board of letters and a word, determine if the word can be constructed from adjacent cells. Discuss backtracking and how to prune the search.',
     'Medium'),
    ('system-design', 1, 'Design a Web Crawler',
     'Design a web crawler that can crawl billions of pages. Cover URL frontier management, politeness/rate-limiting per domain, deduplication, and distributed coordination.',
     'Hard'),
    ('system-design', 1, 'Design a Search Autocomplete System',
     'Design a typeahead suggestion service. Discuss the trie-based approach, ranking by frequency, how suggestions are kept fresh, and caching hot prefixes.',
     'Hard'),
    ('system-design', 1, 'Design a Distributed Cache',
     'Design a distributed key-value cache like Memcached. Cover consistent hashing for sharding, replication, eviction policy, and handling a node failure.',
     'Hard'),
    ('system-design', 1, 'Design a Payment Processing System',
     'Design a system that processes payments reliably. Discuss idempotency keys, the outbox pattern, handling partial failures, and reconciliation with a payment provider.',
     'Hard'),
    ('system-design', 1, 'Design a File Storage Service',
     'Design a service like Dropbox. Cover chunking large files, deduplication, sync conflict resolution, metadata storage, and how clients detect changes efficiently.',
     'Hard'),
    ('system-design', 1, 'Design a Ticket Booking System',
     'Design a system like Ticketmaster for high-demand events. Discuss seat locking under contention, overselling prevention, and handling a traffic spike at on-sale time.',
     'Hard'),
    ('system-design', 2, 'Design a Video Streaming Service',
     'Design a service like YouTube. Cover video ingestion and transcoding, CDN delivery, adaptive bitrate streaming, and how view counts and recommendations scale.',
     'Hard'),
    ('system-design', 2, 'Design a Ride-Sharing Service',
     'Design a service like Uber. Cover real-time driver location tracking, rider-driver matching, ETA estimation, and surge pricing under load.',
     'Hard'),
    ('system-design', 2, 'Design a Distributed Job Scheduler',
     'Design a system like a distributed cron that reliably fires jobs at scale. Discuss leader election, exactly-once vs at-least-once execution, and handling worker failure.',
     'Hard'),
    ('system-design', 2, 'Design a Web Analytics Pipeline',
     'Design a pipeline that ingests page-view events and produces near-real-time dashboards. Discuss event ingestion, stream processing, storage for aggregation, and late-arriving data.',
     'Hard'),
    ('system-design', 2, 'Design an E-commerce Inventory System',
     'Design inventory management for an e-commerce platform with many warehouses. Discuss stock reservation during checkout, oversell prevention, and eventual consistency across regions.',
     'Hard'),
    ('system-design', 2, 'Design a Collaborative Document Editor',
     'Design a service like Google Docs supporting simultaneous editing. Discuss operational transforms vs CRDTs, conflict resolution, and how changes propagate to other viewers in real time.',
     'Hard'),
    ('oop-lld', 1, 'Design a Library Management System',
     'Model books, members, and loans for a library system. Discuss how you would enforce borrowing limits and due dates, and how the design extends to reservations.',
     'Medium'),
    ('oop-lld', 1, 'Design a Hotel Booking System',
     'Model rooms, room types, and reservations for a hotel booking system. Discuss how you would prevent double-booking a room and support date-range availability search.',
     'Medium'),
    ('oop-lld', 1, 'Design a Restaurant Reservation System',
     'Model tables, parties, and time slots for a restaurant reservation system. Discuss how you would handle walk-ins alongside reservations and table-size matching.',
     'Medium'),
    ('oop-lld', 1, 'Design an ATM',
     'Model the classes and state machine for an ATM: card authentication, PIN checks, and cash withdrawal with denomination logic. Discuss what happens if the machine runs low on a note type.',
     'Medium'),
    ('oop-lld', 1, 'Design a Logging Framework',
     'Design a pluggable logging library with log levels and multiple output destinations (console, file, network). Discuss how you would keep it extensible without touching existing code.',
     'Medium'),
    ('oop-lld', 1, 'Design a Notification System',
     'Design a system that notifies users via email, SMS, and push, triggered by different events. Discuss the observer pattern and how a new notification channel gets added.',
     'Medium'),
    ('oop-lld', 2, 'Design a Tic-Tac-Toe Game',
     'Design the classes for a two-player tic-tac-toe game, including win detection and turn management. Discuss how the board size could be made configurable.',
     'Easy'),
    ('oop-lld', 2, 'Design a Chess Game',
     'Model pieces, the board, and move validation for chess. Discuss how you would represent each piece\'s movement rules without a giant conditional, and how check/checkmate detection fits in.',
     'Medium'),
    ('oop-lld', 2, 'Design a Movie Ticket Booking System',
     'Model theatres, shows, and seat booking for a movie ticket system. Discuss concurrent seat selection and how you would prevent two users from booking the same seat.',
     'Medium'),
    ('oop-lld', 2, 'Design a Food Delivery Order System',
     'Model restaurants, menus, orders, and delivery assignment for a food delivery app. Discuss the order\'s state machine from placed to delivered.',
     'Medium'),
    ('oop-lld', 2, 'Design an Expense-Sharing App',
     'Design a system like Splitwise for splitting shared expenses among a group. Discuss how you would model balances between members and simplify a group\'s debts.',
     'Medium'),
    ('oop-lld', 2, 'Design a Task Scheduler',
     'Design an in-process task scheduler that runs jobs on a delay or a recurring interval. Discuss how you would handle a job that\'s still running when its next occurrence is due.',
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
            continue  # room not seeded in this environment; skip rather than fail the migration
        conn.execute(insert_stmt, {"room_id": room_id, "slot": slot, "title": title, "prompt": prompt, "difficulty": difficulty})


def downgrade() -> None:
    conn = op.get_bind()
    delete_stmt = sa.text("DELETE FROM interview_problems WHERE title = :title AND slot = :slot")
    for _slug, slot, title, _prompt, _difficulty in NEW_PROBLEMS:
        conn.execute(delete_stmt, {"title": title, "slot": slot})
