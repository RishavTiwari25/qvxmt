import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchForecast, fetchVintages, useRemote } from '../api'
import { Card, ErrorState, Loading, TooltipBox } from '../components/ui'
import { fmtEnergy, fmtMW, fmtPct, fmtPublishTime, hourLabel, marginPctOfForecast } from '../format'
import type { ForecastView } from '../types'

const COLORS = { forecast: 'var(--accent)', actual: 'var(--actual)', context: 'var(--context)' }
const MIN_DATE = '2026-01-01'
const MAX_DATE = '2026-01-31'

export function DecisionView({ cutoff }: { cutoff: string }) {
  const [date, setDate] = useState('2026-01-15')
  const [overlays, setOverlays] = useState<string[]>([])

  const forecast = useRemote(() => fetchForecast(date, cutoff), [date, cutoff])
  const vintages = useRemote(() => fetchVintages(date, cutoff), [date, cutoff])

  const toggleOverlay = (publishTime: string) =>
    setOverlays((cur) => (cur.includes(publishTime) ? cur.filter((p) => p !== publishTime) : [...cur, publishTime]))

  return (
    <>
      <div className="controls">
        <label className="field">
          Delivery day
          <input
            type="date"
            value={date}
            min={MIN_DATE}
            max={MAX_DATE}
            onChange={(e) => e.target.value >= MIN_DATE && e.target.value <= MAX_DATE && setDate(e.target.value)}
          />
        </label>
        <span className="hint">
          The desk decides on the day before delivery. The chart shows the latest forecast published at or before{' '}
          <strong>{cutoff}</strong> on D-1, against what the wind fleet actually generated.
        </span>
      </div>

      {forecast.loading && !forecast.data && <Loading />}
      {forecast.error && <ErrorState message={forecast.error} />}
      {forecast.data && (
        <>
          {forecast.loading && <div className="loading-bar" />}
          <div className="grid grid-main">
            <ForecastChart view={forecast.data} overlays={overlays} />
            <SidePanel view={forecast.data} />
          </div>

          <div style={{ height: 16 }} />
          <div className="grid grid-main">
            <Card
              title="Earlier vintages"
              sub="Tick any forecast run published before the cutoff to overlay it in grey on the chart."
            >
              <div className="chips">
                {forecast.data.vintages
                  .filter((v) => v.before_cutoff && v.publish_time !== forecast.data!.publish_time)
                  .map((v) => (
                    <label key={v.publish_time} className={overlays.includes(v.publish_time) ? 'on' : ''}>
                      <input
                        type="checkbox"
                        checked={overlays.includes(v.publish_time)}
                        onChange={() => toggleOverlay(v.publish_time)}
                      />
                      {fmtPublishTime(v.publish_time)}
                    </label>
                  ))}
              </div>
            </Card>
            <Card title="Decision-time vintage" sub="Why this run: it is the newest one the desk could have seen.">
              <dl className="stat-list">
                <dt>Published</dt>
                <dd>{fmtPublishTime(forecast.data.publish_time)} UTC</dd>
                <dt>Cutoff</dt>
                <dd>{fmtPublishTime(forecast.data.cutoff_utc)} UTC</dd>
                <dt>Lead time to 00:00 on D</dt>
                <dd>{forecast.data.lead_hours_to_day_start} h</dd>
                <dt>Hours covered</dt>
                <dd>{forecast.data.points.length} / 24</dd>
              </dl>
            </Card>
          </div>

          <div style={{ height: 16 }} />
          <Card
            title="How the forecast for this day evolved"
            sub="Every run that covered the day, oldest first. The highlighted row is the decision-time vintage."
          >
            {vintages.error && <ErrorState message={vintages.error} />}
            {vintages.data && (
              <div style={{ overflowX: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Published (UTC)</th>
                      <th>Lead to 00:00</th>
                      <th>Hours</th>
                      <th>Forecast</th>
                      <th>Actual</th>
                      <th>Bias</th>
                      <th>MAE</th>
                      <th>MAPE</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vintages.data.map((v) => (
                      <tr key={v.publish_time} className={v.publish_time === forecast.data!.publish_time ? 'highlight' : ''}>
                        <td>{fmtPublishTime(v.publish_time)}</td>
                        <td>{v.lead_hours_to_day_start} h</td>
                        <td>{v.hours_covered}</td>
                        <td>{fmtEnergy(v.forecast_mwh)}</td>
                        <td>{fmtEnergy(v.actual_mwh)}</td>
                        <td>{fmtMW(v.bias, true)}</td>
                        <td>{fmtMW(v.mae)}</td>
                        <td>{fmtPct(v.mape)}</td>
                        <td>
                          {v.publish_time === forecast.data!.publish_time ? (
                            <span className="pill">decision</span>
                          ) : v.before_cutoff ? (
                            <span className="pill muted">before cutoff</span>
                          ) : (
                            <span className="pill muted">after cutoff</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </>
  )
}

function ForecastChart({ view, overlays }: { view: ForecastView; overlays: string[] }) {
  // One row per hour with the decision forecast, the actual and any overlaid vintages keyed by publish time.
  const rows = useMemo(() => {
    const byTime = new Map<string, Record<string, number | null | string>>()
    for (const p of view.points) {
      byTime.set(p.time, { time: p.time, forecast: p.forecast_mw, actual: p.actual_mw })
    }
    for (const v of view.vintages) {
      if (!overlays.includes(v.publish_time)) continue
      for (const p of v.points) {
        const row = byTime.get(p.time) ?? { time: p.time, forecast: null, actual: null }
        row[v.publish_time] = p.forecast_mw
        byTime.set(p.time, row)
      }
    }
    return [...byTime.values()].sort((a, b) => String(a.time).localeCompare(String(b.time)))
  }, [view, overlays])

  return (
    <Card title={`Forecast vs actual, ${view.date}`} sub="National wind generation, MW, hourly. Hover for values.">
      <div className="legend">
        <span>
          <i style={{ background: COLORS.forecast }} />
          Decision-time forecast ({fmtPublishTime(view.publish_time)})
        </span>
        <span>
          <i style={{ background: COLORS.actual }} />
          Actual (FUELHH)
        </span>
        {overlays.length > 0 && (
          <span>
            <i style={{ background: COLORS.context }} />
            Earlier vintages
          </span>
        )}
      </div>
      <div className="chart">
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="time" tickFormatter={hourLabel} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} minTickGap={24} />
            <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} width={40} domain={[0, 'auto']} />
            <Tooltip
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={hourLabel(String(label))}
                    rows={payload.map((p) => ({
                      label: p.dataKey === 'forecast' ? 'Forecast' : p.dataKey === 'actual' ? 'Actual' : `Vintage ${fmtPublishTime(String(p.dataKey))}`,
                      value: fmtMW(p.value as number),
                      color: String(p.color),
                    }))}
                  />
                ) : null
              }
            />
            {overlays.map((p) => (
              <Line key={p} type="monotone" dataKey={p} stroke={COLORS.context} strokeWidth={1.5} dot={false} isAnimationActive={false} />
            ))}
            <Line type="monotone" dataKey="forecast" stroke={COLORS.forecast} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="actual" stroke={COLORS.actual} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function SidePanel({ view }: { view: ForecastView }) {
  const s = view.summary
  const errorMwh = s.forecast_mwh !== null && s.actual_mwh !== null ? s.forecast_mwh - s.actual_mwh : null
  const errorPct = errorMwh !== null && s.actual_mwh ? (errorMwh / s.actual_mwh) * 100 : null
  const hours = view.points.length

  return (
    <Card title="Day summary" sub="Energy over the delivery day and the safety margin the error history supports.">
      <dl className="stat-list">
        <dt>Forecast energy</dt>
        <dd>{fmtEnergy(s.forecast_mwh)}</dd>
        <dt>Actual energy</dt>
        <dd>{fmtEnergy(s.actual_mwh)}</dd>
        <dt>Error (forecast - actual)</dt>
        <dd>
          {errorMwh === null ? '-' : `${errorMwh > 0 ? '+' : ''}${fmtEnergy(errorMwh)}`}
          {errorPct !== null && <span className="hint"> ({errorPct > 0 ? '+' : ''}{fmtPct(errorPct)})</span>}
        </dd>
        <dt>Hourly MAE</dt>
        <dd>{fmtMW(s.mae)}</dd>
        <dt>Hourly bias</dt>
        <dd>{fmtMW(s.bias, true)}</dd>
        <dt>MAPE</dt>
        <dd>{fmtPct(s.mape)}</dd>
      </dl>
      <hr className="divider" />
      <h3>Recommended margin</h3>
      <p className="sub">
        Extra power to buy on top of the forecast so the wind shortfall is covered in X% of hours, from the
        January distribution of (forecast - actual) at this cutoff.
      </p>
      <table>
        <thead>
          <tr>
            <th>Coverage</th>
            <th>Margin</th>
            <th>vs forecast</th>
            <th>Plan on</th>
          </tr>
        </thead>
        <tbody>
          {view.margins.map((m) => (
            <tr key={m.coverage}>
              <td>P{m.coverage}</td>
              <td>{fmtMW(m.margin_mw)}</td>
              <td>{fmtPct(marginPctOfForecast(m.margin_mw, s.forecast_mwh, hours), 0)}</td>
              <td>{m.margin_mw !== null && s.forecast_mwh !== null ? fmtEnergy(s.forecast_mwh - m.margin_mw * hours) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint" style={{ marginBottom: 0 }}>
        "Plan on" = forecast energy minus margin x {hours} h: the wind you can count on; buy the rest of demand from
        other sources.
      </p>
    </Card>
  )
}
