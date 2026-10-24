import { Card } from '../components/ui'

export function About() {
  return (
    <div className="grid" style={{ gap: 16 }}>
      <Card title="Who this is for">
        <div className="prose">
          <p>
            A GB energy supplier's day-ahead desk must buy, on day D-1, the power its customers will use on day D that
            wind will not cover. The GB day-ahead auction closes at 09:50 UK time, so the desk can only use wind
            forecasts published before then. This pilot answers two questions with Elexon's open data: what did the
            latest usable forecast say, and how far can it be trusted?
          </p>
        </div>
      </Card>

      <Card title="Decision-time forecast (the cutoff rule)">
        <div className="prose">
          <p>
            Elexon's <code>WINDFOR</code> dataset republishes the national wind forecast roughly every two hours. Each
            run (a "vintage") is stamped with a <code>publishTime</code> and covers about 72 hours ahead at hourly
            resolution. For delivery day D and a cutoff of <code>HH:MM</code>, the app picks the vintage with the
            latest <code>publishTime</code> that is <strong>at or before HH:MM UK time on D-1</strong> and that forecasts at
            least one hour of D. With the default 09:00 cutoff that is normally the 07:30 run, published 16.5 hours
            before midnight on D. Change the cutoff in the header to see how a later decision (or an earlier one)
            would have fared.
          </p>
          <p>
            Vintages published after the cutoff are listed in the evolution table for context but are never used
            for the decision metrics: the desk could not have seen them.
          </p>
        </div>
      </Card>

      <Card title="Metrics">
        <div className="prose">
          <p>
            Every metric is computed on hourly pairs of (forecast, actual) in MW, with <strong>error = forecast - actual</strong>.
            A positive error means the forecast promised wind that did not show up: the desk is short and must buy
            expensive balancing power. A negative error means surplus wind.
          </p>
          <ul>
            <li>
              <strong>MAE</strong>: mean of |error|. The typical size of a miss.
            </li>
            <li>
              <strong>RMSE</strong>: square root of the mean squared error. Larger than MAE when a few hours are badly wrong.
            </li>
            <li>
              <strong>MAPE</strong>: mean of |error| / actual, as a percentage, over hours where actual &gt; 0.
            </li>
            <li>
              <strong>Bias</strong>: mean signed error. A non-zero bias is a systematic offset the desk can correct for directly.
            </li>
            <li>
              <strong>Percentiles</strong> (P5 ... P95) of the signed error describe the whole distribution, not just the average.
            </li>
            <li>
              <strong>Margin at PX</strong>: the X-th percentile of (forecast - actual), floored at zero. Buying this much more than
              "demand minus forecast" would have covered the wind shortfall in X% of January hours. It is empirical: no normal
              distribution is assumed.
            </li>
            <li>
              <strong>Lead time</strong>: hours between a run's publish time and the target hour. Pooling every run shows how error
              falls as the forecast gets fresher.
            </li>
          </ul>
        </div>
      </Card>

      <Card title="Data">
        <div className="prose">
          <ul>
            <li>
              Actuals: Elexon Insights <code>FUELHH</code> (half-hourly outturn by fuel type), <code>fuelType = WIND</code>,
              1 Jan to 31 Jan 2026. Two half-hours are averaged into each hourly MW value to match the forecast resolution.
              Energy totals are MW x 1 h.
            </li>
            <li>
              Forecasts: Elexon Insights <code>WINDFOR</code>, every vintage published 25 Dec 2025 to 31 Jan 2026 (304 runs,
              22,192 rows), so the 1 January decision has a full history.
            </li>
            <li>
              Both datasets measure transmission-connected wind only; embedded (distribution-connected) wind is outside
              their scope. WINDFOR does not model curtailment, which is one likely reason the forecast ran high in January.
            </li>
            <li>
              The January snapshot is committed to the repository and loaded at start-up. <code>POST /api/refresh</code>
              re-fetches it live from Elexon.
            </li>
          </ul>
          <p>
            Times are shown in UTC, which equals UK local time throughout January. The cutoff is converted with the
            Europe/London zone, so the logic stays correct in summer months.
          </p>
        </div>
      </Card>
    </div>
  )
}
