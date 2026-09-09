# ADR-002 — Use PostgreSQL for Persistent Business Data

**Status:** Accepted

## Context

Interview Arena needs durable relational data for users, sessions, rounds, feedback, and history.

## Decision

Use PostgreSQL as the primary persistent database.

## Consequences

- strong transactional guarantees
- relational integrity
- flexible querying
- appropriate for persistent business entities
- later scaling may require indexing, read replicas, partitioning, or other techniques based on evidence
