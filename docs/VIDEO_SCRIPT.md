# Demo video script (two parts, 10 minutes total)

Record in one unlisted YouTube video with a visible chapter break. Have these open before
you start: the deployed app (Decision view, 15 Jan selected, cutoff 09:00), `/api/docs`
in a second tab, the repo in VS Code with `backend/app/vintages.py` open, and a terminal
in the repo root. Speak slowly; the numbers below are the real January 2026 results, so
read them off the screen rather than from memory.

---

## Part 1: customer pitch (target 4:30, hard stop 5:00)

**[0:00] Open on the Decision view, 15 Jan 2026.**

> "Good morning. Your day-ahead desk has one hard question every morning: how much
> thermal power do we buy for tomorrow on top of the wind we expect? Buy too little and
> you pay balancing prices; buy too much and you've wasted money. This pilot answers that
> question with Elexon's open data, for every delivery day in January 2026."

**[0:30] Point at the header.** Hover the cutoff box.

> "Everything on screen respects one rule: the desk decides before the day-ahead auction
> closes at 09:50, so we only ever show the forecast that was actually published before
> the cutoff on the day before. Default is 09:00; you can change it."

**[0:50] The chart.** Trace the blue and orange lines with the cursor; hover at 11:00.

> "Blue is the forecast the desk could act on for 15 January, published at 07:30 on the
> 14th, sixteen and a half hours before the day started. Orange is what the wind fleet
> actually produced. At 11:00 the forecast said 11,578 MW; 9,766 showed up."

**[1:15] Side panel.** Point at each line.

> "For the whole day: 278.6 GWh forecast, 253.6 GWh delivered, so a 25 GWh shortfall,
> about ten percent. The margin table turns that into a buying rule. If you want to be
> covered nine hours out of ten, add 4,300 MW to your thermal purchase on top of
> 'demand minus forecast'. At P95 it is 5,307 MW."

**[1:50] Earlier vintages.** Scroll down, tick `13 Jan 02:30` and `14 Jan 04:30`, scroll back up.

> "You can also see how the forecast drifted. The grey lines are older runs. On this day
> the forecast came down with each run, and it was still too high."

**[2:15] Scroll to the evolution table.**

> "This table is the same story in numbers: every run that covered the day, when it was
> published, its lead time, and how far off it was. The highlighted row is the one the
> desk could use."

**[2:35] Click 'Accuracy view'.** Pause on the KPI tiles.

> "Now the month as a whole, 744 hours. Mean absolute error 2,142 MW. Root mean square
> error 2,612 MW. MAPE 22 percent. And the number that matters most: a bias of plus
> 1,852 MW. The forecast was high in 85 percent of hours. Over January it promised
> 9,994 gigawatt-hours of wind and 8,616 arrived, sixteen percent less."

**[3:10] The interpretation card.** Read the first sentence, then paraphrase.

> "In plain terms: a desk that bought exactly demand minus forecast would have been
> short most days of the month."

**[3:25] Daily bias chart.** Hover 28 Jan, then 11 and 12 Jan.

> "Red days are shortfalls. The worst was 28 January: forecast 267 GWh, actual 138, the
> forecast was almost double reality. 11 and 12 January were both nearly 5,000 MW high
> every hour. Only four days in the month were blue, meaning more wind than forecast."

**[3:50] Hour-of-day and lead-time charts.** Hover 05:00; then the lead-time line.

> "Two things you can act on. First, the error is worst overnight, 2,535 MW at 05:00,
> and smallest in the evening. Second, the forecast gets better as it gets fresher:
> error drops from about 2,380 MW two days out to 1,770 MW within six hours. If the
> desk re-checked the latest run just before gate closure instead of at 09:00, the
> average error would fall from 2,142 to around 1,940 MW."

**[4:20] Histogram and margin table.**

> "This is the distribution behind the margin recommendation. No assumptions, just
> what January did. The desk picks the coverage it is comfortable with and reads off
> the margin: 3,383 MW at P80, 4,300 at P90, 5,307 at P95."

**[4:40] Close.**

> "So the pilot gives your desk the right forecast at the right moment, and a quantified,
> defensible margin to put around it. Next steps would be a longer history, and
> conditioning the margin on forecast level or weather regime. Thank you."

---

## Part 2: tech-lead walkthrough (target 4:30, hard stop 5:00)

**[0:00] Terminal, `tree`-style view of the repo (or the README layout block).**

> "Two services. A Python FastAPI backend under `backend/app`, a React + TypeScript
> frontend under `frontend`, both containerised, with `docker compose up` running the
> pair locally, and `vercel.json` deploying the same code as a static site plus one
> Python serverless function."

**[0:30] Data pipeline. Open `scripts/fetch_data.py`, then `backend/app/data.py`.**

> "Data comes from two Elexon datasets: FUELHH for half-hourly actuals filtered to WIND,
> and WINDFOR for every forecast run. The fetch script pulls January once and commits
> it gzipped, 125 kilobytes total, so cold starts never call Elexon. `data.py` turns the
> raw rows into two tidy pandas frames. Note the two deliberate steps: actuals are
> resampled from half-hourly to hourly means because the forecast is hourly, and
> duplicate `(publishTime, startTime)` rows keep the last copy."

**[1:15] Core logic. Open `backend/app/vintages.py`, scroll to `select_decision_vintage`.**

> "This is the business rule in six lines. Build the deadline as cutoff local time on
> D-1 using the Europe/London zone, list every vintage that covers at least one hour of
> D, keep those published at or before the deadline, take the latest. If there is none,
> return `None` and the API answers 404. Vintages published after the day has ended are
> excluded because they are hindcasts, not forecasts."

**[1:50] Metrics. Open `backend/app/metrics.py`.**

> "Metrics are pure functions over a joined frame with `error = forecast - actual`.
> `summary` gives MAE, RMSE, MAPE with a divide-by-zero guard, bias and energy totals.
> `margin_table` is the empirical percentile floored at zero. `by_lead_time` bins
> `startTime - publishTime` so we can show accuracy versus forecast age using every run,
> not just the decision one. Everything rounds through one helper that also maps NaN
> to null for JSON."

**[2:25] API. Switch to the `/api/docs` tab.**

> "Five read endpoints plus a refresh. `/api/forecast` and `/api/vintages` take a date
> and a cutoff; `/api/accuracy` and `/api/days` take just the cutoff. Pydantic models
> document the shapes. Validation is explicit: malformed input is 422, a day outside
> January or without a usable vintage is 404. The month report is memoised per cutoff
> because it is the one heavy call; it still takes well under a second."

**[2:55] Tests. Terminal: `cd backend && pytest -q`.**

> "Thirty-eight tests. The fixture in `conftest.py` is a synthetic two-day January with
> five vintages designed to hit the edge cases: a duplicated publish, a run published
> after the cutoff, a partial-coverage run, a run with no actuals, and days with no
> vintage at all. API tests use FastAPI's TestClient against that fixture, so they run
> in two seconds, and `test_snapshot.py` pins the committed data so a bad re-fetch is
> caught."

**[3:30] Frontend. Open `frontend/src/pages/DecisionView.tsx`, then `api.ts`.**

> "The frontend is deliberately small: three tab components and one shared `cutoff`
> state in `App.tsx`. `api.ts` has typed fetchers and a `useRemote` hook that keeps the
> last good data while reloading, so charts do not flash. Charts are Recharts with a
> fixed colour scheme: blue forecast, orange actual, grey for earlier runs, red and
> blue for over- and under-forecast. Formatting helpers are covered by vitest; the
> build is strict TypeScript."

**[4:05] Docker and deployment. Open `docker-compose.yml`, then `vercel.json`.**

> "Compose runs the API on 8000 and an nginx container on 8080 that serves the built
> bundle and proxies `/api` to the backend, with a health check gating start-up. On
> Vercel the same bundle is served statically and `api/index.py` imports the FastAPI
> app as a Python function; rewrites send `/api/*` to it and everything else to
> `index.html`. `render.yaml` is a fallback for Render."

**[4:35] Close on the README.**

> "The README has the layout, run commands, API table, methodology, every assumption I
> made and the known limitations. I used Claude Code as a pair-programmer for
> scaffolding and review; the data decisions and validation against the raw Elexon
> responses are mine. Happy to walk through any file in more detail."

---

## Numbers cheat-sheet (09:00 cutoff unless stated)

| Item | Value |
|---|---|
| Hours compared | 744 (31 days x 24) |
| MAE / RMSE / MAPE | 2,142 MW / 2,612 MW / 22.4% |
| Bias | +1,852 MW; 85% of hours over-forecast |
| Energy | 9,994 GWh forecast vs 8,616 GWh actual (+16%) |
| Percentiles P10 / P50 / P90 / P95 | -549 / +1,685 / +4,300 / +5,307 MW |
| Margin P80 / P90 / P95 | 3,383 / 4,300 / 5,307 MW |
| 15 Jan | vintage 14 Jan 07:30, lead 16.5 h, 278.6 vs 253.6 GWh, MAE 1,042 MW, MAPE 11.2% |
| Worst day | 28 Jan, bias +5,375 MW, 267 vs 138 GWh |
| Best day | 19 Jan, MAE 736 MW (under-forecast by 730 MW) |
| Under-forecast days | 5, 10, 14, 19 Jan |
| Worst / best hour | 05:00 MAE 2,535 MW / 21:00 MAE 1,884 MW |
| Lead time MAE | 0-6 h 1,772; 12-24 h 2,002; 24-36 h 2,136; 48-72 h 2,381 MW |
| Cutoff 23:59 instead of 09:00 | MAE 1,936 MW, bias +1,714 MW, P90 margin 3,897 MW |
| Data | 1,584 half-hour actuals; 304 vintages x 73 h = 22,192 forecast rows |
