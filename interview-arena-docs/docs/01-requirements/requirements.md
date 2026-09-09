# Requirements

## Functional Requirements

### FR-01 — User Entry

Allow a user to enter as a guest or registered user.

### FR-02 — Profile

Registered users can maintain a basic profile. A detailed candidate profile is not required for the MVP.

### FR-03 — Interview Room Selection

User selects:

- DSA
- System Design
- OOP / LLD

### FR-04 — Join Queue

User joins the matchmaking queue for the selected room.

### FR-05 — Matchmaking

Match two eligible users randomly. Users cannot intentionally select an opponent.

### FR-06 — Interview Session

Create a session containing:

- participants
- room
- rounds
- roles
- timestamps
- state

### FR-07 — Real-Time Communication

Support real-time session events. Text communication can be implemented before voice/video.

### FR-08 — Role Switching

Swap interviewer/interviewee roles between the two rounds.

### FR-09 — Timer

Use a server-authoritative timer.

Initial duration:

- Round 1: 15 minutes
- Round 2: 15 minutes

### FR-10 — Per-Round Feedback

After each round, both participants submit feedback for the other participant.

The first submitter waits for the second within a bounded timeout.

Feedback results remain hidden until the entire two-round session is complete.

### FR-11 — Rating

Registered users accumulate separate:

- Candidate rating
- Interviewer rating

### FR-12 — History

Registered users can view completed interviews and feedback.

### FR-13 — Guest Dashboard

Guests can see current-visit session results/feedback in a temporary dashboard.

### FR-14 — Early Exit

Users can leave early. The session records abandonment/disconnection appropriately.

## Non-Functional Requirements

### NFR-01 — Consistency

A user must not be matched into two simultaneous sessions.

### NFR-02 — Real-Time Latency

Live session events and matchmaking should feel near-instant.

### NFR-03 — Initial Scale

Design and test for approximately 100 concurrent users first.

### NFR-04 — Security

Include authentication, authorization, input validation, rate limiting, secure WebSockets, and basic abuse prevention.

### NFR-05 — Observability

Support structured logs, metrics, health checks, and error tracking.

### NFR-06 — Evolvability

Keep module boundaries clean enough to add AI, assessments, resources, and mentorship later without rewriting the interview core.
