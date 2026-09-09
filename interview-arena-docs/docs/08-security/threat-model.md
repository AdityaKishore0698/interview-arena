# Threat Model

## Scope

Initial threat model for Interview Arena Phase 0.

## Assets

- registered accounts
- guest identities
- authentication credentials
- interview sessions
- feedback
- ratings
- interview history
- database credentials
- Redis credentials
- infrastructure secrets

## Trust Boundaries

1. Browser → API
2. Browser → WebSocket
3. Backend → PostgreSQL
4. Backend → Redis
5. Deployment environment → secret store

## Threat Categories

### Identity attacks
- credential theft
- session hijacking
- fake guest identities

### Authorization attacks
- IDOR/BOLA
- role forgery
- cross-session access
- feedback forgery

### Integrity attacks
- rating manipulation
- duplicate feedback
- opponent selection
- session-state manipulation

### Availability attacks
- queue flooding
- login abuse
- WebSocket connection flooding
- feedback spam

### Injection attacks
- SQL injection
- XSS
- malformed payloads

## Initial Controls

| Threat | Control |
|---|---|
| Credential theft | TLS + secure credential handling |
| Session hijacking | secure tokens/cookies + expiration |
| IDOR/BOLA | object-level authorization |
| Role forgery | server-derived role |
| Rating manipulation | server-controlled matchmaking |
| Feedback forgery | derive participant/session/round |
| Duplicate feedback | unique constraint + state check |
| Queue flooding | rate limiting |
| SQL injection | parameterized queries |
| XSS | output encoding + CSP |
| WebSocket abuse | authentication + authorization |
| Secret leakage | secret management |

## Risk Approach

Start with deterministic controls and observability. Do not build sophisticated fraud detection until real usage produces evidence that it is necessary.
