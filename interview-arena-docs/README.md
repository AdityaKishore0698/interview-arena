# Interview Arena

Peer-powered placement preparation platform.

## Documentation

This repository uses **Documentation as Code**.

The `docs/` directory contains the canonical engineering documentation in Markdown. Architecture decisions are recorded as ADRs under `docs/decisions/`.

## Engineering Design Sequence

```text
Requirements
    ↓
Domain Modeling (0.6)
    ↓
HLD (0.7)
    ↓
Database Design / ERD (0.8)
    ↓
LLD / UML (0.9)
    ↓
API Design (0.10)
    ↓
Real-Time Design (0.11)
    ↓
Security (0.12)
    ↓
Testing (0.13)
    ↓
Deployment (0.14)
    ↓
Implementation
```

This is iterative rather than strict waterfall. A later design discovery can cause an earlier document to be revised.

## Current source-of-truth documents

- `docs/02-domain/domain-model.md`
- `docs/03-architecture/hld.md`
- `docs/04-design/lld.md`
- `docs/05-database/database-design.md`

## Documentation site

Install MkDocs and run:

```bash
mkdocs serve
```

The documentation source is Markdown; `mkdocs.yml` defines the navigation.

## Source of truth

The Markdown files in `docs/` are the project source of truth.

DOCX/PDF exports are learning/reference artifacts and are not the canonical engineering specification.
