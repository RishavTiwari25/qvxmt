import type { ReactNode } from 'react'

export function Card({ title, sub, children }: { title?: string; sub?: string; children: ReactNode }) {
  return (
    <section className="card">
      {title && <h2>{title}</h2>}
      {sub && <p className="sub">{sub}</p>}
      {children}
    </section>
  )
}

export function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {note && <div className="note">{note}</div>}
    </div>
  )
}

export function Loading({ text = 'Loading data...' }: { text?: string }) {
  return <div className="state">{text}</div>
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state error">
      Could not load data: {message}
      <div className="hint">Check that the API is running and the query is valid.</div>
    </div>
  )
}

/** Recharts tooltip body with our own styling. `rows` are already formatted. */
export function TooltipBox({ title, rows }: { title: string; rows: { label: string; value: string; color?: string }[] }) {
  return (
    <div className="tooltip">
      <b>{title}</b>
      {rows.map((r) => (
        <div key={r.label}>
          {r.color && <i className="swatch" style={{ background: r.color, display: 'inline-block', width: 8, height: 8, borderRadius: 2, marginRight: 6 }} />}
          {r.label}: {r.value}
        </div>
      ))}
    </div>
  )
}
