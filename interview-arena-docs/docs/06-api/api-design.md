# API Design

**Phase:** 0.10  
**Status:** Proposed

## Purpose
Define the contract between Interview Arena clients and the backend: REST, WebSocket, authentication, validation, errors, idempotency, concurrency, rate limits, and versioning.

## REST vs WebSocket
REST handles authentication, room discovery, session queries, feedback submission, and persistent results.

WebSocket handles matchmaking status, match-found events, interview state, timers, round transitions, opponent presence, and reconnect events.

## Versioning
Initial public API: `/api/v1/...`. Breaking changes require a new version.

## Identity
- **REGISTERED:** persistent profile, rating, history.
- **GUEST:** temporary identity and dashboard state.

The backend derives identity from the authenticated token.

## Core REST APIs
- `POST /api/v1/auth/guest`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/rooms`
- `POST /api/v1/matchmaking/queues`
- `DELETE /api/v1/matchmaking/queues/{roomId}`
- `GET /api/v1/matchmaking/status`
- `GET /api/v1/interview-sessions/{sessionId}`
- `POST /api/v1/interview-sessions/{sessionId}/leave`
- `POST /api/v1/interview-sessions/{sessionId}/rounds/{roundId}/feedback`
- `GET /api/v1/interview-sessions/{sessionId}/result`

## Matchmaking Contract
Joining a queue requires only a room ID:

```json
{"roomId":"dsa"}
```

The server determines the pool:

```text
GUEST → Guest pool
REGISTERED → Registered pool
```

Clients cannot choose opponents.

## Feedback Contract
```json
{
  "scores": {
    "communication": 4,
    "technicalKnowledge": 5,
    "problemSolving": 4
  },
  "comments": "Good structured reasoning."
}
```

The backend derives giver, receiver, role, round, and session from authenticated identity and membership. Feedback is submitted per round.

## WebSocket
Initial endpoint:

```text
wss://<host>/ws/v1/interview
```

Message envelope:

```json
{
  "type":"EVENT",
  "event":"ROUND_STARTED",
  "eventId":"uuid",
  "timestamp":"2026-08-19T12:00:00Z",
  "payload":{}
}
```

Important events:

```text
MATCHMAKING_WAITING
MATCH_FOUND
SESSION_CREATED
SESSION_STARTED
ROUND_STARTED
ROUND_TIME_WARNING
ROUND_ENDED
FEEDBACK_STARTED
FEEDBACK_COMPLETED
ROLE_SWAP_STARTED
SESSION_COMPLETED
SESSION_ABANDONED
OPPONENT_CONNECTED
OPPONENT_DISCONNECTED
OPPONENT_RECONNECTED
```

The server owns lifecycle state.

## Server-Authoritative Timer
The server sends `startedAt` and `endsAt`. The browser renders the countdown; only the backend decides whether the round has expired.

## Errors
Standard shape:

```json
{
  "error": {
    "code": "INVALID_SESSION_STATE",
    "message": "The session cannot accept feedback in its current state.",
    "requestId": "uuid"
  }
}
```

Use stable machine-readable codes such as:

`UNAUTHENTICATED`, `FORBIDDEN`, `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `CONFLICT`, `INVALID_SESSION_STATE`, `ALREADY_SUBMITTED`, `QUEUE_NOT_ACTIVE`, `SESSION_EXPIRED`, `RATE_LIMITED`, `INTERNAL_ERROR`.

HTTP conventions:

| Situation | Status |
|---|---:|
| Success | 200 |
| Created | 201 |
| Success/no body | 204 |
| Invalid request | 400 |
| Unauthenticated | 401 |
| Forbidden | 403 |
| Not found | 404 |
| Business/state conflict | 409 |
| Rate limited | 429 |
| Unexpected failure | 500 |

## Idempotency and Concurrency
Retries must not create duplicate queue entries, sessions, or feedback.

Match reservation must be atomic. Feedback must allow both participants to submit concurrently while preventing duplicate submission from the same participant.

Use request/idempotency IDs where appropriate and enforce uniqueness in the persistence layer.

## Security and Anti-Exploitation
Prevent:
- intentional opponent selection
- forged giver/receiver IDs
- unauthorized session access
- arbitrary session-state mutation
- abusive request rates

There must never be an endpoint that accepts a chosen opponent such as `POST /match/{userId}`.

## Rate Limiting
Protect authentication, queue joins, feedback submission, and WebSocket connection attempts. Enforce limits server-side.

## OpenAPI
The formal REST contract lives in:

```text
docs/06-api/openapi.yaml
```

Markdown explains design decisions; OpenAPI provides the machine-readable contract.

## Design Rules
1. Server is authoritative for state.
2. Client identity comes from authentication.
3. Clients cannot choose opponents.
4. Clients cannot choose feedback giver/receiver.
5. WebSocket handles real-time events.
6. REST handles durable/query-oriented operations.
7. Mutations consider retries and idempotency.
8. Business conflicts use `409`.
9. Error codes are stable machine-readable values.
10. Infrastructure details never leak through API responses.

## Phase 0.10 Deliverables
- REST endpoint catalogue
- request/response contracts
- WebSocket protocol
- authentication/authorization model
- error conventions
- idempotency and concurrency rules
- rate limiting
- OpenAPI specification

Next: **0.11 Real-Time Design**.
