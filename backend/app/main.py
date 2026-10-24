"""FastAPI application: five read endpoints plus a refresh hook.

Run locally with:  uvicorn app.main:app --reload --port 8000  (from backend/)
"""

from datetime import date, time
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import analysis, config, data, schemas, vintages

app = FastAPI(
    title="Wind Forecast Decision Support",
    version="1.0.0",
    description=(
        "Day-ahead wind forecast vs outturn for GB, January 2026. "
        "Data: Elexon Insights FUELHH (actuals) and WINDFOR (forecast vintages)."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


# ----------------------------------------------------------------------------- data
_dataset: data.Dataset | None = None


def get_dataset() -> data.Dataset:
    """Lazy-load the committed snapshot once per process."""
    global _dataset
    if _dataset is None:
        _dataset = data.load_from_cache()
    return _dataset


@lru_cache(maxsize=32)
def cached_accuracy(cutoff: time) -> dict:
    """The month report is the heaviest call, so memoise it per cutoff (cleared on refresh)."""
    return analysis.accuracy_report(get_dataset(), cutoff)


# ----------------------------------------------------------------------------- validation
def parse_day(value: str) -> date:
    try:
        day = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")
    if not (config.FIRST_DAY <= day <= config.LAST_DAY):
        raise HTTPException(
            status_code=404,
            detail=f"date must be a delivery day between {config.FIRST_DAY} and {config.LAST_DAY}",
        )
    return day


def parse_cutoff(value: str) -> time:
    try:
        return vintages.parse_cutoff(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


DateParam = Query(default="2026-01-15", description="Delivery day, YYYY-MM-DD, within January 2026")
CutoffParam = Query(default=config.DEFAULT_CUTOFF, description="Decision cutoff on D-1, HH:MM UK local time")


# ----------------------------------------------------------------------------- routes
@app.get("/api/health", response_model=schemas.Health)
def health():
    ds = get_dataset()
    return {
        "status": "ok",
        "data_source": ds.source,
        "actual_hours": len(ds.actuals),
        "forecast_rows": len(ds.forecasts),
        "forecast_vintages": int(ds.forecasts["publish_time"].nunique()),
        "default_cutoff": config.DEFAULT_CUTOFF,
    }


@app.get("/api/days", response_model=list[schemas.DaySummary])
def days(cutoff: str = CutoffParam):
    """Every January delivery day with the decision-time vintage and its error metrics."""
    return cached_accuracy(parse_cutoff(cutoff))["days"]


@app.get("/api/forecast", response_model=schemas.ForecastView)
def forecast(date: str = DateParam, cutoff: str = CutoffParam):
    """Decision-time forecast, actuals and all vintages for one delivery day."""
    view = analysis.forecast_view(get_dataset(), parse_day(date), parse_cutoff(cutoff))
    if view is None:
        raise HTTPException(status_code=404, detail="no forecast vintage published before the cutoff for this day")
    return view


@app.get("/api/vintages", response_model=list[schemas.VintageRow])
def vintage_list(date: str = DateParam, cutoff: str = CutoffParam):
    """How the forecast for one day evolved vintage by vintage."""
    rows = analysis.vintage_evolution(get_dataset(), parse_day(date), parse_cutoff(cutoff))
    if not rows:
        raise HTTPException(status_code=404, detail="no forecast vintages cover this day")
    return rows


@app.get("/api/accuracy", response_model=schemas.AccuracyReport, response_model_by_alias=True)
def accuracy(cutoff: str = CutoffParam):
    """Month-level accuracy of the decision-time forecast, with breakdowns and margins."""
    return cached_accuracy(parse_cutoff(cutoff))


@app.post("/api/refresh", response_model=schemas.Health)
def refresh():
    """Re-fetch January 2026 from Elexon into memory (does not rewrite the committed snapshot)."""
    global _dataset
    try:
        _dataset = data.load_live()
    except Exception as exc:  # network / upstream failure
        raise HTTPException(status_code=502, detail=f"Elexon fetch failed: {exc}")
    cached_accuracy.cache_clear()
    return health()


# ---------------------------------------------------------------------------
# Single-process deployment (Vercel): serve the built React bundle from the
# same app so one Python function answers both /api/* and the SPA routes.
# Locally, nginx (docker compose) or the Vite dev server does this instead.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = config.REPO_ROOT / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        candidate = _FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
