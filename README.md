# delmo

Automatic torrent data mover for [Deluge](https://deluge-torrent.org/). Define rules based on file extension or tracker, and delmo moves completed torrents to organised folders — without interrupting seeding.

- **Rule-based moves** — match by file extension (`.mkv`, `.mp3`, …) or tracker domain substring
- **Priority ordering** — first-match wins; lower number = higher priority
- **Idempotent** — skips torrents already at their destination
- **Live activity feed** — WebSocket-powered log updates in real time
- **Zero env-var setup** — all configuration (including Deluge credentials) is managed in the UI and persisted in SQLite

---

## Quick start (docker compose)

```yaml
# docker-compose.yml
services:
  delmo:
    image: talesofthemoon/delmo:latest
    container_name: delmo
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data          # SQLite database
    restart: unless-stopped
```

```bash
docker compose up -d
# Open http://localhost:8000
```

That's it. No environment variables are required.

---

## Configuration

All settings live in **Settings → Deluge Connection**:

| Setting | Description | Default |
|---|---|---|
| Host | Deluge daemon hostname or IP | _(required)_ |
| Port | Deluge RPC port | `58846` |
| Username | Daemon login (see `~/.config/deluge/auth`) | _(blank)_ |
| Password | Daemon login password | _(blank)_ |
| Polling interval | Seconds between rule-engine runs | `300` |

Click **Test Connection** to verify credentials before saving. Changes take effect immediately — no restart needed.

### Environment variables

Only infrastructure-level vars are accepted:

```
DELMO_DATA_DIR=/data    # Directory for the SQLite database (default: /data)
```

---

## Your first rule

1. Go to **Rules** → **New Rule**
2. Fill in:
   - **Name**: `Movies`
   - **Destination**: `/mnt/media/movies`
   - **Condition**: `extension` = `mkv`
3. Click **Save**
4. Click **Preview** to see which torrents would match right now
5. Go to **Settings** → click **Run Now** to trigger an immediate move

Deluge handles the physical file move via `core.move_storage`. Seeding continues uninterrupted.

---

## Rule logic

- Rules are evaluated in **priority order** (lower number = higher priority)
- A rule matches if **any** condition matches (OR logic)
- Each torrent matches only the **first** matching rule
- Torrents already at the destination are **skipped** (idempotency guard)

### Condition types

| Type | Matches when… |
|---|---|
| `extension` | Any file in the torrent has the given extension (e.g. `mkv` or `.mkv`) |
| `tracker` | Any tracker URL's domain contains the value (case-insensitive substring) |

---

## Architecture

```
Browser (LAN)
     │  :8000
     ▼
┌─────────────────────────────────┐
│  delmo Container                │
│  FastAPI + Uvicorn              │
│  /api/*       REST handlers     │
│  /api/ws/logs WebSocket feed    │
│  /*           React SPA         │
│                                 │
│  APScheduler (background)       │
│  Rule Engine + Deluge RPC       │
└───────────────┬─────────────────┘
                │ SQLite /data/delmo.db
                │
                │ TCP RPC :58846
                ▼
        Deluge Daemon (external)
```

Single multi-stage Docker image — no nginx, no second container.

---

## Docker images

| Registry | Image |
|---|---|
| Docker Hub | `talesofthemoon/delmo:latest` |
| GHCR | `ghcr.io/reloadfast/delmo:latest` |

---

## Security notes

delmo is designed for **LAN-only, single-user** deployment — no authentication layer is included.

- Deluge credentials are stored in SQLite and are never returned by the API or written to logs.
- Restrict access to the database file so only the container user can read it:

  ```bash
  chmod 600 ./data/delmo.db
  ```

- Do not expose port `8000` to the public internet.

---

## Development

**Requirements:** Python 3.14, Node 22

```bash
# Backend
pip install -e ".[dev]"
DELMO_DATA_DIR=/tmp/delmo pytest

# Frontend
cd frontend
npm install
npm run dev          # Vite dev server at :5173 (proxies /api → :8000)
npm test             # Vitest

# Backend dev server
uvicorn app.main:app --reload --app-dir backend
```

---

## License

MIT
