# Deployment Design

**Phase:** 0.14  
**Status:** Proposed

## 1. Purpose

This document defines how Interview Arena moves from development to a publicly deployed application while keeping infrastructure simple, reproducible, observable, and appropriate for a student project with a zero/near-zero budget.

The deployment design intentionally avoids premature infrastructure complexity.

## 2. Deployment Principles

1. Prefer free or generous free-tier services.
2. Avoid AWS for this project because the available free tier is exhausted.
3. Keep application architecture vendor-neutral.
4. Use managed services where they reduce operational burden.
5. Containerize the backend for reproducibility.
6. Keep durable state outside application process memory.
7. Design for horizontal scaling without paying for horizontal scaling before it is needed.
8. Treat deployment configuration as code where practical.
9. Never commit production secrets.
10. Verify deployments automatically.

## 3. Target Environments

```text
Development
     ↓
Staging
     ↓
Production
```

### Development

Local machine for implementation, debugging, unit tests, PostgreSQL, and Redis.

### Staging

A production-like environment used for deployment verification and E2E testing when the selected hosting provider supports it within free limits.

### Production

The public application.

The first deployment should use the smallest viable free-tier configuration.

## 4. Target Architecture

```text
                         INTERNET
                            │
                            ▼
                     HTTPS / WSS
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
           ┌──────────┐         ┌──────────┐
           │ Frontend │         │ Backend  │
           └──────────┘         └────┬─────┘
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                   ┌─────────────┐       ┌──────────┐
                   │ PostgreSQL  │       │  Redis   │
                   │ Persistent  │       │ Ephemeral│
                   └─────────────┘       └──────────┘
```

The deployment provider may change. The logical architecture should not.

## 5. Free-Tier Deployment Strategy

The deployment should use services that have a usable free tier or genuinely zero-cost local development path.

A reasonable initial arrangement is:

```text
Frontend
    → free static/frontend hosting

Backend
    → free application/container hosting, if available

PostgreSQL
    → free managed PostgreSQL tier, if available

Redis
    → free managed Redis-compatible service, if available
```

Exact providers must be verified at implementation time because free-tier limits and pricing change.

Do not design the application around a provider-specific feature unless there is a clear benefit.

## 6. Frontend Deployment

The frontend can be deployed independently.

```text
Browser
   │
   ▼
Frontend hosting
   │
   ├── HTTPS API
   │
   └── WSS
          │
          ▼
       Backend
```

The frontend must obtain API/WebSocket endpoints from environment configuration rather than hard-coded local URLs.

## 7. Backend Deployment

Initially deploy a single backend instance.

```text
Internet
   │
   ▼
Backend instance
   │
   ├── PostgreSQL
   └── Redis
```

Do not deploy multiple instances until there is a real need.

The backend must avoid relying on process-local memory for durable or shared application state.

## 8. Horizontal Scaling

The logical architecture should permit:

```text
                 Load Balancer
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    Backend 1     Backend 2     Backend 3
        │             │             │
        └─────────────┼─────────────┘
                      │
             ┌────────┴────────┐
             ▼                 ▼
        PostgreSQL          Redis
```

The project does not need to pay for this at Phase 0.

## 9. WebSocket Deployment

WebSockets require special consideration.

With multiple backend instances:

```text
User A → Backend 1
User B → Backend 2
```

cross-instance events may need shared coordination:

```text
Backend 1
    │
    ▼
Redis Pub/Sub
    │
    ▼
Backend 2
```

The implementation must therefore avoid assuming that both participants always connect to the same process.

The first deployment may use one backend instance, but the code should not unnecessarily prevent future scaling.

## 10. Database Deployment

Use a managed PostgreSQL service where a free tier is available.

The application should connect through a database URL supplied by environment configuration.

Responsibilities include:

- migrations
- backups where the provider supports them
- connection limits
- indexes
- credentials
- recovery planning

## 11. Database Migrations

Schema changes must be version-controlled.

```text
Migration 001
Migration 002
Migration 003
...
```

Deployment flow:

```text
New version
    ↓
Run migration
    ↓
Start / update application
```

Production schema changes must not normally be performed manually.

## 12. Backward-Compatible Migrations

Avoid destructive migrations that break the currently running application.

Prefer an expand/migrate/contract approach:

```text
1. Add new structure
2. Deploy compatible code
3. Backfill
4. Switch reads/writes
5. Remove obsolete structure later
```

This becomes important when multiple backend instances are eventually deployed.

## 13. Configuration and Secrets

Never commit:

```text
DATABASE_URL
DATABASE_PASSWORD
JWT_SECRET
REDIS_URL
API_KEYS
```

Use hosting-provider environment variables/secrets.

For local development:

```text
.env
```

may be used, but real secrets must remain outside Git.

Provide a `.env.example` containing variable names without secret values.

## 14. Containerization

The backend should have a Dockerfile so the runtime is reproducible.

Conceptually:

```text
Docker image
 ├── application
 ├── runtime
 └── dependencies
```

The image should be built by CI where practical.

The project should not depend on an engineer's machine-specific runtime configuration.

## 15. CI/CD

Target pipeline:

```text
GitHub
   │
   ▼
Pull Request / Push
   │
   ▼
CI
   ├── lint
   ├── static checks
   ├── unit tests
   ├── integration tests
   ├── security checks
   └── build
          │
          ▼
      deployment
          │
          ▼
       staging
          │
          ▼
        E2E
          │
          ▼
     production
```

The exact CI provider can be selected later.

## 16. Deployment Strategy

For the initial free-tier deployment, use the simplest reliable deployment mechanism supported by the selected provider.

Do not introduce Kubernetes, service meshes, or complex deployment orchestration.

When multiple instances become necessary, rolling or blue-green strategies can be evaluated.

## 17. Health and Readiness

The backend should expose:

```text
GET /health
GET /ready
```

Conceptually:

```text
health
→ Is the process alive?

readiness
→ Can this instance safely receive traffic?
```

Readiness can include checks for critical dependencies where appropriate.

## 18. Graceful Shutdown

The backend should handle shutdown signals.

```text
SIGTERM
   ↓
Stop accepting new work
   ↓
Finish active requests
   ↓
Handle WebSocket sessions
   ↓
Release resources
   ↓
Exit
```

This reduces interrupted sessions and corrupted state.

## 19. Observability

Use three pillars:

```text
Logs
Metrics
Traces
```

### Logs

Examples:

```text
MATCH_CREATED
ROUND_STARTED
ROUND_COMPLETED
FEEDBACK_SUBMITTED
USER_DISCONNECTED
```

Logs should use structured fields where practical.

### Metrics

Important initial metrics:

```text
active_users
matchmaking_queue_size
match_success_rate
average_match_wait_time
interview_completion_rate
websocket_connections
websocket_disconnects
api_latency
error_rate
```

Tracing can be added later.

## 20. Monitoring

The deployed application should allow us to detect:

- high error rate
- high API latency
- database failure
- Redis failure
- WebSocket failure spikes
- abnormal matchmaking queue growth
- resource exhaustion

Use the hosting provider's free monitoring where adequate.

Do not pay for a dedicated observability platform merely to demonstrate monitoring.

## 21. Backup and Recovery

The project should document:

- whether the database provider supplies backups
- how database export can be performed
- what data would be lost if the free database disappears
- how the application can be redeployed

The concepts of RPO and RTO should be understood even if the initial values are modest.

## 22. Infrastructure as Code

Full Terraform/Kubernetes infrastructure is not required initially.

The project should first use provider configuration plus repository configuration that can be reproduced.

Infrastructure as Code can be introduced later if it adds learning or resume value.

## 23. Cost Constraint

The project has an explicit cost constraint:

> Initial deployment cost target: ₹0.

The implementation must not depend on paid AWS infrastructure.

Before selecting any external service, verify its current free-tier terms.

Avoid accidentally exceeding free quotas through:

- excessive logging
- uncontrolled database storage
- background workers
- unnecessary polling
- large build artifacts
- high-frequency monitoring
- runaway WebSocket connections

## 24. Things We Explicitly Do Not Need Yet

Do not introduce:

- Kubernetes
- service mesh
- Kafka
- multi-region deployment
- custom load balancers
- self-managed databases
- complex service discovery
- elaborate disaster recovery
- microservices solely for resume value

Engineering maturity includes knowing when not to introduce infrastructure.

## 25. Deployment Definition of Done

Phase 0.14 is complete when we have defined:

- development/staging/production environments
- free-tier deployment constraints
- frontend/backend deployment boundaries
- PostgreSQL deployment
- Redis deployment
- database migrations
- secrets/configuration
- containerization
- CI/CD
- health/readiness checks
- graceful shutdown
- WebSocket deployment considerations
- horizontal scaling strategy
- observability
- monitoring
- backup/recovery
- deployment/rollback considerations

## 26. Implementation Transition

Phase 0.14 is the final architecture/design phase.

After this phase, implementation begins.

The SDD remains the source of truth. Implementation agents such as Antigravity must:

1. inspect the repository
2. read the relevant SDD documents
3. understand the existing implementation
4. identify inconsistencies
5. propose changes when design conflicts exist
6. implement incrementally
7. run tests
8. update documentation when implementation changes the design

The agent must not silently replace architectural decisions with its own preferred architecture.
