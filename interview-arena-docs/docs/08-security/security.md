# Security Design

**Phase:** 0.12  
**Status:** Proposed

## 1. Purpose

Interview Arena is a peer-to-peer interview platform. The client is untrusted, while the backend owns identity, authorization, matchmaking, interview state, feedback, ratings, and persistent data.

The security design protects:

- user and guest identities
- interview sessions
- matchmaking integrity
- feedback and ratings
- API and WebSocket endpoints
- persistent data
- infrastructure credentials
- availability

---

# 2. Security Principles

1. Never trust client-supplied identity or role.
2. Authenticate before accessing protected resources.
3. Authorize every sensitive operation.
4. Enforce business rules on the server.
5. Treat guests as untrusted temporary principals.
6. Use least privilege.
7. Store secrets outside source control.
8. Validate input at trust boundaries.
9. Fail closed for authorization and state transitions.
10. Keep security-relevant actions auditable.
11. Minimize stored personal data.
12. Prefer short-lived credentials and explicit expiration.

---

# 3. Trust Boundaries

```text
                 UNTRUSTED
┌─────────────────────────────────┐
│ Browser / Client                │
│                                 │
│ Can modify requests, JS, state  │
└───────────────┬─────────────────┘
                │ HTTPS / WSS
                ▼
┌─────────────────────────────────┐
│ Backend                         │
│ Authentication                 │
│ Authorization                  │
│ Validation                     │
│ Domain Rules                   │
│ Rate Limiting                  │
└──────────────┬───────┬──────────┘
               │       │
               ▼       ▼
        PostgreSQL    Redis
          trusted     trusted
          boundary   infrastructure
```

The frontend is never a security boundary.

---

# 4. Authentication

Authentication answers:

> Who is making this request?

## Registered users

Initial implementation can use:

```text
Email/username
     ↓
Password verification
     ↓
Authenticated session/token
```

Passwords must never be stored directly.

Use a password hashing algorithm designed for passwords, such as Argon2id or an equivalently appropriate modern password hashing scheme.

## Guests

A guest receives a temporary identity.

```text
POST /api/v1/auth/guest
        ↓
Temporary guest principal
        ↓
Short-lived authentication credential
        ↓
Guest dashboard/session state
```

Guest identity must be cryptographically difficult to guess.

Guest data expires when its server-side lifetime expires and should not become persistent merely because the browser sends a fabricated guest ID.

---

# 5. Session / Token Strategy

The implementation should use secure authentication credentials with:

- expiration
- secure transport
- revocation/rotation strategy where required
- server-side authorization checks

If cookies are used:

```text
Secure
HttpOnly
SameSite
```

must be configured appropriately.

If bearer tokens are used, avoid placing long-lived credentials in browser-accessible storage when a safer architecture is available.

Authentication design must be finalized during implementation based on the chosen backend framework and deployment environment.

---

# 6. Authorization

Authentication is not authorization.

Authorization answers:

> What is this authenticated principal allowed to do?

For a session operation:

```text
authenticated principal
        ↓
is participant in session?
        ↓
what role does participant currently have?
        ↓
is operation valid in current session state?
        ↓
allow / reject
```

Never accept these as authoritative from the client:

```text
userId
sessionParticipantId
role
feedbackReceiverId
ratingOwnerId
sessionState
```

The server derives them from authenticated identity and persistent/domain state.

---

# 7. Object-Level Authorization

Every resource containing a user/session identifier must be checked.

Bad:

```text
GET /api/v1/interview-sessions/{sessionId}
```

with only authentication.

Correct:

```text
authenticated user
        +
session membership
        +
resource authorization
```

A participant can access only sessions for which they have permission.

This prevents IDOR/BOLA-style vulnerabilities.

---

# 8. WebSocket Security

WebSocket connections use:

```text
wss://
```

rather than unencrypted `ws://` in production.

During connection:

```text
CONNECT
   ↓
AUTHENTICATE
   ↓
AUTHORIZE
   ↓
REGISTER CONNECTION
```

Every command is validated against:

- authenticated principal
- session membership
- current session state
- command permissions

A WebSocket connection is not trusted merely because it was previously authenticated.

---

# 9. Matchmaking Security

The client can request:

```json
{
  "roomId": "dsa"
}
```

The client cannot request:

```json
{
  "opponentId": "known-friend"
}
```

The backend determines matchmaking.

This prevents intentional pairing and reduces rating manipulation.

The matchmaking system must also prevent:

- duplicate queue entries
- queue flooding
- rapid join/leave abuse
- bypassing guest/registered pool separation
- assigning one participant to multiple active matches

---

# 10. Rating and Feedback Integrity

Feedback is a high-value abuse target.

The server determines:

```text
feedback giver
feedback receiver
session
round
role
```

The client only supplies allowed feedback fields.

A feedback submission must satisfy:

```text
authenticated participant
        ↓
participant belongs to session
        ↓
round belongs to session
        ↓
participant was eligible to give feedback
        ↓
feedback not already submitted
        ↓
round/session state allows submission
        ↓
persist
```

The server must reject attempts to:

- rate oneself
- rate a non-participant
- rate the same participant twice for one round
- submit feedback outside the round
- modify another participant's feedback
- submit feedback after expiration

---

# 11. Guest Security

Guest users are intentionally limited.

Guest data should be:

```text
temporary
non-persistent
scoped to guest session
automatically expired
```

Guest users match only with other guests.

Guest feedback does not modify persistent registered-user ratings.

This preserves the product requirement that guest participation remains temporary while preventing anonymous users from affecting the persistent rating ecosystem.

---

# 12. Rating Manipulation

The architecture already prevents the largest obvious exploit:

```text
User A ── intentionally ──► User B
          choose opponent
```

because clients cannot select opponents.

Additional protections should be considered after real usage data exists:

- detect repeated pairings
- cap rating influence from suspicious sessions
- reduce influence of very short/abandoned sessions
- detect unusual rating patterns
- record session history for registered users
- maintain separate interview-performance and interviewer-quality signals if useful

Do not build a complex anti-fraud ML system in Phase 0.

Start with deterministic rules and observability.

---

# 13. Input Validation

Validate at every API boundary.

Examples:

```text
roomId
feedback scores
comments
session IDs
round IDs
pagination parameters
```

Validation should include:

- type
- format
- length
- range
- allowed values
- state-dependent constraints

Reject malformed input before it reaches domain logic.

---

# 14. Injection Protection

Use parameterized queries or ORM mechanisms that safely bind values.

Never construct SQL using string concatenation from user input.

For rendered user content:

- escape output appropriately
- avoid injecting raw HTML
- apply a suitable Content Security Policy where applicable

The backend must assume user-generated feedback/comments can contain malicious content.

---

# 15. CSRF

If authentication uses cookies, evaluate CSRF protection for state-changing HTTP operations.

Controls may include:

- SameSite cookies
- CSRF tokens where necessary
- Origin/Referer validation where appropriate

If a pure bearer-token architecture is used, the CSRF threat model differs, but XSS and token theft remain important concerns.

Security decisions must follow the actual authentication architecture.

---

# 16. CORS

CORS must allow only explicitly required origins.

Do not deploy:

```text
Access-Control-Allow-Origin: *
```

together with credentialed cross-origin requests.

Production configuration should use an allowlist.

---

# 17. Rate Limiting

Rate limit operations likely to be abused:

```text
registration
login
guest creation
queue join
queue leave
feedback submission
WebSocket connections
```

Rate limits can use different dimensions:

```text
IP
account
guest identity
endpoint
connection
```

Avoid relying only on IP because multiple legitimate users can share an IP.

---

# 18. Secrets Management

Never commit:

```text
database passwords
JWT signing secrets
API keys
Redis credentials
cloud credentials
private keys
```

to Git.

Use environment-specific secret management.

Local development may use:

```text
.env
```

but `.env` containing secrets must be excluded from version control.

Production should use the deployment platform's secret-management mechanism.

---

# 19. Data Protection

Minimize stored personal information.

Potentially persistent:

```text
account identity
skill/profile information
interview history
feedback
rating
```

Guest data should expire.

Sensitive information should not appear in ordinary logs.

Use encryption in transit:

```text
HTTPS
WSS
```

Database/storage encryption should be enabled where provided by the deployment environment.

---

# 20. Session Security

Prevent:

- session fixation
- token replay where applicable
- token leakage
- unauthorized session reuse

Authentication credentials should have defined expiration.

Logout should invalidate or otherwise make the relevant credential unusable according to the chosen authentication architecture.

---

# 21. Replay Protection

For sensitive state-changing operations, use server-side state checks and idempotency.

Example:

```text
Feedback request
     ↓
Is this participant eligible?
     ↓
Has feedback already been submitted?
     ↓
Is this round still accepting feedback?
     ↓
Persist exactly once
```

A captured old request should not be able to mutate a later session state.

---

# 22. Error Handling

Do not expose internal details.

Bad:

```text
PostgreSQL unique constraint interview_feedback_pkey failed
```

Prefer:

```json
{
  "error": {
    "code": "ALREADY_SUBMITTED",
    "message": "Feedback has already been submitted.",
    "requestId": "req_123"
  }
}
```

Detailed infrastructure information belongs in internal logs, not client responses.

---

# 23. Logging and Auditability

Security-relevant actions should be traceable.

Examples:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
GUEST_CREATED
QUEUE_JOINED
MATCH_CREATED
SESSION_STARTED
FEEDBACK_SUBMITTED
SESSION_ABANDONED
AUTHORIZATION_DENIED
RATE_LIMIT_TRIGGERED
```

Each event should include appropriate correlation identifiers.

Do not log passwords, authentication tokens, or unnecessary personal information.

---

# 24. Threat Model

Initial threats:

| Threat | Primary control |
|---|---|
| Fake identity | Authentication |
| Session hijacking | Secure credentials + TLS |
| IDOR/BOLA | Object-level authorization |
| Rating manipulation | Server-controlled matchmaking/feedback |
| Feedback forgery | Derive giver/receiver from session |
| Duplicate feedback | Unique constraint + state check |
| Queue flooding | Rate limiting |
| SQL injection | Parameterized queries |
| XSS | Output encoding/CSP |
| CSRF | SameSite/CSRF controls where applicable |
| WebSocket abuse | Authentication + command authorization |
| Credential theft | Secure token/cookie handling |
| Secret leakage | Secret management |
| Replay | Expiration + state/idempotency |
| Information leakage | Safe errors/logging |

---

# 25. Security Boundaries by Component

```text
Frontend
   │
   │ untrusted
   ▼
API / WebSocket Gateway
   │
   ├── Authentication
   ├── Authorization
   ├── Validation
   ├── Rate Limiting
   │
   ▼
Application / Domain
   │
   ├── Session rules
   ├── Matchmaking rules
   ├── Feedback rules
   └── Rating rules
   │
   ├───────────────┐
   ▼               ▼
PostgreSQL        Redis
durable           ephemeral
```

Security checks at the gateway are useful, but domain-level authorization must still protect sensitive operations.

---

# 26. Security and the Modular Monolith

Security logic should not become one giant `SecurityService`.

Use clear responsibilities:

```text
Authentication
Authorization
Validation
Rate Limiting
Domain Policies
Audit Logging
```

Domain modules should enforce their own sensitive business invariants.

For example, the feedback module owns the rule:

> A participant can submit feedback only once for an eligible round.

The authentication module should not contain that rule.

---

# 27. Security Non-Goals for Phase 0

Do not initially build:

- advanced fraud ML
- biometric identity verification
- enterprise SSO
- complex bot-detection infrastructure
- zero-trust service mesh
- custom cryptographic algorithms
- microservice-level security architecture

The goal is strong foundational application security, not unnecessary complexity.

---

# 28. Security Acceptance Criteria

Before implementation is considered secure enough for the initial release:

- unauthenticated users cannot access protected registered-user resources
- users cannot access another user's sessions
- clients cannot choose opponents
- clients cannot forge participant roles
- clients cannot forge feedback giver/receiver
- duplicate feedback is rejected
- expired sessions reject state-changing commands
- WebSocket commands are authenticated and authorized
- rate limits exist for abuse-prone endpoints
- secrets are absent from source control
- production traffic uses HTTPS/WSS
- malformed input is rejected
- errors do not expose infrastructure details
- security-relevant events are observable

---

# 29. Security Design Principles

The most important rule:

> The frontend is a convenience layer, not a trust boundary.

The backend must independently determine:

```text
identity
authorization
role
session
round
state
timer validity
feedback eligibility
rating eligibility
```

This principle should guide the implementation of every API and WebSocket command.

---

# 30. Phase 0.12 Deliverables

- security architecture
- authentication model
- authorization model
- guest security
- WebSocket security
- matchmaking integrity
- feedback/rating integrity
- input validation
- injection protection
- CORS/CSRF considerations
- rate limiting
- secret management
- data protection
- threat model
- security acceptance criteria

Next: **Phase 0.13 — Testing Strategy**.
