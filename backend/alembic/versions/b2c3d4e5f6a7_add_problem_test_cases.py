"""add problem test cases for DSA code execution

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23 09:05:00.000000

"Run against test cases" only makes sense for DSA problems (System Design
and OOP/LLD are open-ended design questions with no single correct output).
Piston (the execution engine) runs a full program against raw stdin and
compares raw stdout — there's no per-language function-stub harness — so
each DSA problem gets a short `io_note` describing the exact input/output
convention its test cases use, plus 2 sample test cases the interviewee's
program is checked against.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: str | Sequence[str] | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (title, io_note, [(input, expected_output), ...])
DSA_TEST_CASES: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "Two Sum",
        "Line 1: space-separated integers (nums). Line 2: target integer. "
        "Print the two 0-indexed positions, space-separated, smaller index first.",
        [("2 7 11 15\n9", "0 1"), ("3 2 4\n6", "1 2")],
    ),
    (
        "Valid Parentheses",
        "One line: the string. Print true or false.",
        [("()[]{}", "true"), ("(]", "false")],
    ),
    (
        "Contains Duplicate",
        "One line: space-separated integers. Print true or false.",
        [("1 2 3 1", "true"), ("1 2 3 4", "false")],
    ),
    (
        "Maximum Subarray",
        "One line: space-separated integers (may be negative). Print the maximum subarray sum.",
        [("-2 1 -3 4 -1 2 1 -5 4", "6"), ("1", "1")],
    ),
    (
        "Best Time to Buy and Sell Stock",
        "One line: space-separated prices. Print the maximum achievable profit.",
        [("7 1 5 3 6 4", "5"), ("7 6 4 3 1", "0")],
    ),
    (
        "Valid Anagram",
        "Line 1: string s. Line 2: string t. Print true or false.",
        [("anagram\nnagaram", "true"), ("rat\ncar", "false")],
    ),
    (
        "Reverse a Linked List",
        "One line: space-separated integers representing the list, head first. "
        "Print the reversed list, space-separated.",
        [("1 2 3 4 5", "5 4 3 2 1"), ("1 2", "2 1")],
    ),
    (
        "First Unique Character in a String",
        "One line: the string. Print the 0-indexed position of the first "
        "non-repeating character, or -1 if there isn't one.",
        [("leetcode", "0"), ("aabb", "-1")],
    ),
    (
        "Group Anagrams",
        "One line: space-separated words. Sort each group's words alphabetically, "
        "join a group's words with a single space, then sort the groups by their "
        "first word and join the groups with '|'.",
        [("eat tea tan ate nat bat", "ate eat tea|bat|nat tan"), ("a", "a")],
    ),
    (
        "Longest Palindromic Substring",
        "One line: the string. Print the longest palindromic substring "
        "(if there's a tie, the one starting earliest in the string).",
        [("babad", "bab"), ("cbbd", "bb")],
    ),
    (
        "Product of Array Except Self",
        "One line: space-separated integers. Print the result array, space-separated.",
        [("1 2 3 4", "24 12 8 6"), ("-1 1 0 -3 3", "0 0 9 0 0")],
    ),
    (
        "Trapping Rain Water",
        "One line: space-separated non-negative integers (bar heights). "
        "Print the total units of trapped water.",
        [("0 1 0 2 1 0 1 3 2 1 2 1", "6"), ("4 2 0 3 2 5", "9")],
    ),
    (
        "Merge Two Sorted Lists",
        "Line 1: first sorted list, space-separated. Line 2: second sorted list, "
        "space-separated. Print the merged sorted list, space-separated.",
        [("1 2 4\n1 3 4", "1 1 2 3 4 4"), ("5\n1 2 4", "1 2 4 5")],
    ),
    (
        "Valid Palindrome",
        "One line: the string. Ignoring non-alphanumeric characters and case, "
        "print true or false.",
        [("A man, a plan, a canal: Panama", "true"), ("race a car", "false")],
    ),
    (
        "Number of Islands",
        "Line 1: number of rows R. Next R lines: a row of the grid, each "
        "character '1' (land) or '0' (water). Print the number of islands.",
        [
            ("4\n11110\n11010\n11000\n00000", "1"),
            ("4\n11000\n11000\n00100\n00011", "3"),
        ],
    ),
    (
        "Course Schedule",
        "Line 1: number of courses. Line 2: number of prerequisite pairs. "
        "Next lines: 'a b' meaning course a requires course b first. "
        "Print true if every course can be finished, else false.",
        [("2\n1\n1 0", "true"), ("2\n2\n1 0\n0 1", "false")],
    ),
    (
        "Longest Substring Without Repeating Characters",
        "One line: the string. Print the length of the longest substring "
        "without a repeating character.",
        [("abcabcbb", "3"), ("bbbbb", "1")],
    ),
    (
        "Merge Intervals",
        "Line 1: number of intervals N. Next N lines: 'start end'. Print the "
        "merged, non-overlapping intervals as 'start end', one per line, sorted by start.",
        [("4\n1 3\n2 6\n8 10\n15 18", "1 6\n8 10\n15 18"), ("2\n1 4\n4 5", "1 5")],
    ),
    (
        "Kth Largest Element in an Array",
        "Line 1: space-separated integers. Line 2: k. Print the kth largest value.",
        [("3 2 1 5 6 4\n2", "5"), ("3 2 3 1 2 4 5 5 6\n4", "4")],
    ),
    (
        "Binary Tree Level Order Traversal",
        "One line: the tree in level order, space-separated, using the literal "
        "word 'null' for missing children. Print each level's values space-separated, "
        "with levels separated by '|'.",
        [("3 9 20 null null 15 7", "3|9 20|15 7"), ("1", "1")],
    ),
    (
        "Serialize and Deserialize a Binary Tree",
        "One line: the tree in level order, space-separated, using the literal word "
        "'null' for missing children. Parse it and print it back in the same level-order "
        "form (this checks your parser/rebuilder round-trips correctly).",
        [("1 2 3 null null 4 5", "1 2 3 null null 4 5"), ("1", "1")],
    ),
    (
        "Word Search",
        "Line 1: 'R C' (rows, columns). Next R lines: a row of C characters. "
        "Last line: the word to search for. Print true or false.",
        [
            ("3 4\nABCE\nSFCS\nADEE\nABCCED", "true"),
            ("3 4\nABCE\nSFCS\nADEE\nABCB", "false"),
        ],
    ),
    (
        "LRU Cache",
        "Line 1: capacity. Line 2: number of operations N. Next N lines: "
        "'PUT key value' or 'GET key'. For each GET, print the returned value "
        "(-1 if absent), one per line, in order. PUT prints nothing.",
        [
            (
                "2\n9\nPUT 1 1\nPUT 2 2\nGET 1\nPUT 3 3\nGET 2\nPUT 4 4\nGET 1\nGET 3\nGET 4",
                "1\n-1\n-1\n3\n4",
            ),
            ("1\n5\nPUT 2 1\nGET 2\nPUT 3 2\nGET 2\nGET 3", "1\n-1\n2"),
        ],
    ),
    (
        "N-Queens",
        "One line: N. Print only the number of distinct solutions (not the boards).",
        [("4", "2"), ("8", "92")],
    ),
]


def upgrade() -> None:
    op.add_column('interview_problems', sa.Column('io_note', sa.Text(), nullable=True))

    op.create_table(
        'problem_test_cases',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('problem_id', sa.UUID(), sa.ForeignKey('interview_problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    conn = op.get_bind()
    io_note_stmt = sa.text("UPDATE interview_problems SET io_note = :io_note WHERE title = :title")
    insert_tc_stmt = sa.text(
        "INSERT INTO problem_test_cases (id, problem_id, input, expected_output) "
        "VALUES (gen_random_uuid(), :problem_id, :input, :expected_output)"
    )

    for title, io_note, cases in DSA_TEST_CASES:
        conn.execute(io_note_stmt, {"title": title, "io_note": io_note})
        problem_id = conn.execute(
            sa.text("SELECT id FROM interview_problems WHERE title = :title"), {"title": title}
        ).scalar()
        if problem_id is None:
            continue
        for input_text, expected_output in cases:
            conn.execute(insert_tc_stmt, {"problem_id": problem_id, "input": input_text, "expected_output": expected_output})


def downgrade() -> None:
    op.drop_table('problem_test_cases')
    op.drop_column('interview_problems', 'io_note')
