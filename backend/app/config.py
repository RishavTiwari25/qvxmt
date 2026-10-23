"""Static configuration shared by the API, the data loader and the scripts."""

from datetime import date
from pathlib import Path
import os

# Repo root is two levels above backend/app (works in Docker, Vercel and dev).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO_ROOT / "data"))

ACTUALS_FILE = DATA_DIR / "actuals_wind_2026-01.json.gz"
FORECASTS_FILE = DATA_DIR / "windfor_2026-01.json.gz"

# Scope of the pilot: delivery days in January 2026.
FIRST_DAY = date(2026, 1, 1)
LAST_DAY = date(2026, 1, 31)

# Decisions are made on D-1 before the GB day-ahead auction (gate closure 09:50 UK time).
DEFAULT_CUTOFF = "09:00"
LOCAL_TZ = "Europe/London"

# Window of raw data to download. Forecast vintages start a week early so that the
# 1 January decision has history; actuals run one day either side for safety.
ACTUALS_FROM = date(2025, 12, 31)
ACTUALS_TO = date(2026, 2, 1)
FORECASTS_PUBLISHED_FROM = "2025-12-25T00:00Z"
FORECASTS_PUBLISHED_TO = "2026-02-01T00:00Z"
