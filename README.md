# Interview Arena

Interview Arena is a peer-to-peer mock interview platform. Two candidates are matched from a queue, interview each other over live video and chat (one plays interviewer while the other answers), swap roles for a second round, and rate each other on a 1–5 rubric. Sign-in is by email and password, Google, or as a guest.

The interesting engineering is in the real-time path: matchmaking is an atomic Redis Lua script, the interview state machine and its timers are computed on the server (the browser only renders `endsAt` timestamps), session events fan out to both peers over WebSockets backed by Redis pub/sub, and audio/video is peer-to-peer WebRTC with the backend acting only as a signalling relay. Persistent data (users, sessions, rounds, feedback) lives in PostgreSQL behind SQLAlchemy async and Alembic migrations.

- **Live app:** https://interview-arena-gamma.vercel.app
- **API:** https://interview-arena-backend-m6zz.onrender.com (`/docs` serves the interactive OpenAPI page)

## Screenshots

Captured locally at 1280 px width with a made-up demo account and seeded history.

| | |
|---|---|
| ![Landing and sign-in](assets/01-landing-login.png) | ![Dashboard, dark theme](assets/02-dashboard-dark.png) |
| Landing and sign-in (email/password, Google, guest) | Dashboard: pick a room and mode, review past feedback |
| ![Dashboard, light theme](assets/03-dashboard-light.png) | ![Live interview round](assets/04-live-interview.png) |
| Dashboard in the light theme | Live round: problem, scratchpad, WebRTC video, chat, server timer |

![Round feedback form](assets/05-round-feedback.png)

*Post-round feedback: three 1–5 ratings plus free-text comments.*

## Architecture

```mermaid
flowchart LR
  B[Browser] -->|HTTPS| FE[Next.js frontend<br/>Vercel]
  B -->|REST with JWT<br/>+ WebSocket| API[FastAPI backend<br/>Render]
  B <-.->|WebRTC audio/video<br/>peer to peer| B2[Peer browser]
  API --> PG[(PostgreSQL)]
  API --> R[(Redis)]
  API -->|OAuth code exchange| G[Google OAuth]
```

- The frontend is a Next.js App Router app. It talks to the API with Axios and to the session WebSocket at `/api/v1/sessions/{id}/ws`.
- The backend is a modular monolith: `identity`, `matchmaking`, `interview`, `realtime`, plus shared `core` (config, database, Redis, security).
- **PostgreSQL** holds users, profiles, rooms, problems, sessions, participants, rounds, round roles and feedback.
- **Redis** holds matchmaking queues and locks, guest sessions, presence, WebSocket pub/sub channels and password-reset codes.
- Media never touches the backend. It only relays WebRTC signalling messages.

Local development is the same picture with everything on your machine: `docker compose` provides PostgreSQL 15 and Redis 7, the API runs on `:8000`, and the frontend on `:3000`.

## Features

- **Accounts:** email/password signup that creates the account and signs you in immediately (no email verification), login, Google OAuth, and ephemeral guest sessions.
- **Account settings:** update display name, change password, delete account (soft delete: the row is anonymised so interview history stays consistent).
- **Matchmaking:** join a queue per room (DSA, System Design, OOP/LLD) and mode (Quick or Standard). Pairing is reserved atomically in Redis so a user cannot end up in two matches.
- **Interview lifecycle:** preparation, round 1, feedback, round 2, feedback, complete. Roles reverse automatically for round 2. A session is marked abandoned if a participant disconnects and does not return.
- **Timers:** Quick uses 30 s preparation, 5 min rounds and 60 s feedback; Standard uses 30 s, 15 min and 120 s. The server decides every transition.
- **Problems:** each room has a small seeded question bank keyed by round slot (1–2), so the interviewer gets a real question to ask.
- **Live session UI:** presence indicator, server-driven countdown, a local scratchpad (not synchronised between peers), chat relayed through the server, and WebRTC audio/video with a retry path.
- **Feedback:** communication, technical knowledge and problem-solving ratings (1–5) plus optional comments, submitted idempotently per round.
- **History:** completed sessions with received feedback, for registered users. Guests do not get history.
- **Frontend polish:** dark and light themes, terms and privacy pages.
- **Demo password recovery:** see the next section.

### Demo password recovery

Password recovery is deliberately a **demo mechanism**, not email-based recovery. No email is ever sent and no SMTP configuration exists.

1. `POST /api/v1/auth/password/forgot` stores a 6-digit code in Redis for 15 minutes and returns it in the response as `demo_code`.
2. The reset screen shows the code on screen, labelled as a demo, and pre-fills it.
3. `POST /api/v1/auth/password/reset` accepts the code once, enforces an 8-character minimum for the new password, hashes it with bcrypt, and deletes the code.

Limitations, stated plainly: anyone who knows a registered email address can obtain a code for it and set a new password (this includes Google-only accounts), and there is no rate limiting. An unregistered email receives an equally shaped but unusable code so the response does not reveal which emails exist.

## Tech stack

| Layer | Technologies (from `package.json` / `pyproject.toml`) |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui on Base UI, TanStack Query 5, Zustand 5, Axios, lucide-react |
| Backend | Python 3.14, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy 2 (async) with asyncpg, Alembic, PyJWT (HS256), bcrypt, httpx |
| Data | PostgreSQL, Redis (`redis.asyncio`, Lua scripting, pub/sub) |
| Real time | Native WebSockets, WebRTC (STUN by default, optional TURN) |
| Testing and tooling | pytest + pytest-asyncio, Playwright, ESLint 9, Ruff, mypy |

## API overview

Derived from the FastAPI routers. Interactive docs are at `/docs` on the running API. "JWT" means an `Authorization: Bearer <token>` header. The interview router is mounted under both `/api/v1/rooms` and `/api/v1/sessions` (the frontend uses `/sessions` for session routes and `/rooms` for the room list).

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Create an account and return a JWT | None |
| POST | `/api/v1/auth/login` | Email/password login | None |
| POST | `/api/v1/auth/guest` | Create an ephemeral guest session | None |
| GET | `/api/v1/auth/google/login` | Start Google OAuth | None |
| GET | `/api/v1/auth/google/callback` | Finish OAuth and redirect to the frontend with a token | None |
| POST | `/api/v1/auth/password/forgot` | Demo recovery: return a reset code | None |
| POST | `/api/v1/auth/password/reset` | Reset a password with the code | None |
| GET | `/api/v1/auth/me` | Current user | JWT |
| PATCH | `/api/v1/auth/me` | Update display name | JWT (registered) |
| DELETE | `/api/v1/auth/me` | Soft-delete the account | JWT (registered) |
| POST | `/api/v1/auth/password/change` | Change or set a password | JWT (registered) |
| POST | `/api/v1/auth/logout` | Clear queue and match state | JWT |
| GET | `/api/v1/sessions/` | List interview rooms | None |
| GET | `/api/v1/sessions/{session_id}` | Session state | JWT |
| POST | `/api/v1/sessions/{session_id}/leave` | Leave a session | JWT |
| POST | `/api/v1/sessions/{session_id}/rounds/{round_id}/feedback` | Submit feedback | JWT |
| GET | `/api/v1/sessions/user/history` | Completed sessions with feedback | JWT |
| POST | `/api/v1/matchmaking/join` | Join a queue (`QUICK` or `STANDARD`) | JWT |
| POST | `/api/v1/matchmaking/leave` | Leave the queue | JWT |
| GET | `/api/v1/matchmaking/status` | Queue or match status | JWT |
| WS | `/api/v1/sessions/{session_id}/ws?token=` | Events, chat and WebRTC signalling | JWT in query string |
| GET | `/health` | Liveness check (does no database or Redis I/O) | None |

Two test-only routes (`POST /api/v1/debug/flush-redis`, `DELETE /api/v1/debug/redis`) exist for the E2E suite and return 403 unless `TESTING=true`.

## Local development

### Prerequisites

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Node.js 20 or newer
- Docker (for PostgreSQL and Redis)

### 1. Start PostgreSQL and Redis

```bash
docker compose up -d
```

The defaults in `backend/app/core/config.py` match `docker-compose.yml`, so no `.env` file is needed for local development.

### 2. Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload        # http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                                 # http://localhost:3000
```

The frontend calls `http://localhost:8000` unless `NEXT_PUBLIC_API_URL` is set (for example in `frontend/.env.local`).

## Testing

```bash
# Backend: 63 tests (needs PostgreSQL and Redis)
cd backend && TESTING=true uv run pytest

# Frontend
cd frontend
npx tsc --noEmit        # type check (there is no npm script for it)
npm run lint
npm run build
```

Backend tests cover authentication and registration, password recovery, Google OAuth (mock and real code paths), guest sessions, matchmaking and the Lua reservation, the interview lifecycle, abandonment, feedback idempotency, and realtime behaviour.

> **Warning:** the pytest fixtures flush Redis before and after every test. Point `REDIS_URL` at a throwaway Redis, never one that holds data you care about.

**End-to-end (Playwright).** Five specs in `frontend/e2e` drive real browsers, including two-user matchmaking, chat and WebRTC. They are local-only: the config and specs assume the frontend on `localhost:3000` and the API on `localhost:8000` with `TESTING=true` (which shortens interview timers to seconds and mocks Google OAuth).

```bash
cd backend && TESTING=true uv run uvicorn app.main:app
cd frontend && npm run build && npm run start
cd frontend && npx playwright test
```

## CI/CD

There is no GitHub Actions workflow in this repository, so tests, lint and builds are not run automatically. Vercel builds and deploys the frontend when commits land on `main` (visible as deployment records on the GitHub repository). The repository contains no Render or Vercel configuration files, so the backend's Render build and start settings are managed outside this repo.

## Environment variables

Names and purposes only.

**Backend**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection for the application. `postgres://` and `postgresql://` URLs are normalised to the asyncpg driver and `sslmode` is translated. |
| `DIRECT_URL` | Optional. A direct (non-pooled) PostgreSQL connection used by Alembic; falls back to `DATABASE_URL`. |
| `REDIS_URL` | Redis connection (`redis://` or `rediss://`). |
| `SECRET_KEY` | JWT signing key. The default in code is a development placeholder and must be overridden in production. |
| `ALGORITHM` | JWT algorithm. Defaults to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime. Defaults to 7 days. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth client credentials. |
| `BACKEND_URL` | Public URL of this API. Used to build the Google OAuth `redirect_uri` (`{BACKEND_URL}/api/v1/auth/google/callback`), which must match the Google client configuration. |
| `FRONTEND_URL` | Public URL of the frontend. The OAuth callback redirects here with the token. |
| `TESTING` | Test-only. Shortens timers, mocks Google OAuth and enables the debug routes. Never set in production. |

**Frontend**

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | API base URL (also used to derive the WebSocket URL). Baked in at build time. |
| `NEXT_PUBLIC_TURN_URL`, `NEXT_PUBLIC_TURN_USERNAME`, `NEXT_PUBLIC_TURN_CREDENTIAL` | Optional TURN relay for WebRTC. Without it, connections use STUN only. |

## Deployment

- **Frontend:** Next.js on Vercel at https://interview-arena-gamma.vercel.app, deployed from `main`.
- **Backend:** FastAPI on Render at https://interview-arena-backend-m6zz.onrender.com, backed by PostgreSQL and Redis.
- Production needs `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `FRONTEND_URL` and `BACKEND_URL`, plus the Google credentials for Google sign-in. `TESTING` must be unset.
- `GET /health` returns 200 without touching the database or Redis, so it shows the process is up, not that its dependencies are reachable. If auth fails with a 500, check that `DATABASE_URL` and `REDIS_URL` are set: the code silently falls back to `localhost` defaults otherwise.
- Google Cloud must list `{BACKEND_URL}/api/v1/auth/google/callback` as an authorised redirect URI.

`interview-arena-docs/` contains the original design documents (requirements, HLD/LLD, database, API, realtime, security, testing, deployment, ADRs). They are design-phase documents; where they differ from the code (for example the OpenAPI sketch), the code is the source of truth.

## Database and migrations

Schema changes are managed with Alembic (`backend/alembic/versions`), a single linear chain ending at `b1f2c3d4e5a6`. Run migrations from `backend/`:

```bash
uv run alembic upgrade head
```

| Revision | Purpose |
|---|---|
| `524ab1dd6a84` | Initial schema |
| `0002` | Seeds the three interview rooms (DSA, System Design, OOP/LLD) |
| `7e93940e4498`, `89581413d982` | Session `mode` (Quick/Standard) and a session `version` counter |
| `489d85220153` | Rounds, round participants and feedback tables |
| `a8e9876e9f00` | Adds `auth_provider` and `is_verified` to users |
| `b1f2c3d4e5a6` | Adds room difficulty and the seeded question bank |

Notes:

- The current code expects the schema at `b1f2c3d4e5a6`. Run `alembic upgrade head` before deploying code that depends on a newer revision.
- `a8e9876e9f00` added `is_verified` defaulting to false and did not backfill existing rows. The application no longer checks `is_verified` at login, so those users are not locked out. The column is kept to avoid a schema change.
- Whether production has been migrated to `b1f2c3d4e5a6` cannot be determined from this repository. Check with `alembic current` against the production database.
- The Render service configuration is not in this repository, so it is not documented here whether migrations run automatically on deploy.

## Known demo limitations

- **Password recovery is a demo** (see above): the reset code is returned to whoever asks, so anyone who knows an email can reset that account's password. There is no rate limiting on auth endpoints.
- **No email is sent and email is never verified.** Signup does not confirm ownership of the address.
- **Tokens:** JWTs last 7 days, are stored in `localStorage`, and are not revoked on logout (only queue and match state is cleared). The WebSocket takes the token as a query parameter.
- **CORS** allows all origins with credentials enabled.
- **Google sign-in** matches an existing account by email and does not check Google's `verified_email` flag.
- **Route protection is client-side:** pages redirect unauthenticated users; there is no server-side middleware.
- **Guests** are ephemeral (Redis, 24 h) and get no saved history.
- **The scratchpad is local** to each browser; it is not synchronised between peers.
- **Video** relies on STUN unless TURN is configured, so it may fail on restrictive networks. The call is started manually with "Connect Audio/Video".
- **Small content set:** three rooms with a two-slot seeded question bank each.
- **No CI**, and the E2E suite is tied to fixed local ports.
