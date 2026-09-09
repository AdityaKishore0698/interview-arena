# Presence and Reconnection

## Principle

WebSocket connection state is not the same as interview state.

```text
CONNECTED / DISCONNECTED / RECONNECTING
```

is connection-level state.

```text
ACTIVE / LEFT / TIMED_OUT
```

is domain/session state.

## Reconnection

1. Detect connection loss.
2. Mark participant disconnected.
3. Keep the session active during a configurable grace period.
4. Notify the opponent.
5. Accept reconnect.
6. Re-authenticate.
7. Validate session membership.
8. Send authoritative session snapshot.
9. Resume event delivery.
10. Apply abandonment policy if the grace period expires.

The interview timer continues during disconnection unless a future product decision explicitly changes this.

## Duplicate Connections

Phase 0 implementation should choose one policy. Recommended initial policy: one active connection per participant per session; a newer valid connection supersedes the older connection.

## Heartbeats

Use ping/pong or equivalent heartbeat handling. Missed heartbeats indicate possible connection loss; they do not by themselves mean the participant intentionally left.
