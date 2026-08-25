"""Map price indicators to individual and sector-wide severity levels."""
from __future__ import annotations
from typing import Any

def individual_level(indicators: dict[str, Any], thresholds: dict[str, Any]) -> tuple[int, list[str]]:
    if not indicators.get("available"): return 0, ["data_unavailable"]
    trailing, levels = indicators["trailing_drawdown_pct"], thresholds["trailing_levels"]
    confluence = sum([indicators["below_ma50"], indicators["new_swing_low"], indicators["down_streak_days"] >= thresholds["down_streak_min_days"]])
    level, reasons = 0, []
    if trailing >= levels["1"]: level, reasons = 1, ["drawdown_level_1"]
    if trailing >= levels["2"]: level, reasons = 2, ["drawdown_level_2"]
    if trailing >= levels["3"] or confluence >= thresholds["confluence_required_for_level_3"]: level, reasons = 3, ["drawdown_or_confluence_level_3"]
    if trailing >= levels["3"] and confluence >= thresholds["confluence_required_for_level_3"]: level, reasons = 4, ["drawdown_and_confluence_level_4"]
    if trailing >= levels["5"] and confluence >= thresholds["confluence_required_for_level_5"]: level, reasons = 5, ["drawdown_and_confluence_level_5"]
    if level >= 3 and indicators["below_ma100"]:
        level = min(5, level + thresholds["ma100_escalates_by_levels"]); reasons.append("ma100_escalator")
    return level, reasons

def apply_breadth(rows: list[dict[str, Any]], gold_indicators: dict[str, Any] | None, thresholds: dict[str, Any]) -> dict[str, Any]:
    config = thresholds["breadth"]
    declining = [row for row in rows if row["include_in_breadth"] and row["indicators"].get("daily_change_pct") is not None and row["indicators"]["daily_change_pct"] <= -config["daily_drop_threshold_pct"]]
    active = len(declining) >= config["min_count"]
    gold_confirmed = bool(active and gold_indicators and gold_indicators.get("daily_change_pct") is not None and gold_indicators["daily_change_pct"] <= -config["gold_confirmation_threshold_pct"])
    floor = 0
    if active:
        floor = config["floor_level_with_gold_confirmation"] if gold_confirmed else config["floor_level_without_gold_confirmation"]
        for row in rows: row["severity"], row["breadth_floor_applied"] = max(row["severity"], floor), True
    return {"active": active, "confirmed_by_gold": gold_confirmed, "count": len(declining), "declining_tickers": [row["ticker"] for row in declining], "floor_level": floor or None}
