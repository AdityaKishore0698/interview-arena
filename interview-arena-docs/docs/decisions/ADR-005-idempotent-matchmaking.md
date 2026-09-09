# ADR 005: Idempotent Matchmaking Reservation

## Status
Accepted

## Context
Matchmaking evaluates candidate eligibility in Redis (as an ephemeral, fast, concurrent memory store). Once an eligible pair is found, an `InterviewSession` must be durably created in PostgreSQL. Because these are two distinct systems without distributed transactions, a failure in PostgreSQL (e.g. network timeout) after Redis has removed the users from the queue could result in permanently lost matches ("black-holing" users). Alternatively, naïve retries could create duplicate `InterviewSession` records for the same match. We need a consistency mechanism without introducing heavy messaging brokers like Kafka or sacrificing the modular monolith architecture.

## Decision
We will implement a Two-Phase Idempotent Match Reservation mechanism:
1. **Atomic Lock (Redis):** A Lua script atomically finds two eligible users, transitions them from `QUEUED` to `LOCKED_FOR_MATCH`, and assigns a pre-generated UUID (`match_id`). The lock has a short TTL (e.g., 10 seconds).
2. **Durable Creation (PostgreSQL):** The backend attempts to insert the `InterviewSession` using the `match_id` as the Primary Key. The `UNIQUE` constraint guarantees idempotency (preventing duplicate sessions on retry).
3. **Commit & Broadcast:** Upon successful database commit, the Redis lock is explicitly cleared and the `MATCH_FOUND` event is broadcast.
4. **Recovery:** If PostgreSQL creation fails or times out, the Redis lock expires naturally. A lightweight recovery process or subsequent queue sweep safely reverts the expired locks back to `QUEUED`.

## Consequences
- **Positive:** Guarantees that users are never permanently lost between the queue and a session.
- **Positive:** Prevents duplicate session rows via database-level constraints.
- **Positive:** Maintains the simplicity of the architecture (no external brokers needed).
- **Negative:** Requires writing custom Lua scripts for Redis atomic operations.
