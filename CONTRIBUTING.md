# Contributing to delmo

## Dev environment

**Requirements:** Python 3.12+, Node 22

```bash
# Clone and install
git clone https://forgejo.moseisley.es/Wind/delmo.git
cd delmo

# Backend
pip install -e ".[dev]"
DELMO_DATA_DIR=/tmp/delmo uvicorn app.main:app --reload --app-dir backend

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # Vite at :5173, proxies /api → :8000
```

## Branches

| Prefix | When to use |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `chore/` | Tooling, CI, deps, version bumps |
| `docs/` | Documentation only |

Branch off `main`; target `main` in PRs.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add tracker-based rule condition
fix: wrap torrent hash in list for core.move_storage
chore: bump version to 0.3.0
docs: update quickstart in README
```

## PR checklist

- [ ] All tests pass: `DELMO_DATA_DIR=/tmp/delmo pytest` and `cd frontend && npm test`
- [ ] Ruff + mypy clean: `ruff check backend && mypy backend`
- [ ] ESLint clean: `cd frontend && npm run lint`
- [ ] Version bumped if the PR ships user-visible changes (patch/minor/major per semver)
- [ ] `pyproject.toml` and `frontend/package.json` versions are in sync

## Running tests

```bash
# Backend — unit + integration
DELMO_DATA_DIR=/tmp/delmo pytest

# Backend — coverage
DELMO_DATA_DIR=/tmp/delmo pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend && npm test
cd frontend && npm run test:coverage
```

## Sensitive data

- Never commit `.env`, secrets, or credentials.
- Deluge credentials are stored in SQLite — never in source or env vars.
- The `deluge_password` field is intentionally omitted from API GET responses.
