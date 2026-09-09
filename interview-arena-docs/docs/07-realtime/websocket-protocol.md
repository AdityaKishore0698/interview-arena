# WebSocket Protocol

## Endpoint

`wss://<host>/ws/v1/interview`

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

## Command rules

The server validates every command against authenticated identity, session membership, and current domain state.

Clients cannot directly emit lifecycle events such as `ROUND_ENDED` or `SESSION_COMPLETED`.

## Event categories

### Matchmaking
`MATCHMAKING_WAITING`, `MATCH_FOUND`, `MATCHMAKING_CANCELLED`

### Session
`SESSION_CREATED`, `SESSION_READY`, `SESSION_STARTED`, `SESSION_STATE_CHANGED`, `SESSION_COMPLETED`, `SESSION_ABANDONED`

### Round
`ROUND_STARTED`, `ROUND_TIME_WARNING`, `ROUND_ENDED`, `FEEDBACK_STARTED`, `FEEDBACK_COMPLETED`, `ROLE_SWAP_STARTED`

### Presence
`OPPONENT_CONNECTED`, `OPPONENT_DISCONNECTED`, `OPPONENT_RECONNECTED`

## Ordering

Events include `sequence`. Duplicate events can be ignored using `eventId`. A sequence gap triggers state resynchronization.

## Reconnect

A reconnecting client authenticates again and receives an authoritative session snapshot before continuing with new events.
