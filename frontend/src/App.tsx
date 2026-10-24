import { useState } from 'react'
import { About } from './pages/About'
import { AccuracyView } from './pages/AccuracyView'
import { DecisionView } from './pages/DecisionView'

type Tab = 'decision' | 'accuracy' | 'about'

const TABS: { id: Tab; label: string }[] = [
  { id: 'decision', label: 'Decision view' },
  { id: 'accuracy', label: 'Accuracy view' },
  { id: 'about', label: 'Methodology' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('decision')
  // The cutoff is a desk-wide setting, so it lives here and feeds both analytical views.
  const [cutoff, setCutoff] = useState('09:00')

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Wind Desk
          <small>GB day-ahead wind forecast vs outturn, January 2026</small>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="spacer" />
        {tab !== 'about' && (
          <label className="field">
            Decision cutoff (D-1, UK time)
            <input type="time" value={cutoff} step={1800} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
          </label>
        )}
      </header>

      {tab === 'decision' && <DecisionView cutoff={cutoff} />}
      {tab === 'accuracy' && <AccuracyView cutoff={cutoff} />}
      {tab === 'about' && <About />}
    </div>
  )
}
