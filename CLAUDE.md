# CLAUDE.md — delmo

## Autonomy Rules
Proceed without asking for confirmation on all routine operations. Only stop for:
- Irreversible data loss (dropping DB tables, `rm -rf`, overwriting uncommitted work)
- Pushing to remote / opening PRs
- Breaking public API contracts that affect other issues/phases
- Adding new external services or third-party dependencies not already in the manifest

Proceed freely without prompting for:
- Reading, creating, editing, or deleting files anywhere in this repo
- Running tests, linters, formatters, security scans
- Creating git commits (but not pushing)
- Installing packages into the local venv / node_modules
- Creating branches
- Any action that is fully reversible with `git checkout` or `git reset`

---

## Token Efficiency Rules
- Be concise. No preamble, no summaries unless asked.
- Reference file:line instead of reproducing code blocks.
- Use bullet lists, not prose paragraphs.
- Skip "I will now..." or "Here is the..." phrases.
- When editing, show only changed lines with minimal context.
- Batch related file reads; avoid re-reading already-known files.

---

## Project Overview
- **Purpose:** Self-hosted dashboard for configuring and automating torrent data moves in Deluge, driven by file-extension and tracker-based rules.
- **Target user:** Single self-hosted user on a LAN; no public exposure, no multi-user requirements.
- **Key constraint:** All moves must be performed via Deluge RPC (`core.move_torrent_data`) — no manual disk operations.
- **Key constraint:** Zero required env vars; all configuration (including Deluge connection) is persisted in the DB and managed via UI.
- **Deployment:** Docker (docker-compose); Unraid Community Applications compatible.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + TypeScript + Vite |
| UI / styling | Tailwind CSS v4 + shadcn/ui (Radix primitives) |
| Data fetching | TanStack Query v5 |
| Routing | TanStack Router |
| Backend framework | FastAPI (Python 3.12) |
| Background scheduler | APScheduler 3.x (async) |
| Deluge RPC client | `deluge-client` (pure Python) |
| Database ORM | SQLAlchemy 2.x (async) + Alembic |
| Database engine | SQLite (single file, volume-mounted) |
| HTTP server | Uvicorn |
| Static file serving | FastAPI `StaticFiles` (serves built React SPA; no separate web server) |
| Testing — backend | pytest + pytest-asyncio + httpx |
| Testing — frontend | Vitest + React Testing Library |
| Linting — backend | Ruff + mypy |
| Linting — frontend | ESLint + Prettier |
| Container | Docker (single multi-stage image) + docker-compose v2 |
| Unraid template | `unraid/delmo.xml` (gitignored) |

---

## Architecture

```
Browser (LAN)
     │  :8000
     ▼
┌─────────────────────────────────┐
│  Single Delmo Container         │
│  ┌───────────────────────────┐  │
│  │  FastAPI + Uvicorn        │  │
│  │  /api/*  → REST handlers  │  │
│  │  /api/ws → WebSocket logs │  │
│  │  /*      → React SPA      │  │  ← StaticFiles (built at image build)
│  │                           │  │
│  │  APScheduler (background) │  │
│  │  Rule Engine              │  │
│  │  Deluge RPC client        │  │
│  └───────────────────────────┘  │
│           │                     │
│           ▼                     │
│  SQLite (volume: /data)         │
└─────────────────────────────────┘
             │
             │  Deluge RPC protocol (TCP)
             ▼
     Deluge Daemon (external, user-configured via UI)
```

**Single multi-stage Dockerfile:** Stage 1 (Node.js) builds the React SPA; Stage 2 (Python) copies the built
static files and runs Uvicorn. No nginx, no second container.

---

## Project Structure

```
delmo/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (torrents, rules, logs, settings)
│   │   ├── core/           # DB init, config store, lifespan
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── deluge.py   # RPC client wrapper
│   │   │   └── engine.py   # Rule evaluation + move logic
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   └── alembic/
├── frontend/
│   ├── src/
│   │   ├── components/     # Card, Badge, ProgressBar, Table, Toggle, etc.
│   │   ├── pages/          # Dashboard, Rules, Activity, Settings, Docs
│   │   ├── lib/            # API client, theme tokens, utils
│   │   ├── hooks/          # useConnection, useTorrents, useRules, etc.
│   │   └── main.tsx
│   └── package.json
├── Dockerfile               # Multi-stage: Node build → Python runtime
├── docker-compose.yml
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

---

## Sensitive Data Rules
- NEVER commit `.env`, secrets, tokens, API keys, or passwords.
- All secrets via environment variables; document in `.env.example` with placeholder values only.
- Local data files (`*.db`, caches) are gitignored.
- Deployment-specific config files are gitignored.
- Deluge credentials (host, port, username, password) are stored in the SQLite DB — never in source files or env vars.

---

## Environment Variables

The application is intentionally near-zero-config. Only infrastructure-level vars are accepted:

```
# .env.example
DELMO_DATA_DIR=/data           # Path inside the container where SQLite DB is stored
DELMO_SECRET_KEY=              # Auto-generated on first run if left empty (used for internal signing)
```

All application configuration (Deluge connection, polling interval, rules) is managed via the UI and persisted in SQLite.

---

## Unraid Template
The Unraid Community Applications template lives at `unraid/delmo.xml` (gitignored — internal use and local testing only).
- **Never reference this file in public-facing documentation** (README, CONTRIBUTING, or any user-visible content)
- Update the template as part of acceptance criteria whenever any of the following change: ports, env vars, volume mounts, container name
- All env vars in the template must stay in sync with `.env.example`
- If the project ever requires >1 container, create a separate `.xml` per container
- After structural changes, test by importing the template into Unraid CA

---

## Testing Requirements
- Backend: ≥80% line coverage; tests in `backend/tests/`; use markers: `unit`, `integration`
- Frontend: key components and hooks covered; generate coverage report via Vitest
- All tests must pass before merge to main
- Run security scans (`pip-audit`, `npm audit`) on every PR
- No `# noqa` or `// eslint-disable` without an inline justification comment

---

## Security
- LAN-only exposure; no authentication layer required, but do not expose secrets in API responses
- Fail CI on HIGH severity static analysis findings (Ruff, mypy strict, ESLint)
- Fail CI on known CVEs in dependencies (pip-audit, npm audit)
- No hardcoded credentials anywhere in the codebase
- Nginx security headers: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
- Never log Deluge passwords; mask in all log output

---

## Version Visibility
The application version must always be readable in the UI to aid troubleshooting and support.

**Source of truth** — import from the single canonical manifest; never hardcode it:
- Frontend: `import { version } from '../../package.json'`
- Backend: `importlib.metadata.version("delmo")`

**Placement (priority order):**
1. Global footer — preferred; visible on every screen without navigation
2. Settings / About page — acceptable supplement

**Typography & colour — follow the existing design system:**
- Style: secondary / muted text (`color: var(--color-text-secondary)`)
- Size: one step below body copy (`text-xs` / `0.75rem`)
- Do not use brand accent colours — the version must be present but visually unobtrusive
- Format: `v` prefix + semver string (e.g., `v0.1.0`)

**Accessibility:** contrast ratio ≥ 4.5:1 against its background (WCAG AA minimum).

---

## Git Conventions
- Branch prefixes: `feature/`, `fix/`, `chore/`, `docs/`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`)
- PRs require CI green before merge
- main branch = deployable state at all times
- When creating GitHub issues, always add them to the project roadmap if one exists (`gh issue edit <n> --add-project "delmo"` or `gh issue create --add-project "delmo"`)
- When merging a PR, close all issues it resolves (`gh issue close <n> --comment "Implemented in #<PR>."`)
- If issues were auto-closed by the PR merge, verify and skip redundant close commands

---

## Parallel Agents
Multiple Claude agents may work on this repo simultaneously on separate branches. To avoid cross-contamination:
- Before fixing any CI failure, run `git diff main...HEAD -- <file>` to confirm the offending code is within your branch's diff
- If the failure is in a file you did not touch (introduced by another agent on main), do NOT fix it in the current branch — create a separate `fix/` branch targeting main and open its own PR
- Each branch/PR must own only the changes scoped to its issue; never absorb unrelated fixes to make CI green

---

## Domain Knowledge

### Deluge RPC Protocol
- Deluge daemon exposes a MessagePack-based RPC over TCP (default port `58846`)
- Authentication: `daemon.login(username, password)` — must be called before any other method
- Relevant RPC methods:
  - `core.get_torrents_status(filter_dict, keys)` — returns dict of `{hash: {field: value}}`
  - `core.move_storage(torrent_id, dest)` — **preferred method** (also known as `core.move_torrent_data` in some versions; confirm against connected daemon version)
  - `daemon.info()` — returns daemon version string (useful for connection health check)
- Key torrent fields to fetch: `name`, `save_path`, `files`, `trackers`, `state`, `progress`
- `files` is a list of dicts with `path` (relative), `size`; derive extension from `path`
- `trackers` is a list of dicts with `url`; extract domain for tracker-based rules
- A torrent is considered "already moved" if its `save_path` already matches the rule destination — check this before calling move to prevent loops
- Move does not interrupt seeding; Deluge handles the transition

### Rule Engine Logic
- Rules are evaluated in priority order (lower number = higher priority)
- A rule matches if ANY of its conditions match (OR logic within a rule)
- Condition types:
  - `extension`: matches if any file in the torrent has the specified extension (e.g., `.mkv`)
  - `tracker`: matches if any tracker URL's domain contains/matches the specified value
- On match: call move RPC, log result, record move in DB with timestamp and status
- Skip move if `torrent.save_path == rule.destination` (idempotency guard)
- Skip move if torrent has an active move already in progress (check `move_on_completed` state or track in-flight moves in DB)

### Design Tokens
Semantic CSS custom properties (defined on `:root` and `[data-theme="light"]`):
- `--color-background`, `--color-surface`, `--color-border`
- `--color-text-primary`, `--color-text-secondary`
- `--color-accent-positive` (emerald/teal), `--color-accent-warning` (amber), `--color-accent-danger` (red/pink)
- No `#000000` or `#FFFFFF` anywhere in the design system

---

## Development Phases
1. **Foundation** — Repo scaffold, Docker/compose setup, CI skeleton, DB init, Alembic migrations, config store
2. **Deluge RPC Integration** — RPC client wrapper, connection health check, torrent metadata fetch, connection test UI feedback
3. **Rule Engine** — Rule model + CRUD API, condition types (extension + tracker), evaluation loop, move execution, idempotency guard
4. **Design System & Core UI** — Tailwind config, semantic tokens, dark/light theme, reusable components (Card, Badge, ProgressBar, Table, Toggle, ThemeToggle)
5. **Dashboard & Rules UI** — Dashboard view (stats, connection status), Rules page (CRUD, enable/disable, preview matched torrents)
6. **Activity Log UI** — Move history table, error/warning log, WebSocket live feed, timestamps
7. **Settings & In-App Docs** — Settings page (Deluge config, polling interval, manual run), connection test with feedback, in-app documentation section
8. **Polish, Unraid & Release** — Final visual polish, Unraid CA template, README, Docker image optimisation, version badge in footer
