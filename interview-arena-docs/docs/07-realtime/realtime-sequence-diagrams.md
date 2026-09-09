# Real-Time Sequence Diagrams

## 1. Normal Interview

```text
User A       Backend        Redis       User B
  |             |             |            |
  |-- connect ->|             |            |
  |             |<-- presence-|            |
  |             |             |<-- connect |
  |             |<-- presence-|------------|
  |             |                         |
  |<----------- MATCH_FOUND ------------->|
  |             |                         |
  |<--------- ROUND_STARTED ------------->|
  |             |                         |
  |<--------- ROUND_ENDED --------------->|
  |             |                         |
  |-- feedback->|<-------- feedback -------|
  |             |                         |
  |<-------- FEEDBACK_COMPLETED ---------->|
  |<--------- ROLE_SWAP ----------------->|
  |             |                         |
  |<--------- ROUND_STARTED ------------->|
  |             |                         |
  |<--------- SESSION_COMPLETED ---------->|
```

## 2. Reconnection

```text
User A       Server       Session Store       User B
  |             |               |               |
  |--- drop --->X               |               |
  |             |-- mark lost ->|               |
  |             |------------------------------>|
  |                                             |
  |--- reconnect ------------------------------>|
  |             |               |               |
  |<-- snapshot-|<--------------|               |
  |             |               |               |
  |<========= current state restored ==========>|
```

## 3. Cross-Instance Event

```text
User A → Server 1
User B → Server 3

Server 1
   |
   | publish event
   v
 Redis Pub/Sub
   |
   v
Server 3
   |
   v
User B
```

Redis distributes the event; the domain remains authoritative elsewhere.
