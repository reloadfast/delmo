import os
import secrets
from pathlib import Path

DATA_DIR: Path = Path(os.getenv("DELMO_DATA_DIR", "./data"))
DB_PATH: Path = DATA_DIR / "delmo.db"
DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"

# Secret key: read from env or auto-generate (persisted separately if needed)
SECRET_KEY: str = os.getenv("DELMO_SECRET_KEY", "") or secrets.token_hex(32)

# Default settings applied to the DB on first run
DEFAULT_SETTINGS: dict[str, str] = {
    "deluge_host": "",
    "deluge_port": "58846",
    "deluge_username": "",
    "deluge_password": "",
    "polling_interval_seconds": "300",
}
