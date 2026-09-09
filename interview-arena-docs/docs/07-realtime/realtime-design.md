# Real-Time Design

**Phase:** 0.11  
**Status:** Proposed

## 1. Purpose

Interview Arena is a real-time application. Two participants must observe a consistent interview session while their browsers, networks, WebSocket connections, and potentially backend instances operate independently.

The real-time subsystem therefore separates:

- persistent domain state
- ephemeral connection state
- real-time event delivery

The server is authoritative for interview state and time.

---

# 2. Core Mental Model

```text
Browser A ── WebSocket ──┐
                         ├── Realtime Gateway ── Application
Browser B ── WebSocket ──┘                         │
                                                   ├── PostgreSQL
                                                   └── Redis
```

A WebSocket connection is not the interview session.

```text
User Identity
     ≠
WebSocket Connection
     ≠
Interview Session
```

A connection can disappear while the session remains active.

---

# 3. Interview Session State Machine

Initial state model:

```text
WAITING
   │
   ▼
MATCHED
   │
   ▼
READY
   │
   ▼
ROUND_ACTIVE
   │
   ▼
FEEDBACK
   │
   ▼
ROLE_SWAP
   │
   └──────────────► ROUND_ACTIVE
                       │
                       ▼
                    FEEDBACK
                       │
                       ▼
                   COMPLETED
```

Failure path:

```text
ROUND_ACTIVE ── participant leaves/timeout ──► ABANDONED
FEEDBACK ────── participant leaves/timeout ──► ABANDONED
```

The domain state machine, not the WebSocket layer, owns these transitions.

## Legal transitions

| Current | Event | Next |
|---|---|---|
| WAITING | Match created | MATCHED |
| MATCHED | Both connected/ready | READY |
| READY | Server starts round | ROUND_ACTIVE |
| ROUND_ACTIVE | Timer expires | FEEDBACK |
| ROUND_ACTIVE | Participant leaves | ABANDONED |
| FEEDBACK | Both feedback complete | ROLE_SWAP |
| FEEDBACK | Feedback timeout | ABANDONED or policy-defined completion |
| ROLE_SWAP | Next round starts | ROUND_ACTIVE |
| FEEDBACK | Final round complete | COMPLETED |

The exact number of rounds is configuration, not hard-coded into the state machine.

---

# 4. WebSocket Lifecycle

```text
CONNECT
   ↓
AUTHENTICATE
   ↓
REGISTER CONNECTION
   ↓
SYNC CURRENT STATE
   ↓
SUBSCRIBE TO SESSION EVENTS
   ↓
NORMAL OPERATION
   ↓
HEARTBEATS
   ↓
DISCONNECT / RECONNECT
```

On reconnect, the client must not assume it knows the current state. It requests a state snapshot and then resumes from the server's authoritative state.

---

# 5. WebSocket Protocol

Endpoint:

```text
wss://<host>/ws/v1/interview
```

## Client command

```json
{
  "type": "COMMAND",
  "event": "SESSION_READY",
  "requestId": "req_123",
  "payload": {}
}
```

## Server event

```json
{
  "type": "EVENT",
  "event": "ROUND_STARTED",
  "eventId": "evt_123",
  "sequence": 42,
  "sessionId": "session_123",
  "roundId": "round_1",
  "timestamp": "2026-08-19T12:00:00Z",
  "payload": {}
}
```

## Rules

- `requestId` identifies a client command.
- `eventId` uniquely identifies a server event.
- `sequence` provides ordering within a session stream.
- `sessionId` scopes events to the interview.
- `roundId` scopes round-specific events.
- The server validates every command against current domain state.

---

# 6. Important Events

## Matchmaking

```text
MATCHMAKING_WAITING
MATCH_FOUND
MATCHMAKING_CANCELLED
```

## Session

```text
SESSION_CREATED
SESSION_READY
SESSION_STARTED
SESSION_STATE_CHANGED
SESSION_COMPLETED
SESSION_ABANDONED
```

## Round

```text
ROUND_STARTED
ROUND_TIME_WARNING
ROUND_ENDED
FEEDBACK_STARTED
FEEDBACK_COMPLETED
ROLE_SWAP_STARTED
```

## Presence

```text
OPPONENT_CONNECTED
OPPONENT_DISCONNECTED
OPPONENT_RECONNECTED
```

The server generates lifecycle events. Clients request operations rather than directly publishing lifecycle events.

---

# 7. Server-Authoritative Time

The server stores or derives the authoritative round deadline.

Example:

```json
{
  "event": "ROUND_STARTED",
  "payload": {
    "startedAt": "2026-08-19T12:00:00Z",
    "endsAt": "2026-08-19T12:30:00Z"
  }
}
```

The browser calculates a display countdown.

The backend decides whether:

```text
now >= endsAt
```

and therefore whether a round can accept a command.

Do not depend on the browser timer for correctness.

---

# 8. Presence

Presence is connection state, not domain state.

Suggested ephemeral states:

```text
CONNECTED
DISCONNECTED
RECONNECTING
```

The interview session separately tracks whether the participant is:

```text
ACTIVE
LEFT
TIMED_OUT
```

This distinction prevents a transient network failure from immediately destroying a session.

---

# 9. Heartbeats

The connection layer should detect dead connections.

Conceptually:

```text
Client ── ping ──► Server
Client ◄─ pong ─── Server
```

The exact heartbeat interval is an implementation/configuration decision.

A missed heartbeat does not automatically mean the participant intentionally left. It triggers connection-loss handling and the reconnect grace policy.

---

# 10. Reconnection Policy

Initial policy:

1. Connection drops.
2. Server marks the connection as disconnected.
3. Interview session remains active.
4. A configurable grace period begins.
5. The opponent sees a temporary disconnect state.
6. Participant reconnects and authenticates.
7. Server validates session membership.
8. Server sends the authoritative session snapshot.
9. Participant resumes from the current state.
10. If the grace period expires, the session follows the abandonment policy.

The timer continues while the participant is disconnected unless the product explicitly defines a pause policy.

The client does not get to extend the grace period.

---

# 11. State Synchronization After Reconnect

Do not attempt to reconstruct state solely from missed WebSocket messages.

On reconnect:

```text
CONNECT
  ↓
AUTHENTICATE
  ↓
GET CURRENT SESSION SNAPSHOT
  ↓
APPLY AUTHORITATIVE STATE
  ↓
RECEIVE NEW EVENTS
```

The snapshot contains enough information to render the current session:

```text
session state
current round
participant role
deadline
feedback status
opponent presence
```

---

# 12. Event Ordering

Network delivery does not guarantee that application-level events are processed exactly once or in the expected order.

Use:

```text
eventId
sequence
sessionId
```

A client can detect:

```text
sequence 41
sequence 42
sequence 42  ← duplicate
sequence 44  ← gap
```

The client should not invent the missing state.

For a gap, it should request a fresh authoritative snapshot.

---

# 13. Duplicate Events

Events can be duplicated because of retries, reconnects, or infrastructure behavior.

Consumers should treat event processing as idempotent where possible.

Example:

```text
eventId = evt_123
```

If `evt_123` has already been processed, applying it again should not create a second side effect.

---

# 14. Redis

Redis is considered an infrastructure component for ephemeral/distributed coordination.

Potential responsibilities:

```text
Redis
├── matchmaking queues
├── connection/presence metadata
├── Pub/Sub for cross-instance events
├── short-lived coordination data
└── distributed coordination where justified
```

Do not use Redis as the authoritative store for durable interview history.

PostgreSQL remains the source of truth for persistent domain data.

Redis data should have explicit TTL/lifecycle policies where appropriate.

---

# 15. Multiple Backend Instances

Example:

```text
                 Load Balancer
                /      |      \
               ↓       ↓       ↓
            Server 1 Server 2 Server 3
               \       |       /
                \      |      /
                   Redis
                     |
                PostgreSQL
```

A participant's WebSocket can terminate on any instance.

Example:

```text
User A → Server 1
User B → Server 3
```

An event generated by the session owner must reach both relevant connections.

A shared coordination mechanism such as Redis Pub/Sub can distribute events between instances.

---

# 16. Source of Truth

Use different systems for different responsibilities:

| Data | Source of truth |
|---|---|
| User/account | PostgreSQL |
| Persistent feedback | PostgreSQL |
| Persistent session history | PostgreSQL |
| Current domain session state | PostgreSQL/domain transaction |
| WebSocket connection | Realtime layer |
| Presence | Redis/realtime layer |
| Matchmaking queue | Redis/realtime layer |
| Cross-instance event distribution | Redis Pub/Sub |
| Browser countdown | Client display only |

This table is an architectural boundary, not an excuse to duplicate business state arbitrarily.

---

# 17. Race Conditions

### Two users match simultaneously

The reservation/match creation operation must prevent one participant from being assigned to two sessions.

### Both users submit feedback simultaneously

Both valid submissions must succeed, but a participant cannot submit twice for the same round.

### Disconnect during round completion

The server decides the resulting state using the domain state machine. WebSocket disconnection itself does not define business state.

### Reconnect during transition

The reconnecting client obtains the current snapshot rather than assuming which transition happened.

---

# 18. Failure Handling

## Browser disconnect

Keep session alive during grace period.

## Server instance crash

The connection is lost. The participant reconnects through the load balancer. Persistent session state remains recoverable.

## Redis unavailable

Real-time coordination may degrade or become unavailable depending on the operation. The system must fail safely rather than silently producing inconsistent matches.

## PostgreSQL unavailable

Durable domain mutations must not be acknowledged as successful without persistence.

## Duplicate connection

The system needs a defined policy, such as allowing one active connection per participant/session and invalidating the older connection, or explicitly supporting multiple devices. Phase 0 implementation should choose one policy.

---

# 19. Security

WebSocket authentication is mandatory.

Every command must be authorized against:

```text
authenticated user
+
session membership
+
current domain state
```

Never trust:

```text
userId
role
session state
timer
feedback receiver
```

supplied by the browser.

The server derives these values.

---

# 20. Observability

Every real-time operation should be traceable using identifiers such as:

```text
requestId
eventId
sessionId
roundId
userId / guestSessionId
```

Metrics to consider:

```text
active WebSocket connections
connection failures
reconnect rate
matchmaking wait time
session abandonment rate
event delivery latency
event processing failures
feedback timeout rate
```

Logs must avoid sensitive data.

---

# 21. Initial Architecture Decision

Interview Arena remains a **modular monolith** for Phase 0.

The realtime gateway may be deployed as part of the backend initially.

Do not create separate microservices for:

```text
Matchmaking Service
Interview Service
Feedback Service
Realtime Service
```

until actual scale or organizational boundaries justify them.

The architecture should preserve module boundaries so extraction remains possible later.

---

# 22. Phase 0.11 Engineering Principles

1. WebSocket is a transport, not the domain model.
2. The server owns session state.
3. The client is a projection of server state.
4. Persistent domain data belongs in PostgreSQL.
5. Ephemeral coordination belongs in appropriate infrastructure.
6. Reconnects must resynchronize from authoritative state.
7. Events need identity and ordering metadata.
8. Duplicate delivery must be safe.
9. Race conditions must be handled explicitly.
10. Scaling WebSocket connections across instances requires shared coordination.
11. Failure behavior must be defined, not assumed.
12. Do not introduce distributed infrastructure without a concrete requirement.

---

# 23. Phase 0.11 Deliverables

- Real-time architecture
- interview state machine
- WebSocket protocol
- presence model
- heartbeat policy
- reconnection policy
- event ordering/idempotency rules
- Redis responsibilities
- multi-instance architecture
- failure-handling strategy
- security model
- observability requirements

Next: **Phase 0.12 — Security Design**.
