# Product Overview

## Vision

Interview Arena is a peer-powered placement preparation platform where candidates practice interviews with other candidates.

The core principle is:

> Every candidate can be both an interviewee and an interviewer.

## Initial Core Loop

```text
Choose Interview Room
        ↓
Join Queue
        ↓
Random Match
        ↓
Round 1
        ↓
Per-round Feedback
        ↓
Role Swap
        ↓
Round 2
        ↓
Per-round Feedback
        ↓
Session Complete
        ↓
Results
```

## Initial Interview Rooms

- DSA
- System Design
- OOP / LLD

There is no user-facing difficulty selection in the initial flow.

## Identity Modes

### Guest

- Temporary identity
- Guest ↔ Guest matchmaking only
- Temporary dashboard during the current visit
- Temporary feedback/results
- No persistent reputation or history
- Temporary data is erased when the guest leaves/expires

### Registered User

- Persistent identity
- Registered ↔ Registered matchmaking only
- Persistent history
- Candidate rating
- Interviewer rating
- Reputation

## Long-Term Product Direction

The platform can later add:

- AI Interview Copilot
- Interview intelligence and personalized feedback
- Online assessments
- Coding challenges
- Placement preparation resources
- Mentorship marketplace
- Paid mentorship and mentor earnings
- Personalized preparation plans
- Recommendation/intelligence systems

These future modules should remain isolated from the initial interview core.
