"""Loads the cached Elexon data into pandas DataFrames.

The repo ships a snapshot of January 2026 (see scripts/fetch_data.py) so the API
starts instantly, including on serverless cold starts. `refresh()` re-pulls live.
"""

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config, elexon


@dataclass(frozen=True)
class Dataset:
    """Tidy, de-duplicated data ready for analysis.

    actuals:   columns [start_time, actual_mw], hourly mean of the half-hourly outturn.
    forecasts: columns [publish_time, start_time, forecast_mw], one row per vintage/target.
    """

    actuals: pd.DataFrame
    forecasts: pd.DataFrame
    source: str  # "cache" or "live"


def actuals_frame(rows: list[dict]) -> pd.DataFrame:
    """Half-hourly FUELHH rows -> hourly mean MW, so they line up with hourly forecasts."""
    df = pd.DataFrame(rows, columns=["startTime", "generation"])
    df = df.rename(columns={"startTime": "start_time", "generation": "actual_mw"})
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["actual_mw"] = pd.to_numeric(df["actual_mw"], errors="coerce")
    df = df.dropna().drop_duplicates("start_time", keep="last")
    hourly = (
        df.set_index("start_time")["actual_mw"]
        .resample("1h")
        .mean()
        .dropna()
        .reset_index()
    )
    return hourly.sort_values("start_time").reset_index(drop=True)


def forecasts_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["publishTime", "startTime", "generation"])
    df = df.rename(
        columns={"publishTime": "publish_time", "startTime": "start_time", "generation": "forecast_mw"}
    )
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["forecast_mw"] = pd.to_numeric(df["forecast_mw"], errors="coerce")
    # Elexon occasionally re-sends a vintage; keep the last copy of each (vintage, target).
    df = df.dropna().drop_duplicates(["publish_time", "start_time"], keep="last")
    return df.sort_values(["publish_time", "start_time"]).reset_index(drop=True)


def read_gz_json(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def write_gz_json(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(rows, fh, separators=(",", ":"))


def load_from_cache() -> Dataset:
    return Dataset(
        actuals=actuals_frame(read_gz_json(config.ACTUALS_FILE)),
        forecasts=forecasts_frame(read_gz_json(config.FORECASTS_FILE)),
        source="cache",
    )


def load_live() -> Dataset:
    actuals = elexon.fetch_wind_actuals(config.ACTUALS_FROM.isoformat(), config.ACTUALS_TO.isoformat())
    forecasts = elexon.fetch_wind_forecasts(config.FORECASTS_PUBLISHED_FROM, config.FORECASTS_PUBLISHED_TO)
    return Dataset(actuals=actuals_frame(actuals), forecasts=forecasts_frame(forecasts), source="live")
