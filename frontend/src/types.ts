// Mirrors backend/app/schemas.py. Keep the two in sync by hand; the API is small.

export interface Summary {
  n: number
  mae: number | null
  rmse: number | null
  mape: number | null
  bias: number | null
  forecast_mwh: number | null
  actual_mwh: number | null
}

export interface DaySummary extends Summary {
  date: string
  publish_time: string | null
}

export interface Margin {
  coverage: number
  margin_mw: number | null
}

export interface ForecastPoint {
  time: string
  forecast_mw: number
  actual_mw: number | null
  error_mw: number | null
}

export interface Vintage {
  publish_time: string
  before_cutoff: boolean
  points: { time: string; forecast_mw: number }[]
}

export interface ForecastView {
  date: string
  cutoff: string
  cutoff_utc: string
  publish_time: string
  lead_hours_to_day_start: number
  points: ForecastPoint[]
  summary: Summary
  margins: Margin[]
  vintages: Vintage[]
}

export interface VintageRow extends Summary {
  publish_time: string
  lead_hours_to_day_start: number
  before_cutoff: boolean
  hours_covered: number
}

export interface HourRow {
  hour: number
  mae: number | null
  bias: number | null
  n: number
}

export interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
}

export interface LeadTimeRow {
  lead_time: string
  mae: number | null
  bias: number | null
  n: number
}

export interface AccuracyReport {
  cutoff: string
  period: { from: string; to: string }
  month: Summary
  days: DaySummary[]
  by_hour: HourRow[]
  percentiles: Record<string, number | null>
  margins: Margin[]
  histogram: HistogramBin[]
  by_lead_time: LeadTimeRow[]
  over_forecast_share_pct: number | null
}
