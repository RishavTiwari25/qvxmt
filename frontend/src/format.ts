// Small, pure formatting helpers shared by the views. Covered by format.test.ts.

const MW_FORMAT = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

/** 1234.5 -> "1,235 MW"; null -> "-" */
export function fmtMW(value: number | null | undefined, signed = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  const sign = signed && value > 0 ? '+' : ''
  return `${sign}${MW_FORMAT.format(value)} MW`
}

/** Energy totals read better in GWh above 10,000 MWh. */
export function fmtEnergy(mwh: number | null | undefined): string {
  if (mwh === null || mwh === undefined || Number.isNaN(mwh)) return '-'
  if (Math.abs(mwh) >= 10_000) return `${(mwh / 1000).toFixed(1)} GWh`
  return `${MW_FORMAT.format(mwh)} MWh`
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(digits)}%`
}

/** "2026-01-14T07:30:00+00:00" -> "14 Jan 07:30" (UTC; January in the UK is GMT). */
export function fmtPublishTime(iso: string): string {
  const d = new Date(iso)
  const day = d.getUTCDate()
  const month = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })
  return `${day} ${month} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

/** ISO timestamp -> "07:00" clock label for the x-axis. */
export function hourLabel(iso: string): string {
  const d = new Date(iso)
  return `${pad(d.getUTCHours())}:00`
}

/** "2026-01-15" -> "15 Jan" */
export function shortDate(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00Z`)
  return `${d.getUTCDate()} ${d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })}`
}

/** Margin as a share of the average forecast level, e.g. 3383 MW on 13,432 MW -> 25.2 */
export function marginPctOfForecast(marginMw: number | null, forecastMwh: number | null, hours: number): number | null {
  if (marginMw === null || forecastMwh === null || hours <= 0 || forecastMwh <= 0) return null
  return (marginMw / (forecastMwh / hours)) * 100
}

function pad(n: number): string {
  return n.toString().padStart(2, '0')
}
