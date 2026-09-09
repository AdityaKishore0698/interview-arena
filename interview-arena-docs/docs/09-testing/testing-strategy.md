# Testing Strategy

**Phase:** 0.13  
**Status:** Proposed

## 1. Purpose

This document defines how Interview Arena will verify correctness, security, reliability, and real-time behavior.

Testing is part of the engineering design rather than a final verification step.

The strategy prioritizes:
- interview session state transitions
- matchmaking
- feedback and ratings
- authorization
- guest lifecycle
- WebSocket behavior
- timers
- reconnection
- concurrency and race conditions

## 2. Testing Pyramid

```text
                 ┌───────────────┐
                 │   E2E Tests   │
                 │      Few      │
                 └───────┬───────┘
                         │
                ┌────────┴────────┐
                │ Integration/API │
                │     Tests       │
                └────────┬────────┘
                         │
             ┌───────────┴───────────┐
             │      Unit Tests        │
             │        Many            │
             └────────────────────────┘
```

Interview Arena additionally requires first-class WebSocket and concurrency testing.

## 3. Test Levels

### Unit
Test isolated domain behavior without PostgreSQL, Redis, or a browser.

High priority:
- session state machine
- round transitions
- matchmaking rules
- feedback validation
- rating calculations
- guest lifecycle
- authorization policies
- timer calculations

### Integration
Test collaboration with real infrastructure:
- PostgreSQL repositories
- transactions
- constraints
- Redis queues
- Redis TTL
- Redis Pub/Sub

### API
Test:
- status codes
- validation
- authentication
- authorization
- response schemas
- conflicts
- idempotency
- error contracts

### WebSocket
Test:
- authentication
- connection lifecycle
- command authorization
- event delivery and ordering
- disconnect/reconnect
- presence
- session restoration

### Concurrency
Test:
- duplicate matchmaking
- duplicate feedback
- leave vs timeout
- reconnect vs disconnect
- multiple workers consuming the same queue entry

### E2E
Focus on critical user journeys rather than every UI interaction.

## 4. State-Machine Testing

The interview session state machine should have an explicit transition matrix.

| Current State | Action | Expected |
|---|---|---|
| WAITING | Match | MATCHED |
| MATCHED | Ready | READY |
| READY | Start | ROUND_ACTIVE |
| ROUND_ACTIVE | Timer expires | FEEDBACK |
| FEEDBACK | Both submit | ROLE_SWAP / NEXT_ROUND |
| ROUND_ACTIVE | Participant leaves | SESSION_TERMINATED |
| COMPLETED | Submit feedback | Reject |
| TERMINATED | Start round | Reject |

Both legal and illegal transitions must be tested.

## 5. Matchmaking Tests

Test:
- guest-to-guest matching
- no guest-to-registered matching
- no client-selected opponent
- duplicate queue prevention
- queue cleanup
- concurrent workers producing exactly one match

## 6. Feedback and Rating Tests

A feedback submission must verify:
1. authenticated participant
2. session membership
3. round membership
4. feedback eligibility
5. correct recipient
6. valid round state
7. no previous submission
8. valid scores
9. exactly-once persistence

Reject:
- self-rating
- non-participant rating
- duplicate submission
- expired-round submission
- forged recipient
- forged session
- invalid score

## 7. Authentication and Authorization Tests

```text
No credentials → 401
Invalid credentials → 401
Valid credentials → allowed
Authenticated but unauthorized → 403
```

Explicitly test object-level authorization:

```text
User A
  ↓
access User B's session
  ↓
403
```

## 8. Guest Tests

Verify:
- unique temporary identity
- guest authentication
- guest-to-guest matchmaking
- guest/registered isolation
- temporary dashboard
- temporary feedback visibility
- expiration/cleanup
- no persistent rating effect

## 9. WebSocket Tests

Test:

```text
CONNECT
   ↓
AUTHENTICATE
   ↓
AUTHORIZE
   ↓
JOIN SESSION
   ↓
RECEIVE EVENTS
   ↓
DISCONNECT
   ↓
RECONNECT
   ↓
RESTORE SESSION
```

Also test invalid authentication, unauthorized sessions, malformed commands, stale connections, duplicate commands, and reconnect after termination.

## 10. Timer Tests

Use a clock abstraction:

```text
Clock
├── RealClock
└── FakeClock
```

Production uses `RealClock`. Tests use `FakeClock`, allowing a 30-minute round to be tested without waiting 30 minutes.

## 11. Concurrency Tests

### Duplicate feedback

```text
Request A ──┐
            ├── same participant / round
Request B ──┘
```

Exactly one should succeed.

### Duplicate matchmaking

```text
Worker A ──┐
           ├── same queue participants
Worker B ──┘
```

Exactly one match should be created.

### Leave vs timeout

The final state must always satisfy the session state machine.

## 12. Database and Redis Tests

Use real PostgreSQL for constraints, transactions, isolation, and concurrent behavior where relevant.

Use real Redis for queues, TTL, presence, Pub/Sub, and ephemeral state.

Mocks remain useful for isolated unit tests but must not replace infrastructure integration tests where infrastructure semantics affect correctness.

## 13. API Contract Testing

OpenAPI is the API contract. Tests should detect mismatches between documented and implemented status codes, schemas, parameters, and errors.

## 14. Security Testing

Turn Phase 0.12 requirements into automated tests:
- protected endpoint without credentials → 401
- unauthorized resource → 403
- forged role rejected
- forged feedback recipient rejected
- duplicate feedback rejected
- client cannot select opponent
- malformed input rejected
- excessive requests rate limited
- internal errors do not leak infrastructure details

## 15. Critical E2E Journeys

### Registered user
Register → Login → Select room → Matchmaking → Interview → Feedback → Role swap → Second round → Complete.

### Guest
Guest entry → Temporary dashboard → Guest matchmaking → Interview → Feedback → Temporary results → Leave/expire.

### Reconnection
Match → Disconnect → Reconnect → Restore session → Continue.

## 16. Test Data and Isolation

Use deterministic factories such as:

```text
createUser()
createGuest()
createSession()
createRound()
createFeedback()
```

Tests must not depend on manually prepared databases, previous tests, production data, or execution order.

## 17. Environments

```text
Local → CI → Staging → Production
```

Local emphasizes fast feedback. CI runs the automated suite. Staging validates realistic deployment behavior. Production relies on monitoring and safe verification.

## 18. CI Pipeline

Target:

```text
Pull Request
     ↓
Lint / Static Checks
     ↓
Compile / Type Checks
     ↓
Unit Tests
     ↓
Integration Tests
     ↓
API Tests
     ↓
Security Checks
     ↓
Build
     ↓
E2E Tests
```

## 19. Coverage Philosophy

Do not optimize for 100% line coverage.

Prioritize business-risk coverage:
1. session transitions
2. matchmaking
3. authorization
4. feedback
5. rating rules
6. guest isolation
7. reconnection
8. timers
9. concurrency
10. security boundaries

## 20. Definition of Done

A significant backend feature requires:

```text
Implementation
    +
Unit tests
    +
Integration tests where required
    +
Authorization tests
    +
Failure cases
    +
Concurrency tests where applicable
    +
API contract
    +
Observability
```

Critical user workflows additionally require backend, WebSocket, and E2E coverage.

## 21. Acceptance Criteria

Phase 0.13 is complete when:
- test levels are defined
- state transitions have a test strategy
- matchmaking has concurrency tests
- feedback has integrity tests
- guest isolation has tests
- authorization has explicit tests
- WebSocket lifecycle has tests
- timers can be tested without real waiting
- PostgreSQL and Redis integration testing is defined
- API contract testing is defined
- critical E2E journeys are identified
- CI stages are defined
- coverage is risk-based
