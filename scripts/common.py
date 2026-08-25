"""Small, dependency-free helpers shared by the scheduled job."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
PRICES_DIR = DATA_DIR / "prices"

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")

def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

def ticker_key(ticker: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in ticker)

def price_path(ticker: str) -> Path:
    return PRICES_DIR / f"{ticker_key(ticker)}.json"

def parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])
