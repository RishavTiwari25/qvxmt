# Wind Desk: day-ahead wind forecast support for a GB energy supplier

A pilot web app for a UK utility's day-ahead procurement desk. On day D-1 the desk must
buy the power that wind will not cover on day D, using only the forecast available
before the day-ahead auction closes. This app shows (1) the exact wind forecast the
desk could have acted on, and (2) how accurate that forecast turned out to be, so the
desk can size a safety margin instead of guessing.

Data: Elexon Insights (BMRS) open API, national wind only. Scope: delivery days
1 to 31 January 2026.

**Live demo:** `<deployed URL>` (Vercel)

## What it does

| View | What the desk sees |
|---|---|
| **Decision view** | Pick a delivery day. The chart shows the latest forecast published at or before the cutoff on D-1 (default 09:00 UK) against the actual hourly outturn. Tick earlier runs to overlay them. The side panel gives forecast vs actual energy for the day, the error, and the recommended margin at P80/P90/P95. A table shows how every run for that day evolved. |
| **Accuracy view** | Month KPIs (MAE, RMSE, MAPE, bias, share of hours over-forecast), daily bias and MAE bars, error by hour of day, accuracy by forecast lead time, error histogram with percentiles, a margin table, and a plain-English "what this means for procurement". |
| **Methodology** | The cutoff rule, metric definitions and data notes. |

The cutoff is configurable in the header and in every API call (`?cutoff=HH:MM`).

## Key findings for January 2026 (09:00 cutoff)

- The forecast ran **systematically high**: bias **+1,852 MW**, forecast above actual in
  **85% of hours**. Over the month it promised 9,994 GWh of wind and 8,616 GWh arrived (**+16%**).
- Typical hourly miss: **MAE 2,142 MW**, **RMSE 2,612 MW**, **MAPE 22.4%**.
- Error percentiles (forecast - actual): P10 -549, P50 +1,685, P90 +4,300, P95 +5,307 MW.
- Empirical margin: to cover the shortfall in 90% of hours, buy **~4,300 MW** more than
  "demand minus forecast"; for 95%, **~5,307 MW**.
- Worst day 28 Jan (bias +5,375 MW; 267 GWh forecast vs 138 GWh actual). Best day 19 Jan (MAE 736 MW).
  Only 4 of 31 days were under-forecast (5, 10, 14, 19 Jan).
- Errors are largest in the early hours (05:00: MAE 2,535 MW) and smallest in the evening (21:00: 1,884 MW).
- Fresher is better: MAE falls from 2,381 MW at 48-72 h lead to 1,772 MW at 0-6 h.
  Moving the cutoff from 09:00 to 23:59 on D-1 would cut MAE from 2,142 to 1,936 MW.

## Repository layout

```
.
├── api/index.py              Vercel entry: imports the FastAPI app as one serverless function
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI routes, validation, in-memory dataset + memoised report
│   │   ├── analysis.py       Composes data + vintage selection + metrics into API responses
│   │   ├── vintages.py       Decision-time vintage selection (cutoff on D-1, Europe/London)
│   │   ├── metrics.py        MAE/RMSE/MAPE/bias, percentiles, margins, hour-of-day, lead time
│   │   ├── data.py           Loads the cached snapshot (or live) into tidy pandas frames
│   │   ├── elexon.py         Thin HTTP client for FUELHH and WINDFOR
│   │   ├── schemas.py        Pydantic response models (drive /api/docs)
│   │   └── config.py         Dates, cutoff default, file paths
│   ├── tests/                pytest: vintage selection, metrics, API (synthetic fixture), snapshot
│   ├── Dockerfile
│   └── requirements.txt / requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx           Tabs + shared cutoff control
│   │   ├── pages/            DecisionView, AccuracyView, About
│   │   ├── components/ui.tsx Card, KPI tile, loading/error states, tooltip
│   │   ├── api.ts            Typed fetchers + a small useRemote hook
│   │   ├── format.ts         Formatting helpers (vitest-covered)
│   │   └── types.ts          API response types
│   ├── Dockerfile, nginx.conf
│   └── vite.config.ts        Dev proxy /api -> :8000, vitest config
├── data/
│   ├── actuals_wind_2026-01.json.gz   FUELHH WIND, 31 Dec 2025 - 1 Feb 2026 (1,584 half-hours)
│   └── windfor_2026-01.json.gz        WINDFOR, 304 vintages published 25 Dec - 31 Jan (22,192 rows)
├── scripts/fetch_data.py     Re-downloads and re-compresses the snapshot
├── docs/VIDEO_SCRIPT.md      Demo script
├── docker-compose.yml        backend (:8000) + nginx frontend (:8080)
├── vercel.json               Static frontend + Python function under /api
├── render.yaml               Fallback blueprint for Render
└── requirements.txt          Root deps for the Vercel Python runtime
```

## Running it

### Docker (one command)

```bash
docker compose up --build
# UI:   http://localhost:8080
# API:  http://localhost:8000/api/docs
```

### Dev mode

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
pytest                                                 # 38 tests
```

Frontend (Node 20+):

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, proxies /api to :8000
npm run typecheck && npm test && npm run build
```

### Refreshing the data snapshot

```bash
python scripts/fetch_data.py       # rewrites data/*.json.gz from Elexon
```

`POST /api/refresh` re-fetches into memory at runtime without touching the files
(useful on a long-running server; on Vercel it only lasts for that function instance).

## API

Interactive docs at `/api/docs`. All responses are JSON; bad input returns 422, a
date outside January 2026 or a day with no usable vintage returns 404.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Status, data source (cache/live), row counts |
| `GET /api/days?cutoff=09:00` | All 31 delivery days with the decision vintage and MAE/RMSE/MAPE/bias/energy |
| `GET /api/forecast?date=2026-01-15&cutoff=09:00` | Decision-time forecast per hour with actuals and errors, day summary, P80/90/95 margins, every vintage covering the day (for overlays) |
| `GET /api/vintages?date=2026-01-15&cutoff=09:00` | One row per vintage: publish time, lead time, coverage, metrics, before/after cutoff |
| `GET /api/accuracy?cutoff=09:00` | Month KPIs, per-day table, hour-of-day, percentiles, margin table, histogram, lead-time buckets |
| `POST /api/refresh` | Re-fetch January 2026 from Elexon into memory |

## Methodology

**Decision-time vintage.** WINDFOR is republished roughly every two hours; each run
("vintage") has a `publishTime` and forecasts ~72 hours ahead at hourly resolution,
starting 21:00 the evening before publication. For delivery day D and cutoff `HH:MM`,
the app selects the vintage with the latest `publishTime <= HH:MM Europe/London on D-1`
that covers at least one hour of D. With the default 09:00 (the GB day-ahead auction
gate closes 09:50) this is the 07:30 run, 16.5 h before D starts. Vintages published
after D has ended are excluded from the vintage list: they still contain D's last hours
but are hindcasts.

**Resolution.** FUELHH actuals are half-hourly; WINDFOR is hourly. The two half-hours
in each hour are averaged to an hourly MW value before comparison, so all metrics are
over 24 hourly pairs per day (744 for the month). Energy = MW x 1 h.

**Metrics.** `error = forecast - actual`. Positive means the forecast over-promised
wind and the desk is short (the costly case). MAE = mean |error|; RMSE = sqrt(mean
error^2); MAPE = mean(|error| / actual) over hours with actual > 0; bias = mean error.
Percentiles are of the signed error. **Margin at PX** = max(0, X-th percentile of
error): buying this much more than "demand minus forecast" would have covered the wind
shortfall in X% of January hours. It is purely empirical; no distribution is fitted.

**Lead time.** For the lead-time chart every (vintage, target hour) pair in January is
used, bucketed by `startTime - publishTime`, so it shows how error falls as the forecast
gets fresher independent of the cutoff.

## Decisions and assumptions

- **Why a committed data snapshot.** Elexon is fast but the app should not depend on
  it at request time, especially on serverless cold starts. `scripts/fetch_data.py`
  pulls the raw rows once and stores them gzipped (125 KB in total). Only the fields
  the app uses are kept.
- **Why hourly, not per settlement period.** The forecast is hourly, so comparing at
  half-hourly resolution would duplicate each forecast value; averaging actuals to
  hourly is the honest comparison.
- **Why the vintage must cover D.** In this dataset every vintage covers 72 h, so the
  latest run before the cutoff always does, but the rule is written defensively.
- **Duplicate publishes.** If Elexon re-sends a vintage, the last copy of each
  `(publishTime, startTime)` wins.
- **Margins floored at zero.** A negative percentile means the forecast was low that
  often; no top-up is needed for shortfall protection.
- **Month-wide margins on the Decision view.** A single day has too few hours to
  estimate a P95; the daily panel therefore quotes the January-wide margins.
- **Time zone.** The cutoff is converted from Europe/London so the logic is right in
  summer too; in January UK time equals UTC, so the UI simply labels times UTC.
- **No router, no state library.** Three tabs and one shared `cutoff` state are enough;
  `useState` keeps the code easy to follow.
- **Styling.** Plain CSS with custom properties; Recharts for charts. Series colours
  follow a fixed scheme (blue forecast, orange actual, grey earlier vintages,
  red/blue for over/under-forecast) checked for colour-vision-deficiency separation.

## Data coverage and known limitations

- Actuals: 1,584 half-hours (33 days x 48, 31 Dec 2025 to 1 Feb 2026), no gaps.
  Forecasts: 304 vintages x 73 hours, no gaps; the earliest vintage is 25 Dec 2025 02:30,
  so every January day has a decision vintage at any cutoff.
- Both datasets cover transmission-connected wind only; embedded wind is out of scope.
  WINDFOR does not model curtailment, which is one plausible cause of the persistent
  over-forecast; the app reports the bias, it does not explain it.
- The margin recommendation is a backward-looking empirical percentile over one month.
  It is a sizing aid, not a risk model: a longer history and conditioning on forecast
  level or weather regime would make it sturdier.
- The lead-time chart's 48-72 h bucket is thinner (fewer hours have a run that old).
- Single-user, read-only pilot: no auth, no persistence beyond the snapshot.
- Vercel's Python function cold start (pandas import + snapshot load) is roughly 2-3 s
  on the first request; subsequent requests are served from a warm instance.

## Testing

- `backend/tests`: 38 pytest tests. A synthetic January fixture (two days, five vintages,
  including a duplicated publish, a partial-coverage vintage, a vintage with no actuals
  and a day with no vintage before the cutoff) drives the selection, metric and API tests.
  `test_snapshot.py` pins the committed data's coverage.
- `frontend`: `tsc -b` strict typecheck, 5 vitest tests on the formatting helpers, `vite build`.

## Deployment

**Vercel** (`vercel.json`): the frontend is built from `frontend/` and served statically;
`api/index.py` is deployed as a Python 3.12 serverless function and `/api/*` is rewritten
to it. From the repo root:

```bash
npm i -g vercel
vercel          # preview
vercel --prod   # production; paste the URL into "Live demo" above
```

**Render** fallback (`render.yaml`): a Docker web service for the API and a static site
for the UI with `/api/*` rewritten to the API.

## AI tools used

Claude Code (Anthropic) was used as a pair-programmer throughout: scaffolding the
FastAPI and React code, drafting tests and this README, and reviewing code for bugs.
The problem framing, data-handling decisions (cutoff rule, hourly resampling, margin
definition), validation of the numbers against the raw Elexon responses, and the final
review of every file were done by the author.
