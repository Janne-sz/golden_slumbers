"""Incremental Yahoo Finance ingestion for daily and hourly OHLC bars."""
from __future__ import annotations
from datetime import timedelta
from typing import Any
import pandas as pd
import yfinance as yf
from common import CONFIG_DIR, PRICES_DIR, parse_date, price_path, read_json, utc_now, utc_text, write_json

INITIAL_DAILY_LOOKBACK_DAYS = 365 * 3
INITIAL_INTRADAY_LOOKBACK_DAYS = 30

def load_instruments() -> list[dict[str, Any]]:
    config = read_json(CONFIG_DIR / "tickers.json", {})
    return [{**instrument, "kind": kind} for kind in ("watchlist", "reference") for instrument in config.get(kind, [])]

def _rows_from_history(frame: pd.DataFrame, interval: str) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    frame = frame.reset_index()
    time_column = next((name for name in ("Datetime", "Date", "datetime", "date") if name in frame.columns), None)
    if time_column is None or "Close" not in frame.columns:
        raise RuntimeError("Yahoo Finance response lacks a timestamp or Close column")
    rows = []
    for _, item in frame.iterrows():
        timestamp = pd.Timestamp(item[time_column])
        if pd.isna(item["Close"]):
            continue
        row = {"open": float(item.get("Open", item["Close"])), "high": float(item.get("High", item["Close"])), "low": float(item.get("Low", item["Close"])), "close": float(item["Close"]), "volume": int(item.get("Volume", 0) or 0)}
        if interval == "1d":
            row["date"] = timestamp.date().isoformat()
        else:
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            row["timestamp"] = timestamp.tz_convert("UTC").isoformat().replace("+00:00", "Z")
        rows.append(row)
    return rows

def _merge_rows(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    merged = {row[key]: row for row in existing}
    merged.update({row[key]: row for row in incoming})
    return [merged[value] for value in sorted(merged)]

def _start_for_daily(price_file: dict[str, Any]) -> str:
    daily = price_file.get("daily", [])
    return ((utc_now().date() - timedelta(days=INITIAL_DAILY_LOOKBACK_DAYS)) if not daily else (parse_date(daily[-1]["date"]) - timedelta(days=7))).isoformat()

def _start_for_intraday(price_file: dict[str, Any]) -> str:
    intraday = price_file.get("intraday", [])
    # yfinance parses `start` as a date even for hourly intervals. Passing an
    # ISO timestamp (with its `T` and timezone suffix) makes every request fail.
    # Re-fetching the prior calendar day is deliberate: merge-by-timestamp makes
    # this idempotent and gives Yahoo time to finalise the latest hourly bar.
    start = (
        utc_now() - timedelta(days=INITIAL_INTRADAY_LOOKBACK_DAYS)
        if not intraday
        else pd.Timestamp(intraday[-1]["timestamp"]) - timedelta(days=1)
    )
    return pd.Timestamp(start).date().isoformat()

def _download(ticker: str, interval: str, start: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        yahoo_ticker = yf.Ticker(ticker)
        frame = yahoo_ticker.history(start=start, interval=interval, auto_adjust=True, actions=False)
    except Exception as error:
        raise RuntimeError(f"yfinance request failed for {ticker} ({interval}): {error}") from error
    metadata = yahoo_ticker.history_metadata or {}
    previous_close = next((metadata.get(key) for key in ("regularMarketPreviousClose", "previousClose") if metadata.get(key) is not None), None)
    return _rows_from_history(frame, interval), {"previous_close": float(previous_close) if previous_close is not None else None}

def _previous_intraday_date(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    latest_date = rows[-1]["timestamp"][:10]
    return next((row["timestamp"][:10] for row in reversed(rows) if row["timestamp"][:10] != latest_date), None)

def update_instrument(instrument: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    ticker = instrument["ticker"]
    file_path = price_path(ticker)
    stored = read_json(file_path, {"ticker": ticker, "daily": [], "intraday": []})
    daily_new, daily_quote = _download(ticker, "1d", _start_for_daily(stored))
    stored["daily"] = _merge_rows(stored.get("daily", []), daily_new, "date")
    # Persist useful daily data before attempting the less reliable intraday
    # request. A transient Yahoo intraday outage must not blank the dashboard.
    stored["updated_at"] = utc_text()
    write_json(file_path, stored)

    hourly_new, hourly_quote = _download(ticker, "1h", _start_for_intraday(stored))
    stored["intraday"] = _merge_rows(stored.get("intraday", []), hourly_new, "timestamp")[-(24 * 45):]
    quote = hourly_quote if hourly_quote["previous_close"] is not None else daily_quote
    if quote["previous_close"] is not None:
        stored["quote"] = {
            "previous_close": quote["previous_close"],
            "previous_close_date": _previous_intraday_date(stored["intraday"]),
            "as_of_date": stored["intraday"][-1]["timestamp"][:10] if stored["intraday"] else (stored["daily"][-1]["date"] if stored["daily"] else None),
        }
    stored["updated_at"] = utc_text()
    write_json(file_path, stored)
    item_state = state.setdefault("instruments", {}).setdefault(ticker, {})
    item_state.update({"last_checked_at": stored["updated_at"], "last_daily_timestamp": stored["daily"][-1]["date"] if stored["daily"] else None, "last_intraday_timestamp": stored["intraday"][-1]["timestamp"] if stored["intraday"] else None})
    return {"ticker": ticker, "daily_rows": len(stored["daily"]), "intraday_rows": len(stored["intraday"])}

def update_all(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    successes, errors = [], []
    for instrument in load_instruments():
        try:
            successes.append(update_instrument(instrument, state))
        except Exception as error:
            errors.append({"ticker": instrument["ticker"], "message": str(error)})
    return successes, errors
