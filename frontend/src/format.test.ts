import { describe, expect, it } from 'vitest'
import { fmtEnergy, fmtMW, fmtPct, fmtPublishTime, hourLabel, marginPctOfForecast, shortDate } from './format'

describe('format helpers', () => {
  it('formats megawatts with thousands separators and optional sign', () => {
    expect(fmtMW(1234.5)).toBe('1,235 MW')
    expect(fmtMW(1234.5, true)).toBe('+1,235 MW')
    expect(fmtMW(-80, true)).toBe('-80 MW')
    expect(fmtMW(null)).toBe('-')
  })

  it('switches energy to GWh above 10,000 MWh', () => {
    expect(fmtEnergy(9_500)).toBe('9,500 MWh')
    expect(fmtEnergy(278_630)).toBe('278.6 GWh')
    expect(fmtEnergy(undefined)).toBe('-')
  })

  it('formats percentages', () => {
    expect(fmtPct(22.38)).toBe('22.4%')
    expect(fmtPct(null)).toBe('-')
  })

  it('formats publish times and hour labels in UTC', () => {
    expect(fmtPublishTime('2026-01-14T07:30:00+00:00')).toBe('14 Jan 07:30')
    expect(hourLabel('2026-01-15T23:00:00+00:00')).toBe('23:00')
    expect(shortDate('2026-01-05')).toBe('5 Jan')
  })

  it('expresses a margin as a share of the mean forecast level', () => {
    // 3,383 MW margin on a day forecast at 278,630 MWh over 24 h (11,610 MW average)
    expect(marginPctOfForecast(3383.3, 278_630, 24)).toBeCloseTo(29.14, 1)
    expect(marginPctOfForecast(null, 278_630, 24)).toBeNull()
    expect(marginPctOfForecast(100, 0, 24)).toBeNull()
  })
})
