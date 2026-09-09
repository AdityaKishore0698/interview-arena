# ADR-001 — Start with a Modular Monolith

**Status:** Accepted

## Context

The MVP has a small scope and does not yet require independently scalable services. Microservices would add operational and deployment complexity.

## Decision

Start with a modular monolith.

Internal boundaries will exist between Identity, Interview, Matchmaking, Feedback/Rating, and Real-Time modules.

## Consequences

### Positive

- simpler local development
- simpler deployment
- easier debugging
- straightforward database transactions
- clear path to later extraction if required

### Negative

- modules share one deployment
- some boundaries may need refactoring if the system grows significantly
