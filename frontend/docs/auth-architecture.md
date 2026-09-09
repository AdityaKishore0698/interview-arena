# Frontend Authentication Architecture (Phase 3A)

## Decision: JWT Storage

The FastAPI backend issues JWT tokens upon authentication (Guest or Registered) and expects them to be provided via the `Authorization: Bearer <token>` header for REST endpoints, and via the `?token=<jwt>` query parameter for WebSockets.

### Options Considered
1. **HttpOnly Secure Cookies via Next.js Route Handlers (BFF):**
   - *Pros:* Most secure against XSS.
   - *Cons:* Requires introducing a Next.js server proxy layer. The browser cannot easily attach HttpOnly cookies to cross-domain backend WebSocket connections without proxying the WebSocket connection as well. Modifying the backend to natively accept and set HttpOnly cookies would break the explicit API contract documented in the SDD.
   
2. **Local Storage (Chosen Approach):**
   - *Pros:* Directly compatible with the existing FastAPI backend and WebSocket protocol. Keeps the frontend architecture strictly as a Client (SPA-like) connecting directly to the API, avoiding unnecessary backend proxy infrastructure.
   - *Cons:* Susceptible to XSS.
   
### Implementation
We have implemented a Zustand store (`src/store/useAuth.ts`) that persists the authentication state (token and user profile) to `localStorage`. An Axios interceptor (`src/lib/api.ts`) automatically retrieves this token and attaches it to the `Authorization` header for all outgoing API requests.

Future implementations of the WebSocket connection will also read from this store to append the `?token=` parameter.
