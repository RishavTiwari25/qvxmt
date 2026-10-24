import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchAccuracy, useRemote } from '../api'
import { Card, ErrorState, Kpi, Loading, TooltipBox } from '../components/ui'
import { fmtEnergy, fmtMW, fmtPct, marginPctOfForecast, shortDate } from '../format'
import type { AccuracyReport } from '../types'

const OVER = 'var(--over)'
const UNDER = 'var(--under)'
const ACCENT = 'var(--accent)'

const axisProps = { tick: { fontSize: 12 }, tickLine: false, axisLine: false } as const
const kFormat = (v: number) => `${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}k`

export function AccuracyView({ cutoff }: { cutoff: string }) {
  const report = useRemote(() => fetchAccuracy(cutoff), [cutoff])

  if (report.loading && !report.data) return <Loading text="Computing January metrics..." />
  if (report.error) return <ErrorState message={report.error} />
  if (!report.data) return null
  const r = report.data
  const m = r.month

  return (
    <>
      {report.loading && <div className="loading-bar" />}
      <p className="hint" style={{ marginTop: 0 }}>
        Decision-time forecast (latest run published by <strong>{cutoff}</strong> on D-1) against hourly actuals,
        {` ${r.period.from} to ${r.period.to}`}, {m.n} hours.
      </p>

      <div className="kpis">
        <Kpi label="MAE" value={fmtMW(m.mae)} note="mean absolute hourly error" />
        <Kpi label="RMSE" value={fmtMW(m.rmse)} note="penalises the big misses" />
        <Kpi label="MAPE" value={fmtPct(m.mape)} note="relative to actual output" />
        <Kpi label="Bias" value={fmtMW(m.bias, true)} note={m.bias && m.bias > 0 ? 'forecast runs high' : 'forecast runs low'} />
        <Kpi label="Hours over-forecast" value={fmtPct(r.over_forecast_share_pct, 0)} note="forecast above actual" />
        <Kpi
          label="Energy gap"
          value={m.forecast_mwh && m.actual_mwh ? `${(((m.forecast_mwh - m.actual_mwh) / m.actual_mwh) * 100).toFixed(1)}%` : '-'}
          note={`${fmtEnergy(m.forecast_mwh)} forecast vs ${fmtEnergy(m.actual_mwh)} actual`}
        />
      </div>

      <Interpretation r={r} />

      <div style={{ height: 16 }} />
      <div className="grid grid-2">
        <DailyBiasChart r={r} />
        <DailyMaeChart r={r} />
      </div>
      <div style={{ height: 16 }} />
      <div className="grid grid-2">
        <HourOfDayChart r={r} />
        <LeadTimeChart r={r} />
      </div>
      <div style={{ height: 16 }} />
      <div className="grid grid-2">
        <HistogramChart r={r} />
        <MarginCard r={r} />
      </div>
    </>
  )
}

function Interpretation({ r }: { r: AccuracyReport }) {
  const m = r.month
  const p90 = r.margins.find((x) => x.coverage === 90)?.margin_mw ?? null
  const p95 = r.margins.find((x) => x.coverage === 95)?.margin_mw ?? null
  const meanForecastMw = m.forecast_mwh && m.n ? m.forecast_mwh / m.n : null
  const worst = [...r.days].filter((d) => d.bias !== null).sort((a, b) => (b.bias ?? 0) - (a.bias ?? 0))[0]
  const high = m.bias !== null && m.bias > 0

  return (
    <Card title="What this means for procurement">
      <div className="prose">
        <p>
          In January 2026 the day-ahead wind forecast was <strong>{high ? 'systematically optimistic' : 'systematically cautious'}</strong>:
          on average it {high ? 'over' : 'under'}stated hourly wind by <strong>{fmtMW(Math.abs(m.bias ?? 0))}</strong>
          {meanForecastMw && ` (about ${fmtPct(((m.bias ?? 0) / meanForecastMw) * 100, 0)} of the mean forecast level)`}, and it was above the
          outturn in <strong>{fmtPct(r.over_forecast_share_pct, 0)}</strong> of hours. A desk that bought exactly "demand minus forecast"
          would have been short {high ? 'most days' : 'rarely'}.
        </p>
        <p>
          The typical miss (MAE) was <strong>{fmtMW(m.mae)}</strong>, but the tail matters more than the average: the worst day was{' '}
          <strong>{worst ? shortDate(worst.date) : '-'}</strong> with a bias of <strong>{fmtMW(worst?.bias ?? null, true)}</strong>.
          To be covered in 9 hours out of 10, add roughly <strong>{fmtMW(p90)}</strong> of thermal headroom to the forecast; for 19 out of 20,
          add <strong>{fmtMW(p95)}</strong>. The forecast also gets better as it ages (see lead time), so re-checking the latest run
          right before gate closure is worth a few hundred MW of accuracy.
        </p>
      </div>
    </Card>
  )
}

function DailyBiasChart({ r }: { r: AccuracyReport }) {
  const data = r.days.map((d) => ({ ...d, label: shortDate(d.date) }))
  return (
    <Card title="Daily bias" sub="Mean (forecast - actual) per delivery day. Red = forecast too high (shortfall risk), blue = too low.">
      <div className="chart-sm">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="label" {...axisProps} interval={4} />
            <YAxis tickFormatter={kFormat} {...axisProps} width={40} />
            <ReferenceLine y={0} stroke="var(--text-muted)" />
            <Tooltip
              cursor={{ fill: 'var(--grid)' }}
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <TooltipBox
                    title={shortDate(payload[0].payload.date)}
                    rows={[
                      { label: 'Bias', value: fmtMW(payload[0].payload.bias, true) },
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae) },
                      { label: 'Forecast', value: fmtEnergy(payload[0].payload.forecast_mwh) },
                      { label: 'Actual', value: fmtEnergy(payload[0].payload.actual_mwh) },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="bias" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.date} fill={(d.bias ?? 0) >= 0 ? OVER : UNDER} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function DailyMaeChart({ r }: { r: AccuracyReport }) {
  const data = r.days.map((d) => ({ ...d, label: shortDate(d.date) }))
  return (
    <Card title="Daily MAE" sub="Mean absolute hourly error per delivery day, MW.">
      <div className="chart-sm">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="label" {...axisProps} interval={4} />
            <YAxis tickFormatter={kFormat} {...axisProps} width={40} />
            <Tooltip
              cursor={{ fill: 'var(--grid)' }}
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <TooltipBox
                    title={shortDate(payload[0].payload.date)}
                    rows={[
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae) },
                      { label: 'RMSE', value: fmtMW(payload[0].payload.rmse) },
                      { label: 'MAPE', value: fmtPct(payload[0].payload.mape) },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="mae" fill={ACCENT} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function HourOfDayChart({ r }: { r: AccuracyReport }) {
  const data = r.by_hour.map((h) => ({ ...h, label: `${h.hour.toString().padStart(2, '0')}:00` }))
  return (
    <Card title="Error by hour of day" sub="MAE (bars) and bias (line) across all 31 days, MW.">
      <div className="chart-sm">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="label" {...axisProps} interval={3} />
            <YAxis tickFormatter={kFormat} {...axisProps} width={40} />
            <Tooltip
              cursor={{ fill: 'var(--grid)' }}
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <TooltipBox
                    title={payload[0].payload.label}
                    rows={[
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae) },
                      { label: 'Bias', value: fmtMW(payload[0].payload.bias, true) },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="mae" fill={ACCENT} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
            <Line type="monotone" dataKey="bias" stroke={OVER} strokeWidth={2} dot={false} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span>
          <i style={{ background: ACCENT }} />
          MAE
        </span>
        <span>
          <i style={{ background: OVER }} />
          Bias
        </span>
      </div>
    </Card>
  )
}

function LeadTimeChart({ r }: { r: AccuracyReport }) {
  return (
    <Card
      title="Accuracy by forecast lead time"
      sub="MAE of every run against every January hour, bucketed by hours between publication and the target hour. A 09:00 D-1 decision sits at 15-39 h."
    >
      <div className="chart-sm">
        <ResponsiveContainer>
          <LineChart data={r.by_lead_time} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="lead_time" {...axisProps} />
            <YAxis tickFormatter={kFormat} {...axisProps} width={40} domain={[0, 'auto']} />
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <TooltipBox
                    title={`Lead ${payload[0].payload.lead_time}`}
                    rows={[
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae) },
                      { label: 'Bias', value: fmtMW(payload[0].payload.bias, true) },
                      { label: 'Hours', value: String(payload[0].payload.n) },
                    ]}
                  />
                ) : null
              }
            />
            <Line type="monotone" dataKey="mae" stroke={ACCENT} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: 'var(--card)', fill: ACCENT }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function HistogramChart({ r }: { r: AccuracyReport }) {
  const data = r.histogram.map((b) => ({ ...b, label: kFormat(b.bin_start) }))
  const p = r.percentiles
  return (
    <Card title="Error distribution" sub="Hours per 500 MW bin of (forecast - actual). Red bins are shortfalls the margin must cover.">
      <div className="chart-sm">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="label" {...axisProps} interval={2} />
            <YAxis {...axisProps} width={32} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: 'var(--grid)' }}
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <TooltipBox
                    title={`${fmtMW(payload[0].payload.bin_start, true)} to ${fmtMW(payload[0].payload.bin_end, true)}`}
                    rows={[{ label: 'Hours', value: String(payload[0].payload.count) }]}
                  />
                ) : null
              }
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
              {data.map((b) => (
                <Cell key={b.bin_start} fill={b.bin_start >= 0 ? OVER : UNDER} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table>
        <thead>
          <tr>
            {Object.keys(p).map((k) => (
              <th key={k}>{k.toUpperCase()}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            {Object.values(p).map((v, i) => (
              <td key={i}>{fmtMW(v, true)}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </Card>
  )
}

function MarginCard({ r }: { r: AccuracyReport }) {
  const m = r.month
  return (
    <Card
      title="Margin recommendation"
      sub="Buy the forecast minus this margin's worth of wind. Coverage is the share of January hours in which that would have been enough."
    >
      <table>
        <thead>
          <tr>
            <th>Coverage</th>
            <th>Margin (MW)</th>
            <th>vs mean forecast</th>
          </tr>
        </thead>
        <tbody>
          {r.margins.map((x) => (
            <tr key={x.coverage} className={x.coverage === 90 ? 'highlight' : ''}>
              <td>P{x.coverage}</td>
              <td>{fmtMW(x.margin_mw)}</td>
              <td>{fmtPct(marginPctOfForecast(x.margin_mw, m.forecast_mwh, m.n), 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        Margins come straight from the empirical error percentiles above (no distribution assumed). They are
        month-wide; a per-day view is in the Decision tab. Negative percentiles are floored at zero.
      </p>
    </Card>
  )
}
