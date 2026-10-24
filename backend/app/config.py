from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _seed_as_of(meta_path: Path) -> str | None:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8")).get("asOf")
    except (OSError, ValueError):
        return None


@dataclass(frozen=True)
class Config:
    db_path: Path
    seed_path: Path
    seed_meta_path: Path
    as_of: str | None
    admin_email: str
    admin_password: str
    session_hours: int
    cookie_secure: bool
    seed_on_start: bool

    @classmethod
    def from_env(cls) -> "Config":
        seed_path = Path(os.getenv("SEED_PATH", ROOT / "data" / "seed.json"))
        seed_meta_path = Path(os.getenv("SEED_META_PATH", ROOT / "data" / "seed.meta.json"))
        # For the demo the seed dates are shifted to a fixed snapshot time.
        # If AS_OF is not provided, reuse the seed's asOf so scores stay stable.
        # Set AS_OF=now to score against the current clock in production.
        raw_as_of = os.getenv("AS_OF")
        if raw_as_of and raw_as_of.strip().lower() == "now":
            as_of = None
        else:
            as_of = raw_as_of or _seed_as_of(seed_meta_path)
        return cls(
            db_path=Path(os.getenv("APP_DB", ROOT / "data" / "app.db")),
            seed_path=seed_path,
            seed_meta_path=seed_meta_path,
            as_of=as_of,
            admin_email=os.getenv("ADMIN_EMAIL", "admin@example.test"),
            admin_password=os.getenv("ADMIN_PASSWORD", "admin123"),
            session_hours=int(os.getenv("SESSION_HOURS", "12")),
            cookie_secure=_env_bool("COOKIE_SECURE", False),
            seed_on_start=_env_bool("SEED_ON_START", True),
        )
