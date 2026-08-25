"""Scheduled entry point: fetch, calculate, alert, and persist app status."""
from __future__ import annotations
from datetime import datetime, timezone

from common import CONFIG_DIR, DATA_DIR, price_path, read_json, utc_text, write_json
from fetch import load_instruments, update_all
from indicators import calculate
from notify import send
from severity import apply_breadth, individual_level


def _is_stale(as_of: str | None, threshold_minutes: int) -> bool:
    if not as_of or "T" not in as_of:
        return True
    observed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - observed).total_seconds() > threshold_minutes * 60

def run(send_notifications: bool = True) -> dict:
    thresholds = read_json(CONFIG_DIR / "thresholds.json", {})
    ticker_config = read_json(CONFIG_DIR / "tickers.json", {})
    ath_references = {item["ticker"]: item for item in ticker_config.get("ath_reference", [])}
    state = read_json(DATA_DIR / "state.json", {"schema_version": 1, "instruments": {}, "breadth_active": False})
    fetched, fetch_errors = update_all(state)
    rows, gold_indicators = [], None
    for instrument in load_instruments():
        instrument_state = state.setdefault("instruments", {}).setdefault(instrument["ticker"], {})
        indicators = calculate(
            read_json(price_path(instrument["ticker"]), {}),
            thresholds,
            instrument_state.get("trailing_peak_price"),
        )
        if indicators.get("available"):
            instrument_state["trailing_peak_price"] = indicators["trailing_peak_price"]
            instrument_state["peak_initialized_at"] = instrument_state.get("peak_initialized_at", utc_text())
            instrument_state["last_data_timestamp"] = indicators["as_of"]
            indicators["data_is_stale"] = _is_stale(indicators["as_of"], thresholds["stale_data_threshold_minutes"])
        ath = ath_references.get(instrument["ticker"])
        if ath and indicators.get("available"):
            indicators["ath_price"] = ath["ath_price"]
            indicators["ath_date"] = ath["ath_date"]
            indicators["ath_drawdown_pct"] = round(((ath["ath_price"] - indicators["last_price"]) / ath["ath_price"]) * 100, 3)
        base_severity, reasons = individual_level(indicators, thresholds)
        row = {**instrument, "indicators": indicators, "base_severity": base_severity, "severity": base_severity, "reasons": reasons, "breadth_floor_applied": False}; rows.append(row)
        if instrument.get("role") == "gold_confirmation": gold_indicators = indicators
    breadth = apply_breadth(rows, gold_indicators, thresholds)
    status = {"schema_version": 1, "generated_at": utc_text(), "status": "ok" if not fetch_errors else "degraded", "fetch": {"updated": fetched, "errors": fetch_errors}, "breadth": breadth, "instruments": rows}
    notifications = []
    if send_notifications:
        try: notifications = send(status, state)
        except Exception as error: status["notification_error"] = str(error)
    for row in rows: state.setdefault("instruments", {}).setdefault(row["ticker"], {})["previous_base_severity"] = row["base_severity"]
    state["breadth_active"], state["last_run_at"], status["notifications_sent"] = breadth["active"], status["generated_at"], notifications
    write_json(DATA_DIR / "latest_status.json", status); write_json(DATA_DIR / "state.json", state)
    return status

if __name__ == "__main__":
    result = run(); print(f"Guldbevakare run complete: {result['status']}; {len(result['fetch']['updated'])} instruments updated")
