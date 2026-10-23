"""A tiny synthetic dataset for January 2026 so tests run in milliseconds.

Two delivery days (10 and 11 Jan) with hourly actuals; three forecast vintages
published on 9 Jan. The raw rows go through the real parsers in app.data so the
de-duplication and resampling paths are exercised too.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import main
from app.data import Dataset, actuals_frame, forecasts_frame

DAY = date(2026, 1, 10)


def half_hourly_actuals(day: str, mw: float) -> list[dict]:
    rows = []
    for hour in range(24):
        for minute in ("00", "30"):
            rows.append({"startTime": f"{day}T{hour:02d}:{minute}:00Z", "generation": mw})
    return rows


def vintage(publish_time: str, day: str, mw: float, hours=range(24)) -> list[dict]:
    return [
        {"publishTime": publish_time, "startTime": f"{day}T{hour:02d}:00:00Z", "generation": mw}
        for hour in hours
    ]


@pytest.fixture
def raw_actuals() -> list[dict]:
    # 10 Jan: flat 10,000 MW. 11 Jan: flat 5,000 MW. Nothing at all for other days.
    return half_hourly_actuals("2026-01-10", 10_000) + half_hourly_actuals("2026-01-11", 5_000)


@pytest.fixture
def raw_forecasts() -> list[dict]:
    rows = []
    # Oldest vintage, published early on 9 Jan: forecasts 12,000 MW for 10 Jan.
    rows += vintage("2026-01-09T02:30:00Z", "2026-01-10", 12_000)
    # Decision vintage for a 09:00 cutoff: published 07:30 on 9 Jan, 11,000 MW.
    rows += vintage("2026-01-09T07:30:00Z", "2026-01-10", 11_000)
    # The same vintage re-sent by Elexon with a corrected value: must win the de-dup.
    rows += vintage("2026-01-09T07:30:00Z", "2026-01-10", 11_500)
    # Published after the 09:00 cutoff, so it must NOT be picked at 09:00.
    rows += vintage("2026-01-09T11:30:00Z", "2026-01-10", 10_200)
    # A vintage for 11 Jan published on 10 Jan 07:30, but only the first 6 hours exist.
    rows += vintage("2026-01-10T07:30:00Z", "2026-01-11", 6_000, hours=range(6))
    # A vintage for 12 Jan, a day with no actuals at all.
    rows += vintage("2026-01-11T07:30:00Z", "2026-01-12", 8_000)
    return rows


@pytest.fixture
def dataset(raw_actuals, raw_forecasts) -> Dataset:
    return Dataset(actuals=actuals_frame(raw_actuals), forecasts=forecasts_frame(raw_forecasts), source="test")


@pytest.fixture
def client(dataset, monkeypatch) -> TestClient:
    """API client wired to the synthetic dataset instead of the committed snapshot."""
    monkeypatch.setattr(main, "_dataset", dataset)
    main.cached_accuracy.cache_clear()
    return TestClient(main.app)
