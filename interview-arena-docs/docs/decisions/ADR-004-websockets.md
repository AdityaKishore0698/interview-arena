# ADR-004 — Use WebSockets for Live Interview Events

**Status:** Accepted

## Context

The live interview experience requires bidirectional real-time events such as match notifications, role switches, disconnects, and session state updates.

## Decision

Use WebSockets for live session communication and HTTP/REST for normal request/response operations.

## Consequences

- low-latency bidirectional events
- persistent connections during active sessions
- additional connection lifecycle/reconnect complexity
- multi-instance deployments require shared connection/event coordination
