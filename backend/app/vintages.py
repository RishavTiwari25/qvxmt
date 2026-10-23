"""Decision-time forecast selection.

A "vintage" is one WINDFOR publication (identified by its publish_time). For a
delivery day D the desk decides on D-1 before the day-ahead auction, so the only
forecast it can act on is the latest vintage published at or before the cutoff
time on D-1. Everything in this module is plain pandas filtering.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from . import config

LOCAL = ZoneInfo(config.LOCAL_TZ)


def parse_cutoff(value: str) -> time:
    """'HH:MM' -> time; raises ValueError on anything else."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError("cutoff must be HH:MM (24-hour clock)") from exc


def cutoff_utc(day: date, cutoff: time) -> pd.Timestamp:
    """The decision deadline: `cutoff` local time on the day before `day`."""
    local = datetime.combine(day - timedelta(days=1), cutoff, tzinfo=LOCAL)
    return pd.Timestamp(local).tz_convert("UTC")


def day_window(day: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start, end) of the delivery day in UTC (local midnight to midnight)."""
    start = datetime.combine(day, time(0, 0), tzinfo=LOCAL)
    end = start + timedelta(days=1)
    return pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")


def rows_for_day(forecasts: pd.DataFrame, day: date) -> pd.DataFrame:
    """All forecast rows (any vintage) whose target hour falls on `day`."""
    start, end = day_window(day)
    mask = (forecasts["start_time"] >= start) & (forecasts["start_time"] < end)
    return forecasts.loc[mask]


def vintages_covering(forecasts: pd.DataFrame, day: date) -> list[pd.Timestamp]:
    """Publish times of every vintage that forecasts at least one hour of `day`.

    Vintages published after the day has ended are excluded: they still list the
    day's last hours (each run starts at 21:00 the previous evening) but are
    hindcasts, not forecasts.
    """
    _, end = day_window(day)
    rows = rows_for_day(forecasts, day)
    return sorted(rows.loc[rows["publish_time"] < end, "publish_time"].unique())


def select_decision_vintage(forecasts: pd.DataFrame, day: date, cutoff: time) -> pd.Timestamp | None:
    """Latest vintage published at or before the D-1 cutoff that covers `day`.

    Returns None when no usable vintage exists (e.g. data starts after the cutoff).
    """
    deadline = cutoff_utc(day, cutoff)
    candidates = [p for p in vintages_covering(forecasts, day) if p <= deadline]
    return max(candidates) if candidates else None


def vintage_series(forecasts: pd.DataFrame, publish_time: pd.Timestamp, day: date) -> pd.DataFrame:
    """Hourly forecast of one vintage for one day: columns [start_time, forecast_mw]."""
    rows = rows_for_day(forecasts, day)
    rows = rows.loc[rows["publish_time"] == publish_time, ["start_time", "forecast_mw"]]
    return rows.sort_values("start_time").reset_index(drop=True)
