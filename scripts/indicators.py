"""Pure indicator calculations over persisted adjusted OHLC history."""
from __future__ import annotations
from typing import Any

def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None

def _latest_price(daily: list[dict[str, Any]], intraday: list[dict[str, Any]]) -> tuple[float | None, dict[str, Any] | None]:
    if intraday: return float(intraday[-1]["close"]), intraday[-1]
    if daily: return float(daily[-1]["close"]), daily[-1]
    return None, None

def _intraday_changes(intraday: list[dict[str, Any]], price: float) -> dict[str, dict[str, Any]]:
    """Changes from the latest available hourly close to earlier hourly bars."""
    changes: dict[str, dict[str, Any]] = {}
    for hours in (1, 2, 4):
        if len(intraday) <= hours:
            continue
        reference = intraday[-(hours + 1)]
        reference_price = float(reference["close"])
        changes[f"{hours}h"] = {
            "change_pct": round(((price / reference_price) - 1) * 100, 3),
            "reference_timestamp": reference["timestamp"],
        }
    return changes

def calculate(
    price_data: dict[str, Any], thresholds: dict[str, Any], saved_peak: float | None = None
) -> dict[str, Any]:
    daily, intraday = price_data.get("daily", []), price_data.get("intraday", [])
    price, latest_bar = _latest_price(daily, intraday)
    if price is None or not daily: return {"available": False, "reason": "No daily price history"}
    closes = [float(row["close"]) for row in daily]
    latest_date = latest_bar.get("timestamp", latest_bar.get("date", ""))[:10] if latest_bar else ""
    completed = daily[:-1] if daily[-1]["date"] == latest_date else daily
    completed_closes = [float(row["close"]) for row in completed]
    previous_close = completed_closes[-1] if completed_closes else None
    daily_change = ((price / previous_close) - 1) * 100 if previous_close else None
    moving_averages = {str(period): _mean(closes[-period:]) if len(closes) >= period else None for period in thresholds["ma_periods"]}
    # Severity follows the peak established after this monitor was introduced,
    # not an historical all-time high that would leave it permanently alarmed.
    bootstrap_closes = closes[-thresholds["peak_backfill_lookback_days"]:]
    peak = float(saved_peak) if saved_peak is not None else max(bootstrap_closes)
    peak = max(peak, price)
    drawdown = ((peak - price) / peak) * 100
    intraday_changes = _intraday_changes(intraday, price)
    hourly_change = intraday_changes.get("1h", {}).get("change_pct")
    prior_lows = [float(row["low"]) for row in daily if row["date"] < latest_date][-thresholds["swing_low_lookback_days"]:]
    latest_low = float(latest_bar.get("low", price)) if latest_bar else price
    streak = 0
    for index in range(len(completed_closes) - 1, 0, -1):
        if completed_closes[index] < completed_closes[index - 1]: streak += 1
        else: break
    return {"available": True, "as_of": latest_bar.get("timestamp", latest_bar.get("date")), "last_price": round(price, 4), "previous_close": round(previous_close, 4) if previous_close else None, "daily_change_pct": round(daily_change, 3) if daily_change is not None else None, "intraday_changes": intraday_changes, "hourly_change_pct": hourly_change, "hourly_move_highlight": hourly_change is not None and abs(hourly_change) >= thresholds["hourly_move_highlight_threshold_pct"], "trailing_peak_price": round(peak, 4), "trailing_drawdown_pct": round(drawdown, 3), "moving_averages": {key: round(value, 4) if value is not None else None for key, value in moving_averages.items()}, "below_ma50": moving_averages.get("50") is not None and price < moving_averages["50"], "below_ma100": moving_averages.get("100") is not None and price < moving_averages["100"], "below_ma200": moving_averages.get("200") is not None and price < moving_averages["200"], "new_swing_low": bool(prior_lows) and latest_low < min(prior_lows), "down_streak_days": streak, "history_days": len(daily)}
