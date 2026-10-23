"""Composes the data, vintage selection and metrics into API-shaped results."""

from datetime import date, time, timedelta

import pandas as pd

from . import config, metrics, vintages
from .data import Dataset


def january_days() -> list[date]:
    n = (config.LAST_DAY - config.FIRST_DAY).days + 1
    return [config.FIRST_DAY + timedelta(days=i) for i in range(n)]


def decision_errors(ds: Dataset, day: date, cutoff: time) -> pd.DataFrame | None:
    """Decision-time forecast joined with actuals for one day, or None without a vintage."""
    publish_time = vintages.select_decision_vintage(ds.forecasts, day, cutoff)
    if publish_time is None:
        return None
    series = vintages.vintage_series(ds.forecasts, publish_time, day)
    joined = metrics.join_forecast_actual(series, ds.actuals)
    joined["publish_time"] = publish_time
    return joined


def day_summary(ds: Dataset, day: date, cutoff: time) -> dict:
    publish_time = vintages.select_decision_vintage(ds.forecasts, day, cutoff)
    if publish_time is None:
        return {"date": day.isoformat(), "publish_time": None, **metrics.summary(pd.DataFrame())}
    series = vintages.vintage_series(ds.forecasts, publish_time, day)
    joined = metrics.join_forecast_actual(series, ds.actuals)
    return {"date": day.isoformat(), "publish_time": publish_time.isoformat(), **metrics.summary(joined)}


def all_decision_errors(ds: Dataset, cutoff: time) -> pd.DataFrame:
    """Decision-time errors for every January day stacked into one frame."""
    frames = [f for f in (decision_errors(ds, d, cutoff) for d in january_days()) if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=["start_time", "forecast_mw", "actual_mw", "error_mw", "publish_time"])
    return pd.concat(frames, ignore_index=True)


def forecast_view(ds: Dataset, day: date, cutoff: time) -> dict | None:
    """Everything the Decision view needs for one day."""
    publish_time = vintages.select_decision_vintage(ds.forecasts, day, cutoff)
    if publish_time is None:
        return None
    deadline = vintages.cutoff_utc(day, cutoff)
    start, end = vintages.day_window(day)

    series = vintages.vintage_series(ds.forecasts, publish_time, day)
    joined = metrics.join_forecast_actual(series, ds.actuals)

    actuals = ds.actuals[(ds.actuals["start_time"] >= start) & (ds.actuals["start_time"] < end)]
    actual_by_time = dict(zip(actuals["start_time"], actuals["actual_mw"]))

    points = []
    for t, f in zip(series["start_time"], series["forecast_mw"]):
        actual = actual_by_time.get(t)
        points.append(
            {
                "time": t.isoformat(),
                "forecast_mw": float(f),
                "actual_mw": None if actual is None else float(actual),
                "error_mw": None if actual is None else round(float(f) - float(actual), 1),
            }
        )

    all_vintages = []
    for p in vintages.vintages_covering(ds.forecasts, day):
        s = vintages.vintage_series(ds.forecasts, p, day)
        all_vintages.append(
            {
                "publish_time": p.isoformat(),
                "before_cutoff": bool(p <= deadline),
                "points": [
                    {"time": t.isoformat(), "forecast_mw": float(f)}
                    for t, f in zip(s["start_time"], s["forecast_mw"])
                ],
            }
        )

    month_errors = all_decision_errors(ds, cutoff)["error_mw"]
    return {
        "date": day.isoformat(),
        "cutoff": cutoff.strftime("%H:%M"),
        "cutoff_utc": deadline.isoformat(),
        "publish_time": publish_time.isoformat(),
        "lead_hours_to_day_start": round((start - publish_time) / pd.Timedelta(hours=1), 1),
        "points": points,
        "summary": metrics.summary(joined),
        "margins": metrics.margin_table(month_errors, coverages=(80, 90, 95)),
        "vintages": all_vintages,
    }


def vintage_evolution(ds: Dataset, day: date, cutoff: time) -> list[dict]:
    """One row per vintage covering the day: when it was published and how good it was."""
    deadline = vintages.cutoff_utc(day, cutoff)
    start, _ = vintages.day_window(day)
    rows = []
    for publish_time in vintages.vintages_covering(ds.forecasts, day):
        series = vintages.vintage_series(ds.forecasts, publish_time, day)
        joined = metrics.join_forecast_actual(series, ds.actuals)
        rows.append(
            {
                "publish_time": publish_time.isoformat(),
                "lead_hours_to_day_start": round((start - publish_time) / pd.Timedelta(hours=1), 1),
                "before_cutoff": bool(publish_time <= deadline),
                "hours_covered": int(len(series)),
                **metrics.summary(joined),
            }
        )
    return rows


def accuracy_report(ds: Dataset, cutoff: time) -> dict:
    """Everything the Accuracy view needs."""
    joined = all_decision_errors(ds, cutoff)
    errors = joined["error_mw"]

    # Lead-time analysis uses *every* vintage for January target hours, not just the decision one.
    start, _ = vintages.day_window(config.FIRST_DAY)
    _, end = vintages.day_window(config.LAST_DAY)
    jan_rows = ds.forecasts[(ds.forecasts["start_time"] >= start) & (ds.forecasts["start_time"] < end)]
    lead_rows = metrics.join_forecast_actual(jan_rows, ds.actuals)

    return {
        "cutoff": cutoff.strftime("%H:%M"),
        "period": {"from": config.FIRST_DAY.isoformat(), "to": config.LAST_DAY.isoformat()},
        "month": metrics.summary(joined),
        "days": [day_summary(ds, d, cutoff) for d in january_days()],
        "by_hour": metrics.by_hour_of_day(joined),
        "percentiles": metrics.percentiles(errors, levels=(5, 10, 25, 50, 75, 90, 95)),
        "margins": metrics.margin_table(errors),
        "histogram": metrics.error_histogram(errors),
        "by_lead_time": metrics.by_lead_time(lead_rows),
        "over_forecast_share_pct": metrics._r((errors > 0).mean() * 100) if len(errors) else None,
    }
