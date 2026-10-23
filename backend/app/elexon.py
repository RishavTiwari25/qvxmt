"""Thin client for the two Elexon Insights (BMRS) datasets we use.

Both endpoints are public (no API key) and return a JSON array of rows.
"""

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
TIMEOUT = httpx.Timeout(60.0)


def fetch_wind_actuals(date_from: str, date_to: str) -> list[dict]:
    """FUELHH half-hourly outturn by fuel type, filtered to WIND.

    Returns rows with keys startTime (ISO-8601 UTC) and generation (MW).
    """
    params = {"settlementDateFrom": date_from, "settlementDateTo": date_to, "fuelType": "WIND"}
    rows = _get(f"{BASE_URL}/FUELHH/stream", params)
    return [
        {"startTime": r["startTime"], "generation": r["generation"]}
        for r in rows
        if r.get("fuelType") == "WIND"  # belt and braces: the server already filters
    ]


def fetch_wind_forecasts(published_from: str, published_to: str) -> list[dict]:
    """WINDFOR national wind forecast, every vintage published in the window.

    Returns rows with keys publishTime, startTime (ISO-8601 UTC) and generation (MW).
    """
    params = {"publishDateTimeFrom": published_from, "publishDateTimeTo": published_to}
    rows = _get(f"{BASE_URL}/WINDFOR/stream", params)
    return [
        {"publishTime": r["publishTime"], "startTime": r["startTime"], "generation": r["generation"]}
        for r in rows
    ]


def _get(url: str, params: dict) -> list[dict]:
    response = httpx.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"Unexpected response shape from {url}: {type(data).__name__}")
    return data
