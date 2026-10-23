"""Forecast error metrics. Pure functions over small pandas frames.

Convention used everywhere: error = forecast - actual (MW).
Positive error  -> the forecast was too high (over-forecast). The desk bought too
                   little thermal power and is short on the day: the costly case.
Negative error  -> under-forecast; more wind arrived than planned (surplus).
"""

import math

import numpy as np
import pandas as pd

HOURS_PER_ROW = 1.0  # forecasts and resampled actuals are hourly, so MW x 1h = MWh


def join_forecast_actual(forecast: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Inner-join on start_time and add the error column. Hours without an actual drop out."""
    joined = forecast.merge(actuals, on="start_time", how="inner")
    joined["error_mw"] = joined["forecast_mw"] - joined["actual_mw"]
    return joined.sort_values("start_time").reset_index(drop=True)


def summary(joined: pd.DataFrame) -> dict:
    """MAE, RMSE, MAPE, mean bias and energy totals for a set of matched hours."""
    n = len(joined)
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "mape": None, "bias": None,
                "forecast_mwh": None, "actual_mwh": None}
    err = joined["error_mw"]
    positive_actual = joined["actual_mw"] > 0  # guard against divide-by-zero
    mape = (
        float((err[positive_actual].abs() / joined.loc[positive_actual, "actual_mw"]).mean() * 100)
        if positive_actual.any()
        else None
    )
    return {
        "n": int(n),
        "mae": _r(err.abs().mean()),
        "rmse": _r(math.sqrt((err ** 2).mean())),
        "mape": _r(mape, 2),
        "bias": _r(err.mean()),
        "forecast_mwh": _r(joined["forecast_mw"].sum() * HOURS_PER_ROW),
        "actual_mwh": _r(joined["actual_mw"].sum() * HOURS_PER_ROW),
    }


def percentiles(errors: pd.Series, levels=(10, 50, 90)) -> dict:
    """Percentiles of the signed error distribution, keyed 'p10', 'p50', ..."""
    if errors.empty:
        return {f"p{p}": None for p in levels}
    return {f"p{p}": _r(np.percentile(errors, p)) for p in levels}


def margin_table(errors: pd.Series, coverages=(50, 80, 90, 95, 99)) -> list[dict]:
    """Empirical safety margin: to be covered X% of hours, assume the forecast is
    too high by the X-th percentile of (forecast - actual) and buy that much more.

    Negative margins are floored at zero: if the forecast is low that often, no
    extra purchase is needed to protect against a shortfall.
    """
    rows = []
    for cov in coverages:
        if errors.empty:
            rows.append({"coverage": cov, "margin_mw": None})
            continue
        margin = max(0.0, float(np.percentile(errors, cov)))
        rows.append({"coverage": cov, "margin_mw": _r(margin)})
    return rows


def by_hour_of_day(joined: pd.DataFrame) -> list[dict]:
    """MAE and bias for each clock hour 0-23 (UTC == UK local time in January)."""
    if joined.empty:
        return []
    hours = joined["start_time"].dt.hour
    grouped = joined.groupby(hours)["error_mw"]
    return [
        {"hour": int(hour), "mae": _r(g.abs().mean()), "bias": _r(g.mean()), "n": int(len(g))}
        for hour, g in grouped
    ]


def error_histogram(errors: pd.Series, bin_width_mw: float = 500.0) -> list[dict]:
    """Counts of hours per error bin, for the distribution chart."""
    if errors.empty:
        return []
    lo = math.floor(errors.min() / bin_width_mw) * bin_width_mw
    hi = math.ceil(errors.max() / bin_width_mw) * bin_width_mw + bin_width_mw
    edges = np.arange(lo, hi + bin_width_mw, bin_width_mw)
    counts, _ = np.histogram(errors, bins=edges)
    return [
        {"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]), "count": int(c)}
        for i, c in enumerate(counts)
    ]


def by_lead_time(all_rows: pd.DataFrame, edges=(0, 6, 12, 24, 36, 48, 72)) -> list[dict]:
    """How accuracy changes with forecast age.

    `all_rows` holds every (vintage, target hour) pair with matched actuals and
    columns publish_time, start_time, error_mw. Lead time is target minus publish.
    """
    if all_rows.empty:
        return []
    lead_h = (all_rows["start_time"] - all_rows["publish_time"]) / pd.Timedelta(hours=1)
    labels = [f"{edges[i]}-{edges[i + 1]}h" for i in range(len(edges) - 1)]
    bucket = pd.cut(lead_h, bins=list(edges), labels=labels, right=False)
    return [
        {"lead_time": str(label), "mae": _r(g.abs().mean()), "bias": _r(g.mean()), "n": int(len(g))}
        for label, g in all_rows.groupby(bucket, observed=True)["error_mw"]
    ]


def _r(value, ndigits: int = 1):
    """Round for JSON, turning NaN into None."""
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) else round(value, ndigits)
