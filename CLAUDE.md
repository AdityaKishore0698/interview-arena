# PlacementPrep / Interview Arena - Agent Handover Document

This document is a comprehensive technical specification and handover guide for the PlacementPrep project. It is designed to give any AI agent (or human engineer) complete context on the architecture, business logic, rules, and existing implementation of the system.

## 1. Project Purpose & Overview
**PlacementPrep (Interview Arena)** is a peer-powered placement preparation platform. It allows candidates to practice interviews with other candidates through real-time, structured, server-authoritative mock interview sessions. 

The application is built as a realistic **production-grade Modular Monolith**, not a prototype. It enforces strict separation of concerns, robust state machines, and concurrency safety.

### Core Capabilities
- Authenticated accounts (Google OAuth, Email OTP) alongside ephemeral Guest flows.
- Concurrent Matchmaking using Redis queues (Quick & Standard modes).
- Real-time signaling and state synchronization via WebSockets (Redis Pub/Sub backplane).
- Peer-to-Peer Audio/Video communication via WebRTC.
- Server-authoritative interview lifecycle (Preparation -> Round 1 -> Feedback -> Round 2 -> Feedback -> Completion).
- Persistent historical records and feedback evaluation matrices.

## 2. Tech Stack & Infrastructure
### Backend
- **Framework:** Python 3.11+, FastAPI
- **Database:** PostgreSQL (persistent truth) + SQLAlchemy 2.x (async) + Alembic (migrations)
- **Cache/PubSub:** Redis (matchmaking queues, pub/sub for real-time events, ephemeral guest states)
- **Testing:** Pytest (100% integration coverage required)

### Frontend
- **Framework:** Next.js 14+ (React), TypeScript
- **Styling:** Tailwind CSS, shadcn/ui
- **State Management:** TanStack Query (React Query) + Zustand
- **Testing:** Playwright for full End-to-End browser acceptance tests.

## 3. Architecture & Principles
- **Modular Monolith:** Separated into `identity`, `matchmaking`, `interview`, and `realtime` modules.
- **Server-Authoritative:** The frontend **never** infers state transitions or timers. The backend is the single source of truth for session timers and lifecycle changes.
- **Idempotency:** Real-time state transitions and match reservations are built to survive concurrent duplicate requests.
- **WebSocket Usage:** WebSockets are strictly for event synchronization (signaling, chat, lifecycle events). REST is used for commanding and mutating persistent state (e.g., submitting feedback).
- **Concurrency Safety:** Row-level locks in PostgreSQL and Lua scripts in Redis prevent ghost matches and dirty reads.

## 4. Sub-Systems Deep Dive

### A. Identity & Authentication (`backend/app/identity`)
Supports two flows:
1. **Registered Users:** 
   - Google OAuth (`/auth/google/login`).
   - Email OTP (`/auth/otp/send` -> `/auth/otp/verify`).
   - Issues a JWT securely, persisting users in PostgreSQL.
2. **Guests:** Ephemeral users intended for immediate quick-play without registration. Guest data resides entirely in Redis and expires via TTL.

### B. Matchmaking (`backend/app/matchmaking`)
- Uses Redis for queueing (`QUICK` vs `STANDARD` modes are isolated).
- When two users match, a Redis Lua script idempotently pops them from the queue, assigns roles (Interviewer vs Interviewee), and creates an `InterviewSession`.
- Prevents "Ghost Matches": Users must successfully poll/acknowledge the match. Matchmaking locks (`active_match:<user_id>`) prevent users from entering multiple queues concurrently.

### C. The Interview Lifecycle & State Machine (`backend/app/interview`)
The session is rigorously governed by `backend/app/interview/lifecycle.py` and transitions strictly via timestamps.
**State Flow:**
1. `CREATED`
2. `PREPARATION` (Users read instructions, verify media)
3. `ROUND_1_ACTIVE` (Role 1: Interviewer, Role 2: Interviewee)
4. `ROUND_1_FEEDBACK` (Independent evaluation using a 1-5 rubric + comments)
5. `ROUND_2_ACTIVE` (**Automatic Role Reversal**)
6. `ROUND_2_FEEDBACK`
7. `COMPLETED` (Persisted to historical records for dashboard)
8. `ABANDONED` (If a user abruptly disconnects and timeout lapses)

**Critical Implementation Detail:**
Lifecycle state transitions commit to the database (or Redis for guests) *before* publishing the `EVENT` over WebSocket Pub/Sub to avoid frontend `refetch()` race conditions.

### D. Real-Time Signaling & Chat (`backend/app/realtime`)
- WebSockets handle `PING`/`PONG` (liveness), `CHAT_MESSAGE`, and `SIGNAL` (WebRTC SDP/ICE candidates).
- Messages are broadcast to a specific Redis channel `session:<session_id>:events`.
- Chat operates independent of local echo; `A -> B` and `B -> A` validation occurs through the backend.

### E. WebRTC (Audio/Video)
- Video components (`frontend/src/components/interview/VideoPanel.tsx`) establish Peer-to-Peer media.
- Backend is **Signaling Only**, it never handles the media stream.
- Currently utilizes standard Google STUN (`stun:stun.l.google.com:19302`).

### F. Frontend UX & Design Language
- **Visual Direction:** "Clarity Light + Focus Dark". Premium interview-platform aesthetic. No generic dashboards. Deep navy dark themes, atmospheric gradients, and strong semantic hierarchy.
- **Arena Layout:** Desktop view is dominated by the Interview Workspace (split between Problem Description and Code/Scratchpad). WebRTC media and Chat collapse into a secondary sidebar.

## 5. Directory Structure Reference
```
backend/app/
├── core/         # Config, Database setup, Redis connections, Security JWTs
├── identity/     # Auth routers, User models, OTP services
├── matchmaking/  # Queue logic, Redis Lua scripts
├── interview/    # Session lifecycle, SQLAlchemy Round models, Rubric submissions
├── realtime/     # WebSocket Connection Manager, PubSub Router
└── main.py       # FastAPI entrypoint, CORS configuration

frontend/src/
├── app/          # Next.js App Router (Dashboard, Interview Room)
├── components/   # UI logic (ChatPanel, VideoPanel, InterviewWorkspace, QueueUX)
├── lib/          # API Axios clients, Utils
└── store/        # Zustand Auth states
```

## 6. Testing Philosophy
- **Do not bypass tests.** If a test fails, fix the implementation, do not mock the test away.
- E2E Tests (`frontend/e2e/auth-flow-full.spec.ts`) utilize multiple Playwright browser contexts in parallel to simulate A->B interactions, verifying matchmaking, presence, media tracks, chat, and the full state machine.
- To avoid CI/Playwright timeouts on real-world 45-minute interviews, the backend supports a `TESTING=true` environment override which radically accelerates timer durations (e.g., 15-second rounds) without changing the state machine logic itself.

## 7. Working Constraints for AI Agents
1. **No Speculative Architecture:** Do not add Kafka, microservices, Monaco CRDTs, or AWS infrastructure unless explicitly requested by the user.
2. **Server-Authoritative UX:** The frontend must never guess the next state. If a countdown reaches zero, the frontend must wait for the backend WebSocket `EVENT` or fetch authoritative state.
3. **Database Rules:** Alembic migrations are required for all schema changes. Never modify models without generating a migration.
4. **Environment:** When booting the local test environment, Next.js must be built/started (`npm run build && npm run start`), the Postgres/Redis Docker containers must be up, and the Python backend must run with `TESTING=true` to support E2E mocking of OAuth/Timers.


---

## 🤖 Claude Code Specific Directives
You are acting as the Lead Full-Stack Engineer on this project. Your current priorities are:

1. **Frontend Polish (Production-Ready UI):**
   - Upgrade the Next.js frontend to look premium, using the "Clarity Light + Focus Dark" aesthetic.
   - Improve the shadcn/ui components, typography, and atmospheric gradients. 
   - Ensure the Interview Workspace (Code/Scratchpad vs. A/V sidebar) is highly responsive and professional.

2. **Bug Fixing & Reliability:**
   - Identify and fix existing bugs in the state machine, WebSocket synchronization, or UI state.
   - Do not bypass or mock away failing tests. If a test fails, fix the code.

3. **Test Execution Protocol:**
   - **Backend:** Run Python integration tests using `pytest`.
   - **Frontend/E2E:** Run the Playwright end-to-end tests (e.g., `npx playwright test`).
   - **Environment:** Always ensure `TESTING=true` is set when running tests locally so the 45-minute mock interview timers are accelerated to 15 seconds. Ensure Postgres and Redis containers are running before executing tests.

   ## 🛠 Engineering & Git Workflow Rules
You must adhere strictly to these production standards:
1. **Plan Before Execution:** Always outline your proposed changes and the files involved before modifying code. Wait for my approval.
2. **Feature Branching:** Never commit directly to `main` or `master`. Always checkout a descriptive feature branch (e.g., `git checkout -b fix/port-revert` or `feat/dashboard-metrics`) before making changes.
3. **Atomic Commits:** Commit your changes in small, logical units. Use Conventional Commits (e.g., `fix(frontend): revert port overrides to default 3000`).
4. **Test-Driven Validation:** Run the test suite (`pytest` for backend, `npx playwright test` for frontend) **before** every commit. Do not commit failing code.
5. **Environment Configuration:** Never hardcode environment variables, ports, or credentials in the source code. Always use `.env` files and environment-driven configurations.