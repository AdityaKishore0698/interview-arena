# Test Matrix

| Requirement | Unit | Integration | API/Security | WebSocket | Concurrency | E2E |
|---|---:|---:|---:|---:|---:|---:|
| Session state transitions | ✓ | | | | | |
| Invalid state transitions | ✓ | | ✓ | ✓ | | |
| Guest/registered isolation | | ✓ | ✓ | | ✓ | ✓ |
| No intentional opponent selection | ✓ | | ✓ | | | ✓ |
| Duplicate queue prevention | ✓ | ✓ | ✓ | | ✓ | |
| Match creation correctness | ✓ | ✓ | | ✓ | ✓ | ✓ |
| Feedback validation | ✓ | ✓ | ✓ | | ✓ | ✓ |
| Duplicate feedback prevention | | ✓ | ✓ | | ✓ | |
| Rating integrity | ✓ | ✓ | ✓ | | | ✓ |
| Object-level authorization | | | ✓ | ✓ | | ✓ |
| Authentication | | | ✓ | ✓ | | ✓ |
| WebSocket lifecycle | | | | ✓ | | ✓ |
| Reconnection | | ✓ | | ✓ | ✓ | ✓ |
| Presence | | ✓ | | ✓ | ✓ | |
| Timer expiry | ✓ | | | ✓ | | ✓ |
| PostgreSQL constraints | | ✓ | | | ✓ | |
| Redis queue/TTL | | ✓ | | ✓ | ✓ | |
| API/OpenAPI contract | | | ✓ | | | |
| Rate limiting | | ✓ | ✓ | ✓ | | |
| Input validation | ✓ | | ✓ | ✓ | | |
| Critical user journeys | | | | | | ✓ |

## Priority

### P0 — Must be reliable
- authentication
- authorization
- session state machine
- matchmaking
- feedback integrity
- duplicate prevention
- WebSocket lifecycle
- reconnection
- concurrency-sensitive operations

### P1 — Important
- rating calculations
- guest expiration
- presence
- API contract
- rate limiting

### P2 — Later
- advanced anti-fraud detection
- large-scale load testing
- sophisticated chaos testing
