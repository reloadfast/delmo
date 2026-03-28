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
- HTTP security headers via FastAPI middleware: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
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
- Format: `v` prefix + semver string (e.g., `v0.2.0`)

**Accessibility:** contrast ratio ≥ 4.5:1 against its background (WCAG AA minimum).

**Acceptance criteria — every PR and release must satisfy all of the following before merge:**
- [ ] Version string bumped in the canonical manifest (`pyproject.toml` + `frontend/package.json`) following semver
- [ ] Version renders correctly in the UI at the designated placement (manually verified)
- [ ] No version string is hardcoded anywhere outside the canonical manifests
- [ ] `CHANGELOG.md` entry written for the new version ([Keep a Changelog](https://keepachangelog.com) format: `## [x.y.z] – YYYY-MM-DD` with Added / Changed / Fixed / Removed sub-sections)
- [ ] Git tag `vx.y.z` created and pushed after the release PR merges

---

## Versioning

The version is defined in **two files that must always be kept in sync**:
- `pyproject.toml` → `[project] version = "x.y.z"` (backend source of truth; read at runtime via `importlib.metadata`)
- `frontend/package.json` → `"version": "x.y.z"` (frontend source of truth; read at build time via `import { version }`)

**Never hardcode the version string anywhere else in the codebase.**

**When to bump** (follow semver):
- `patch` (`0.2.x`) — bug fixes only, no new UI or API surface
- `minor` (`0.x.0`) — new features, new API endpoints, meaningful UI additions
- `major` (`x.0.0`) — breaking changes to the public API or Docker interface

**How to bump** — update both files atomically in the same commit, then tag:
```
# 1. Edit pyproject.toml  →  version = "0.3.0"
# 2. Edit frontend/package.json via npm (also updates package-lock.json):
cd frontend && npm version 0.3.0 --no-git-tag-version
# 3. Commit:
git add pyproject.toml frontend/package.json frontend/package-lock.json
git commit -m "chore: bump version to 0.3.0"
# 4. Tag (on main after merge):
git tag v0.3.0
```

Every PR that ships user-visible features or meaningful bug fixes **must** include a version bump commit and a `CHANGELOG.md` entry. Purely internal chores (CI tweaks, tests, docs) may skip the bump.

---

## Git Conventions
- Branch prefixes: `feature/`, `fix/`, `chore/`, `docs/`, `release/`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `release:`)
- PRs require CI green before merge
- main branch = deployable state at all times
- Version bump + CHANGELOG entry are **required acceptance criteria** for any release PR (see Version Visibility)
- When creating Forgejo issues, reference them in commits by ID
- When merging a PR, close all issues it resolves
- If issues were auto-closed by the PR merge, verify and skip redundant close commands
- **Never push to a branch after its PR is open** — if the PR merges while you're still committing, those commits land on the branch but never reach `main`. Always `git fetch origin && git log origin/main` before pushing follow-up fixes. If the PR is already merged, create a new branch from `origin/main`, cherry-pick the commit(s), and open a new PR.

**Remote (Forgejo):**
- `origin` → `forgejo:Wind/delmo.git` — uses the `forgejo` SSH alias defined in `~/.ssh/config` (resolves to `192.168.1.110:1022`)
- Always use the alias form — never the raw `ssh://git@192.168.1.110:1022/` URL
- Standard operations: `git push origin main`, `git fetch origin`, `git pull origin main`

**GitHub remote (`github`) — deprecated for delmo:**
- GitHub is no longer used for delmo; `github` remote may still be configured locally but must never be pushed to automatically or as part of any PR/CI workflow
- Only push to `github` when the user **explicitly asks** for it; never include it in branch push steps or CI automation
- All PRs target Forgejo (`origin`) only

**Forgejo API / issue management:**
- Use `mcp__forgejo__*` MCP tools — they authenticate via the configured Forgejo token automatically; no manual curl needed for issue/PR/repo operations

---

## Forgejo Docker Registry

The registry is served over HTTPS via Traefik at `forgejo.moseisley.es` — standard `docker/login-action` works fine.

**Login:**
```yaml
- name: Log in to Forgejo registry
  uses: docker/login-action@v3
  with:
    registry: forgejo.moseisley.es
    username: ${{ github.actor }}
    password: ${{ secrets.FORGEJO_TOKEN }}
```

**Image name:** `forgejo.moseisley.es/wind/delmo`

**Tags — use explicit ref, not template (`enable={{is_default_branch}}` does not resolve in Forgejo Actions):**
```yaml
- name: Generate Docker image tags
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: forgejo.moseisley.es/wind/delmo
    tags: |
      type=raw,value=main,enable=${{ github.ref == 'refs/heads/main' }}
      type=sha,prefix=sha-,format=short
      type=semver,pattern={{version}}
      type=raw,value=latest
```

**`GITHUB_TOKEN` does NOT have package registry write access in Forgejo Actions** — use a Forgejo PAT with `package` scope stored as repo secret `FORGEJO_TOKEN`.

**Forgejo Actions API — broken methods (all return 404 on current Forgejo version):**
- `list_runs`, `list_jobs`, `list_workflows`, `get_job_log_preview` via MCP — do NOT attempt; they waste tool calls

**Working approach to inspect CI:**
1. Check runner logs: `ssh root@192.168.1.110 "docker logs forgejo-runner 2>&1 | tail -50"`
2. Check task status via Forgejo API:
   ```bash
   curl -s "https://forgejo.moseisley.es/api/v1/repos/Wind/delmo/actions/tasks" \
     -H "Authorization: Bearer $TOKEN"
   ```
3. Check registry packages:
   ```bash
   curl -s "https://forgejo.moseisley.es/api/v1/packages/Wind?type=container&limit=20" \
     -H "Authorization: Bearer $TOKEN"
   ```

**Generating a temporary scoped token when none is available:**
```bash
ssh root@192.168.1.110 "docker exec -u git Forgejo forgejo admin user generate-access-token \
  --username Wind --token-name debug-tmp --raw --scopes read:repository,read:package"
```
- Container name is `Forgejo` (capital F) — not `forgejo`; must use `-u git`
- Delete temporary tokens after use via Forgejo UI → Settings → Applications

---

## Backlog / Roadmap Conventions
- All backlog, roadmap, and milestone tracking files must use codified IDs for every item (e.g. `SEC-001`, `BUG-003`, `UX-011`)
- ID format: `<CATEGORY>-<NNN>` — category is uppercase, number is zero-padded to 3 digits
- IDs must never be reused or renumbered once assigned; retired items stay in the file marked `[DONE]` or `[DROPPED]`
- When referencing a backlog item in a commit message, PR, or comment, always use its ID (e.g. "fixes BUG-001")
- New items are appended at the bottom of their category table; do not insert mid-table to avoid ID churn
- Backlog files are gitignored — they are local working documents, not public artefacts

---

## GitHub Actions / CI Efficiency

**Structure rules — one workflow file, jobs grouped by language:**
- Fold lint + test + security audit into a single job per language (e.g. `backend`, `frontend`)
  — do NOT create a separate `security.yml`; bake pip-audit/npm-audit into the CI jobs
- Docker build/push only on `push` to `main` or tags — never on PRs alone
- Secret scanning may be its own lightweight job but stays in the same workflow file

**Every workflow must include a concurrency block to cancel stale runs:**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

**Always cache package managers:**
- Python: `cache: pip` in `actions/setup-python` (already in CI)
- Node: `cache: npm` + `cache-dependency-path: frontend/package-lock.json` in `actions/setup-node` (already in CI)

**Target job count:** ≤ 4 jobs per workflow trigger (backend, frontend, docker, release).

**Self-hosted runner disk hygiene — prune dangling images after every successful push:**
```yaml
- name: Prune dangling images
  if: success()
  run: docker image prune -f
```
- `docker image prune -f` removes **dangling images only** (untagged layers) — build cache is untouched
- Never use `docker builder prune -f` (destroys build cache) or `docker system prune -f` (removes volumes)

**`docker/metadata-action` tag generation — `enable={{is_default_branch}}` does NOT resolve in Forgejo Actions:**
- It produces empty tags, causing buildx to fail with `tag is needed when pushing to registry`
- Always use the explicit form:
```yaml
tags: |
  type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
  type=semver,pattern={{version}}
  type=semver,pattern={{major}}.{{minor}}
  type=sha,prefix=sha-,format=short
```
- The current `ci.yml` was updated to use `forgejo.moseisley.es/wind/delmo` with the explicit form.

**CI workflow path hygiene:**
When deleting a module or directory, immediately update all CI workflow references to it (`ruff check`, `--cov=`, etc.). Stale paths cause CI to fail even though the deletion was correct.

---

## Docker Best Practices

**HEALTHCHECK — use `curl`, never `python3` (or other heavy interpreters):**
- Spawning a full interpreter every 30 s causes constant CPU spikes — each spawn costs 50–100 ms of startup
- Use `curl` instead: starts in ~5 ms and exits cleanly
- Install curl in the same `RUN` layer as other OS packages
- Use ENV vars for the port so the check stays in sync automatically:
  ```dockerfile
  HEALTHCHECK --interval=60s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:${APP_PORT}/api/health > /dev/null || exit 1
  ```
- Set interval to **60 s or longer** for self-hosted containers — 30 s is unnecessarily aggressive for low-traffic services
- Mirror the same settings in `docker-compose.yml` so local dev matches production behaviour

**CI smoke tests — the Forgejo runner is Docker-in-Docker (DinD):**
- Each job runs inside a container. `docker run -p HOST:CONTAINER` binds the port on the **Docker daemon host**, not on `localhost` inside the job container — `curl http://localhost:PORT` will always get "connection refused" even when the container is healthy.
- **Never use `-p` + `curl localhost` for smoke tests on this runner.**
- Use `docker exec <name> curl -sf http://localhost:PORT/api/health` instead — curl runs inside the app container where its own `localhost` is always reachable:
  ```yaml
  - name: Smoke test
    run: |
      IMAGE=$(echo "${{ steps.meta.outputs.tags }}" | head -1)
      docker rm -f delmo-ci 2>/dev/null || true
      docker run -d --rm --name delmo-ci -e DELMO_DATA_DIR=/tmp "$IMAGE"
      for i in $(seq 1 30); do
        docker exec delmo-ci curl -sf http://localhost:8000/api/health \
          2>/dev/null && echo "Health OK" && break
        [ "$i" -eq 30 ] && { docker logs delmo-ci; docker stop delmo-ci; exit 1; }
        sleep 1
      done
      docker stop delmo-ci
  ```

---

## Local Pre-Push Checks

CI failures are expensive to fix once a PR is open. Mirror all CI gates locally so they fail fast before the push.

**Install the hook once per clone:**
```bash
git config core.hooksPath .githooks
```

**`.githooks/pre-push`** (commit this file; make it executable with `chmod +x .githooks/pre-push`):
```bash
#!/usr/bin/env bash
# Pre-push hook — mirrors CI checks so failures are caught locally.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 1. Python lint (ruff)
python -m ruff check backend/

# 2. Python type-check (mypy)
python -m mypy backend/app/

# 3. Python tests + coverage gate
python -m pytest --cov=backend/app --cov-fail-under=80 -q --tb=short

# 4. Frontend lint (ESLint)
(cd frontend && npm run lint --silent)

# 5. TypeScript type errors
(cd frontend && npm run type-check)

# 6. Frontend security audit (mirrors CI gate)
(cd frontend && npm audit --audit-level=high)

echo "All checks passed — push allowed."
```

**What each check catches:**
- `ruff` — import sorting, line length, common Python anti-patterns
- `mypy` — type errors, missing annotations
- `pytest --cov-fail-under=80` — missing tests on new modules; regression failures
- `ESLint` — frontend parse errors, unused vars
- `tsc` — prop type mismatches, JSX tag errors that ESLint doesn't catch
- `npm audit --audit-level=high` — known CVEs in frontend deps before they reach CI

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
- A rule matches if ALL of its conditions match (AND logic within a rule)
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
