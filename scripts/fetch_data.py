"""Download the January 2026 wind actuals and forecast vintages from Elexon and
store them as compressed JSON in data/ so the API (and Vercel cold starts) never
need to call Elexon at request time.

Usage:  python scripts/fetch_data.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config, elexon  # noqa: E402  (import after sys.path tweak)
from app.data import write_gz_json  # noqa: E402


def main() -> None:
    print(f"Fetching FUELHH WIND actuals {config.ACTUALS_FROM} .. {config.ACTUALS_TO}")
    actuals = elexon.fetch_wind_actuals(config.ACTUALS_FROM.isoformat(), config.ACTUALS_TO.isoformat())
    write_gz_json(config.ACTUALS_FILE, actuals)
    print(f"  {len(actuals)} rows -> {config.ACTUALS_FILE.relative_to(ROOT)}")

    print(f"Fetching WINDFOR vintages published {config.FORECASTS_PUBLISHED_FROM} .. {config.FORECASTS_PUBLISHED_TO}")
    forecasts = elexon.fetch_wind_forecasts(config.FORECASTS_PUBLISHED_FROM, config.FORECASTS_PUBLISHED_TO)
    write_gz_json(config.FORECASTS_FILE, forecasts)
    vintages = len({r["publishTime"] for r in forecasts})
    print(f"  {len(forecasts)} rows in {vintages} vintages -> {config.FORECASTS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
