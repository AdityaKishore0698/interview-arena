# Testing ADR Review Note

Phase 0.13 does not require a new architectural ADR.

The testing strategy introduces implementation constraints:
- domain logic must be testable without infrastructure
- time must be injectable for deterministic timer tests
- infrastructure integration tests should use real PostgreSQL/Redis behavior where semantics matter
- concurrency-sensitive operations require explicit tests

If implementation later adopts a specific testing framework, testcontainers strategy, or CI architecture that constitutes a significant architectural decision, record it as an ADR then.
