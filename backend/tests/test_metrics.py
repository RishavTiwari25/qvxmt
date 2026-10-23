import math

import pandas as pd
import pytest

from app import metrics
from app.data import actuals_frame


def frame(forecast, actual):
    times = pd.date_range("2026-01-10T00:00Z", periods=len(forecast), freq="1h")
    f = pd.DataFrame({"start_time": times, "forecast_mw": forecast})
    a = pd.DataFrame({"start_time": times, "actual_mw": actual})
    return metrics.join_forecast_actual(f, a)


def test_summary_hand_computed():
    joined = frame([100, 200, 300, 400], [110, 180, 300, 360])
    s = metrics.summary(joined)
    # errors = -10, +20, 0, +40
    assert s["n"] == 4
    assert s["mae"] == pytest.approx(17.5)
    assert s["rmse"] == pytest.approx(math.sqrt((100 + 400 + 0 + 1600) / 4), abs=0.05)
    assert s["bias"] == pytest.approx(12.5)
    assert s["mape"] == pytest.approx((10 / 110 + 20 / 180 + 0 + 40 / 360) / 4 * 100, abs=0.01)
    assert s["forecast_mwh"] == 1000
    assert s["actual_mwh"] == 950


def test_mape_skips_zero_actuals():
    joined = frame([100, 100], [0, 50])
    assert metrics.summary(joined)["mape"] == pytest.approx(100.0)


def test_mape_is_none_when_every_actual_is_zero():
    assert metrics.summary(frame([100], [0]))["mape"] is None


def test_summary_of_empty_frame_is_all_none():
    s = metrics.summary(pd.DataFrame(columns=["start_time", "forecast_mw", "actual_mw", "error_mw"]))
    assert s["n"] == 0 and s["mae"] is None and s["forecast_mwh"] is None


def test_join_drops_hours_without_actuals():
    times = pd.date_range("2026-01-10T00:00Z", periods=3, freq="1h")
    f = pd.DataFrame({"start_time": times, "forecast_mw": [1.0, 2.0, 3.0]})
    a = pd.DataFrame({"start_time": times[:2], "actual_mw": [1.0, 1.0]})
    joined = metrics.join_forecast_actual(f, a)
    assert list(joined["error_mw"]) == [0.0, 1.0]


def test_percentiles_and_margins():
    errors = pd.Series(range(-100, 101))  # symmetric -100..100 step 1
    p = metrics.percentiles(errors, levels=(10, 50, 90))
    assert p["p50"] == 0
    assert p["p90"] == pytest.approx(80)
    margins = {m["coverage"]: m["margin_mw"] for m in metrics.margin_table(errors, coverages=(10, 90))}
    assert margins[90] == pytest.approx(80)
    assert margins[10] == 0  # negative margin floored: under-forecast needs no top-up


def test_margins_on_empty_series_are_none():
    assert metrics.margin_table(pd.Series([], dtype=float), coverages=(90,)) == [{"coverage": 90, "margin_mw": None}]


def test_by_hour_of_day_groups_on_clock_hour():
    joined = frame([10] * 48, [0] * 24 + [20] * 24)  # day 1 error +10, day 2 error -10
    rows = metrics.by_hour_of_day(joined)
    assert len(rows) == 24
    assert all(r["mae"] == 10 and r["bias"] == 0 and r["n"] == 2 for r in rows)


def test_by_lead_time_buckets():
    publish = pd.Timestamp("2026-01-09T00:00Z")
    times = pd.date_range("2026-01-09T01:00Z", periods=30, freq="1h")  # leads 1h..30h
    rows = pd.DataFrame({"publish_time": publish, "start_time": times, "error_mw": [5.0] * 30})
    out = {r["lead_time"]: r for r in metrics.by_lead_time(rows)}
    assert out["0-6h"]["n"] == 5  # leads 1..5 (right-open bins)
    assert out["6-12h"]["n"] == 6
    assert out["24-36h"]["n"] == 7  # leads 24..30
    assert out["0-6h"]["mae"] == 5.0


def test_error_histogram_counts_everything():
    errors = pd.Series([-700.0, -100.0, 0.0, 499.0, 1200.0])
    bins = metrics.error_histogram(errors, bin_width_mw=500)
    assert sum(b["count"] for b in bins) == 5
    assert bins[0]["bin_start"] == -1000.0


def test_actuals_resample_to_hourly_mean():
    rows = [
        {"startTime": "2026-01-10T00:00:00Z", "generation": 100},
        {"startTime": "2026-01-10T00:30:00Z", "generation": 200},
        {"startTime": "2026-01-10T01:00:00Z", "generation": 300},
    ]
    hourly = actuals_frame(rows)
    assert list(hourly["actual_mw"]) == [150.0, 300.0]
