from datetime import date, time

import pandas as pd
import pytest

from app import vintages

DAY = date(2026, 1, 10)


def test_cutoff_is_on_the_day_before_in_uk_time():
    deadline = vintages.cutoff_utc(DAY, time(9, 0))
    assert deadline == pd.Timestamp("2026-01-09T09:00:00Z")  # GMT in January


def test_cutoff_respects_british_summer_time():
    # In July the UK is UTC+1, so 09:00 local is 08:00 UTC.
    deadline = vintages.cutoff_utc(date(2026, 7, 10), time(9, 0))
    assert deadline == pd.Timestamp("2026-07-09T08:00:00Z")


def test_day_window_is_local_midnight_to_midnight():
    start, end = vintages.day_window(DAY)
    assert start == pd.Timestamp("2026-01-10T00:00:00Z")
    assert end == pd.Timestamp("2026-01-11T00:00:00Z")


def test_parse_cutoff():
    assert vintages.parse_cutoff("09:50") == time(9, 50)
    with pytest.raises(ValueError):
        vintages.parse_cutoff("9am")
    with pytest.raises(ValueError):
        vintages.parse_cutoff("25:00")


def test_selects_latest_vintage_at_or_before_cutoff(dataset):
    chosen = vintages.select_decision_vintage(dataset.forecasts, DAY, time(9, 0))
    assert chosen == pd.Timestamp("2026-01-09T07:30:00Z")


def test_cutoff_is_inclusive(dataset):
    chosen = vintages.select_decision_vintage(dataset.forecasts, DAY, time(7, 30))
    assert chosen == pd.Timestamp("2026-01-09T07:30:00Z")


def test_later_cutoff_picks_later_vintage(dataset):
    chosen = vintages.select_decision_vintage(dataset.forecasts, DAY, time(12, 0))
    assert chosen == pd.Timestamp("2026-01-09T11:30:00Z")


def test_no_vintage_before_cutoff_returns_none(dataset):
    assert vintages.select_decision_vintage(dataset.forecasts, DAY, time(1, 0)) is None
    assert vintages.select_decision_vintage(dataset.forecasts, date(2026, 1, 20), time(9, 0)) is None


def test_duplicate_publish_times_keep_last_value(dataset):
    series = vintages.vintage_series(dataset.forecasts, pd.Timestamp("2026-01-09T07:30:00Z"), DAY)
    assert len(series) == 24
    assert set(series["forecast_mw"]) == {11_500}


def test_vintages_covering_excludes_vintages_published_after_the_day(dataset):
    covering = vintages.vintages_covering(dataset.forecasts, DAY)
    assert covering == [
        pd.Timestamp("2026-01-09T02:30:00Z"),
        pd.Timestamp("2026-01-09T07:30:00Z"),
        pd.Timestamp("2026-01-09T11:30:00Z"),
    ]


def test_vintage_series_handles_partial_coverage(dataset):
    series = vintages.vintage_series(dataset.forecasts, pd.Timestamp("2026-01-10T07:30:00Z"), date(2026, 1, 11))
    assert len(series) == 6
