# Interview Arena — AI Engineering Instructions

## 0. Mandatory Agent Instructions

This file is mandatory project-level guidance.

Before performing any implementation, modification, refactoring, documentation change, dependency installation, database migration, or Git operation, read and follow this file.

The root `AGENTS.md` applies to the entire repository unless a more specific nested `AGENTS.md` explicitly overrides it for its directory.

The canonical Markdown SDDs under `interview-arena-docs/docs/` are the source of truth for the system architecture and design. `AGENTS.md` defines the engineering workflow used to implement that design.

## 1. Project Purpose

Interview Arena is a peer-powered placement preparation platform.

The platform allows candidates to practice interviews with other candidates through real-time, structured interview sessions. The system will progressively support matchmaking, interview rounds, feedback, ratings, online assessments, mentorship, and other placement-preparation capabilities.

The goal is to build this as a realistic production-grade software project rather than a prototype.

AI-assisted development is allowed and encouraged, but generated code must follow the project's architecture, design documents, engineering standards, and tests.

---

## 2. Source of Truth

The canonical engineering specification is the Markdown documentation under:

`interview-arena-docs/docs/`

The documentation is maintained as Documentation as Code.

Before implementing a feature:

1. Inspect the relevant SDD documents.
2. Inspect relevant ADRs.
3. Inspect the existing implementation.
4. Identify affected modules, APIs, database structures, and tests.
5. Implement only after understanding the existing design.

Do not silently contradict the SDD.

If implementation reveals that the current design is insufficient or incorrect:

1. Stop and identify the discrepancy.
2. Explain the architectural implication.
3. Update the relevant SDD and/or create an ADR when appropriate.
4. Then implement the change.

Do not treat generated DOCX or PDF learning material as the source of truth.

---

## 3. Current Architecture

The application follows a Modular Monolith architecture.

Do not introduce microservices unless explicitly requested.

The system currently separates responsibilities into modules such as:

- Identity
- Interview
- Matchmaking
- Feedback
- Realtime
- Shared infrastructure

Modules should have clear boundaries and should not directly depend on another module's internal implementation.

Prefer:

`Router → Service → Repository/Infrastructure → Database`

where appropriate.

Business rules belong in the domain/service layer rather than HTTP routes.

---

## 4. Approved Technology Stack

### Backend

Python

FastAPI

Pydantic

SQLAlchemy 2.x

Alembic

PostgreSQL

Redis

Celery when asynchronous/background task processing is required

Kafka only when the architecture genuinely requires durable event streaming; do not introduce Kafka merely because it is available in the preferred stack.

Pytest

Ruff

Mypy

REST / OpenAPI

JWT / OAuth2

### Frontend

TypeScript

React

Next.js

Tailwind CSS

shadcn/ui

TanStack Query

### Infrastructure

Docker

Docker Compose

GitHub Actions

Linux

Git

Nginx where appropriate

AWS may be used in future production deployments, but local development and the current project should prioritize free/low-cost infrastructure.

Do not introduce another major framework or database without explicit justification.

---

## 5. Engineering Principles

Follow SOLID principles where applicable.

Prefer composition over unnecessary inheritance.

Use clear domain models and explicit business rules.

Avoid premature abstractions.

Do not create abstractions simply to demonstrate a design pattern.

Use design patterns when they solve a real problem.

Prefer simple, maintainable code over clever code.

Use strong typing.

Avoid `Any` unless there is a documented reason.

Keep functions and classes focused.

Avoid God classes and God modules.

Keep API, domain, persistence, and infrastructure responsibilities separated.

---

## 6. Database Rules

PostgreSQL is the persistent source of truth for durable domain state.

Use SQLAlchemy 2.x for database access.

Use Alembic for schema migrations.

Never modify the production schema manually without creating the corresponding Alembic migration.

Every schema change must have an appropriate migration.

Database constraints should enforce important invariants whenever practical.

Do not rely exclusively on application-level validation for data integrity.

Use transactions for domain operations that require atomicity.

Use row-level locking where required by the documented concurrency model.

Avoid N+1 database queries.

Do not store derived data in the database unless there is a clear reason.

---

## 7. Redis Rules

Redis is used for ephemeral and coordination-related state.

Examples include:

- Matchmaking queues
- Presence
- WebSocket coordination
- Temporary guest sessions
- Distributed locks
- Pub/Sub
- Short-lived state

Do not treat Redis as the authoritative source for durable domain data unless the SDD explicitly specifies it.

Every Redis key should have:

- A clear naming convention
- A documented purpose
- An appropriate TTL where applicable

Avoid creating permanent Redis state accidentally.

---

## 8. API Rules

All public APIs should be versioned under:

`/api/v1/`

Use REST conventions consistently.

Use Pydantic request and response schemas.

Do not expose SQLAlchemy models directly through API responses.

Validate authorization at the service/domain boundary, not only at the router.

Return appropriate HTTP status codes.

Maintain OpenAPI documentation.

Breaking API changes require explicit consideration and documentation.

---

## 9. Realtime Rules

WebSockets are server-authoritative.

Clients must not directly mutate domain state through arbitrary WebSocket messages.

WebSockets primarily deliver real-time events and synchronization information.

REST endpoints are used for commands and authoritative recovery/snapshot operations unless the SDD explicitly specifies otherwise.

The server owns authoritative timestamps and state transitions.

The client should render server state rather than independently deciding authoritative state.

Reconnect flows must retrieve an authoritative session snapshot.

Realtime state transitions must be idempotent.

---

## 10. Matchmaking Rules

Matchmaking is intentionally separated from the persistent interview session lifecycle.

Guest users must only be matched with guest users.

Registered users must only be matched with registered users.

Matching must respect the configured room and interview mode.

The system must prevent immediate repeated matches where specified by the SDD.

Do not expose queue depth or other potentially exploitable matchmaking information unless explicitly required.

Matchmaking must remain safe under concurrent requests.

Redis reservation and PostgreSQL session creation must follow the idempotency strategy documented in ADR-005.

Do not replace the existing reservation mechanism without updating the relevant ADR and SDD.

---

## 11. Interview Session Rules

Interview sessions are persistent domain entities.

Session state transitions must follow the documented state machine.

Do not introduce arbitrary state transitions.

Round roles must follow the documented role assignment rules.

Round 1 and Round 2 must enforce role reversal where required.

Interrupted rounds must not be incorrectly marked as successfully completed.

Feedback is submitted per round.

Feedback timeout behavior must follow the documented design.

Early departure and disconnect behavior must follow the documented grace-period rules.

Concurrent transitions must be protected against duplicate execution.

---

## 12. Guest User Rules

Guest sessions are intentionally ephemeral.

Guest state must not accidentally become persistent user data.

Guest sessions should have explicit TTLs.

When a guest leaves the system and the guest data expires, the system should not retain unnecessary personal/session information.

Guest and registered-user flows must remain explicitly separated where required by the architecture.

---

## 13. Security Rules

Never commit secrets.

Never commit:

- `.env`
- `.env.local`
- API keys
- passwords
- JWT secrets
- private certificates
- cloud credentials

Use environment variables for secrets and environment-specific configuration.

Authentication and authorization must be enforced server-side.

Never trust client-provided user identity.

Never trust client-provided role or session state.

Validate JWTs server-side.

Do not log passwords, tokens, secrets, or sensitive authentication data.

---

## 14. Testing Requirements

Every meaningful backend feature should include tests.

Prefer the testing pyramid:

Unit tests
→ Service/domain tests
→ Integration tests
→ API tests
→ End-to-end tests where appropriate

Test important failure paths, not only the happy path.

For concurrent systems, explicitly test race conditions where practical.

For matchmaking and realtime functionality, test:

- Duplicate requests
- Concurrent requests
- Disconnects
- Reconnects
- Timeouts
- Database failures
- Redis failures
- Idempotent retries
- Unauthorized access
- Invalid state transitions

Tests must not be removed merely because they expose an implementation problem.

Fix the implementation or explicitly revise the design.

---

## 15. Code Quality

Before considering backend work complete, run:

`uv run pytest`

`uv run ruff check .`

`uv run mypy .`

For frontend work, run the appropriate:

`npm run lint`

`npm run build`

and relevant tests.

Do not claim a feature is complete if the relevant validation has not been executed.

If a check cannot be executed because of an environmental limitation, explicitly report that limitation.

---

## 16. Documentation Requirements

Documentation must evolve with the implementation.

When an implementation changes architecture, update the relevant Markdown SDD.

When an architectural decision introduces a meaningful tradeoff, create or update an ADR.

Examples include:

- Database technology
- Caching strategy
- Messaging strategy
- Matchmaking algorithm
- Concurrency strategy
- Authentication architecture
- Deployment architecture
- Major framework decisions

Do not update documentation merely to make it appear complete.

Documentation must describe the actual system.

---

## 17. Git Workflow

Git is part of the engineering workflow.

Before starting meaningful work:

`git status`

Inspect the current branch and working tree.

Do not overwrite unrelated uncommitted work.

After implementation:

`git status`

`git diff`

Review the actual changes before staging.

Stage only files belonging to the current task.

Do not blindly run:

`git add .`

when unrelated files may exist.

Create focused commits representing coherent units of work.

Use Conventional Commit style.

Examples:

`feat(matchmaking): implement queue reservation`

`feat(realtime): add session websocket synchronization`

`fix(matchmaking): recover expired reservations`

`test(interview): add session transition coverage`

`docs(realtime): document websocket protocol`

`refactor(identity): separate authentication service`

Avoid vague messages such as:

`update`

`changes`

`fix`

`final`

`phase 2`

Do not create one enormous commit containing unrelated work.

Do not rewrite Git history.

Do not force-push.

Do not amend an existing commit unless explicitly requested.

---

## 18. AI-Assisted Development Rules

AI may be used extensively during development.

However, AI-generated code must be treated as proposed code, not automatically correct code.

Before implementing a feature, understand:

- Why the feature exists
- Which requirement it satisfies
- Which domain objects it affects
- Which APIs it affects
- Which database structures it affects
- Which concurrency concerns exist
- Which tests are required

Do not generate large amounts of speculative code.

Prefer incremental implementation.

After each meaningful implementation step:

1. Inspect the code.
2. Run tests.
3. Run static analysis.
4. Review the diff.
5. Correct issues.
6. Continue.

Do not introduce technologies simply because an AI tool recommends them.

The SDD and explicit project decisions take precedence over generic AI recommendations.

---

## 19. Antigravity Operating Procedure

When asked to implement a feature, follow this sequence:

First inspect the repository structure.

Then inspect `AGENTS.md`.

Then inspect the relevant SDD documents and ADRs.

Then inspect the existing implementation.

Then identify the smallest coherent implementation plan.

Before modifying architecture, explain the proposed architectural change.

Implement incrementally.

Write tests.

Run validation.

Review the Git diff.

Update documentation when required.

Stage only relevant files.

Create a focused Git commit.

Report:

- What was implemented
- Files changed
- Tests executed
- Static checks executed
- Documentation changed
- Git commit created
- Any remaining limitations

Do not proceed with major architectural changes merely because they appear convenient.

---

## 20. Git Commit Responsibility

Antigravity is allowed to create Git commits for completed implementation units.

Before committing, it MUST:

1. Check `git status`.
2. Review `git diff`.
3. Ensure no secrets or unrelated files are included.
4. Ensure tests and required checks have passed.
5. Stage only relevant files.
6. Create a meaningful Conventional Commit message.
7. Verify the commit with `git status` and `git log -1`.

The agent must report the resulting commit hash.

If tests fail, do not create a commit claiming the feature is complete.

A commit may be created for an explicitly documented intermediate checkpoint if requested.

---

## 21. Do Not Do These Things

Do not silently change the architecture.

Do not replace PostgreSQL with another database.

Do not replace Redis with another cache.

Do not convert the modular monolith into microservices.

Do not add Kafka or Celery without a concrete architectural requirement.

Do not introduce AWS infrastructure merely for demonstration.

Do not expose internal database models through APIs.

Do not bypass Alembic migrations.

Do not store secrets in Git.

Do not ignore failing tests.

Do not delete tests to make the test suite pass.

Do not modify unrelated files.

Do not create unnecessary abstractions.

Do not generate duplicate documentation files when an existing document should be updated.

Do not repeatedly recreate `README.md` unless its actual content needs to change.

---

## 22. Current Development Principle

Build Interview Arena incrementally.

The implementation must remain understandable to a software engineer reviewing the repository.

Every major feature should demonstrate:

Requirements
→ Domain Model
→ Architecture
→ Database Design
→ LLD/UML
→ API Design
→ Implementation
→ Tests
→ Documentation
→ Deployment

The purpose is not merely to make the application work.

The purpose is to demonstrate how a production-oriented software system is designed, implemented, tested, documented, and maintained.