import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.connection import router as connection_router
from app.api.settings import router as settings_router
from app.api.torrents import router as torrents_router
from app.core.database import init_db, seed_defaults

logger = logging.getLogger(__name__)

# Built React SPA lives here after `npm run build`
_STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    logger.info("Starting delmo…")
    await init_db()
    await seed_defaults()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down delmo.")


app = FastAPI(
    title="delmo",
    version="0.1.0",
    description="Automatic torrent data mover via Deluge RPC",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN-only; no auth layer required
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ──────────────────────────────────────────────────────────────
app.include_router(settings_router, prefix="/api")
app.include_router(connection_router, prefix="/api")
app.include_router(torrents_router, prefix="/api")


@app.get("/api/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Static SPA serving ──────────────────────────────────────────────────────
# Only mount when the frontend has been built (i.e. in Docker or after npm build)
if _STATIC_DIR.exists():
    _assets_dir = _STATIC_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:  # noqa: RUF029
        return FileResponse(_STATIC_DIR / "index.html")

else:

    @app.get("/{full_path:path}", include_in_schema=False)
    async def dev_placeholder(full_path: str) -> JSONResponse:  # noqa: RUF029
        return JSONResponse(
            {
                "message": "Frontend not built.",
                "hint": "cd frontend && npm run dev  (or docker compose up --build)",
            }
        )
