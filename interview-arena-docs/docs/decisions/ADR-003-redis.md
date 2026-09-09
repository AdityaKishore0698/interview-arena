# ADR-003 — Use Redis for Ephemeral Coordination

**Status:** Accepted

## Context

Matchmaking queues, presence, active connections, temporary guest state, and short-lived coordination state have different lifecycle and latency requirements from persistent business data.

## Decision

Use Redis for ephemeral/high-speed coordination state.

## Consequences

- low-latency matchmaking
- shared temporary state across backend instances
- atomic operations can help prevent double matching
- persistent business state remains in PostgreSQL
- Redis failure handling must be designed explicitly
