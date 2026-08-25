"""ntfy publishing with deduplication owned by persisted state."""
from __future__ import annotations
import os
from typing import Any
import requests
PRIORITY = {3: "low", 4: "default", 5: "urgent"}

def _post(title: str, body: str, level: int) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic: raise RuntimeError("NTFY_TOPIC is not configured")
    response = requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), headers={"Title": title, "Priority": PRIORITY[level], "Tags": "warning" if level < 5 else "rotating_light"}, timeout=15)
    response.raise_for_status()

def send(status: dict[str, Any], state: dict[str, Any]) -> list[str]:
    sent, breadth = [], status["breadth"]
    if breadth["active"] and not state.get("breadth_active", False):
        level, confirmation = breadth["floor_level"], " med guldbekräftelse" if breadth["confirmed_by_gold"] else " utan guldbekräftelse"
        _post("Guldbevakare: sektorlarm", f"{breadth['count']} aktier faller kraftigt{confirmation}: {', '.join(breadth['declining_tickers'])}", level); sent.append("breadth")
    for row in status["instruments"]:
        if row["kind"] != "watchlist" or row.get("breadth_floor_applied") or row["base_severity"] < 3: continue
        previous = state.get("instruments", {}).get(row["ticker"], {}).get("previous_base_severity", 0)
        if row["base_severity"] <= previous: continue
        indicator = row["indicators"]
        _post(f"Guldbevakare: {row['ticker']} nivå {row['base_severity']}", f"{row['name']}: drawdown {indicator['trailing_drawdown_pct']:.1f}%, dagsförändring {indicator['daily_change_pct'] if indicator['daily_change_pct'] is not None else 'saknas'}%.", row["base_severity"]); sent.append(row["ticker"])
    return sent
