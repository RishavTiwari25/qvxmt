"""Integration checks against the committed January 2026 snapshot in data/.

These pin the data coverage the README reports, so a bad re-fetch is caught.
"""

import pytest

from app import data


@pytest.fixture(scope="module")
def snapshot():
    return data.load_from_cache()


def test_snapshot_coverage(snapshot):
    assert len(snapshot.actuals) == 33 * 24  # 31 Dec .. 1 Feb, hourly
    assert snapshot.forecasts["publish_time"].nunique() == 304
    assert len(snapshot.forecasts) == 304 * 73


def test_every_january_day_has_a_decision_vintage(snapshot):
    from datetime import time

    from app import analysis

    days = [analysis.day_summary(snapshot, d, time(9, 0)) for d in analysis.january_days()]
    assert all(d["publish_time"] is not None and d["n"] == 24 for d in days)
