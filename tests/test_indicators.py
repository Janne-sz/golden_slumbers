import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from indicators import calculate

THRESHOLDS = {"ma_periods": [50, 100, 200], "peak_backfill_lookback_days": 45, "hourly_move_highlight_threshold_pct": 2, "swing_low_lookback_days": 60}

def bar(timestamp, close):
    return {"timestamp": timestamp, "close": close, "low": close}

def price_data(intraday):
    return {"daily": [{"date": "2026-08-20", "close": 90, "low": 89}, {"date": "2026-08-21", "close": 100, "low": 99}], "intraday": intraday}

def test_intraday_changes_use_one_two_and_four_previous_hourly_bars():
    result = calculate(price_data([bar("2026-08-21T14:30:00Z", 80), bar("2026-08-21T15:30:00Z", 90), bar("2026-08-21T16:30:00Z", 95), bar("2026-08-21T17:30:00Z", 100), bar("2026-08-21T18:30:00Z", 105)]), THRESHOLDS)
    changes = result["intraday_changes"]
    assert changes["1h"] == {"change_pct": 5.0, "reference_timestamp": "2026-08-21T17:30:00Z"}
    assert changes["2h"] == {"change_pct": 10.526, "reference_timestamp": "2026-08-21T16:30:00Z"}
    assert changes["4h"] == {"change_pct": 31.25, "reference_timestamp": "2026-08-21T14:30:00Z"}

def test_intraday_changes_preserve_actual_reference_time_across_market_gap():
    result = calculate(price_data([bar("2026-08-21T18:30:00Z", 100), bar("2026-08-21T19:30:00Z", 101), bar("2026-08-24T13:30:00Z", 102), bar("2026-08-24T14:30:00Z", 103), bar("2026-08-24T15:30:00Z", 104)]), THRESHOLDS)
    assert result["intraday_changes"]["4h"]["reference_timestamp"] == "2026-08-21T18:30:00Z"
