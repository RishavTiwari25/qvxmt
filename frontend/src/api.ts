import { useEffect, useState } from 'react'
import type { AccuracyReport, ForecastView, VintageRow } from './types'

// Same-origin in every deployment (Vite proxy in dev, nginx in Docker, rewrites on Vercel).
const BASE = '/api'

async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params).toString()
  const response = await fetch(`${BASE}${path}?${query}`)
  if (!response.ok) {
    let detail = response.statusText
    try {
      detail = (await response.json()).detail ?? detail
    } catch {
      /* body was not JSON */
    }
    throw new Error(`${response.status}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export const fetchForecast = (date: string, cutoff: string) =>
  getJson<ForecastView>('/forecast', { date, cutoff })

export const fetchVintages = (date: string, cutoff: string) =>
  getJson<VintageRow[]>('/vintages', { date, cutoff })

export const fetchAccuracy = (cutoff: string) => getJson<AccuracyReport>('/accuracy', { cutoff })

export interface Remote<T> {
  data: T | null
  error: string | null
  loading: boolean
}

/** Minimal fetch-on-change hook; keeps the last good data while reloading so charts don't flash. */
export function useRemote<T>(load: () => Promise<T>, deps: unknown[]): Remote<T> {
  const [state, setState] = useState<Remote<T>>({ data: null, error: null, loading: true })

  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    load().then(
      (data) => !cancelled && setState({ data, error: null, loading: false }),
      (err: Error) => !cancelled && setState((s) => ({ ...s, error: err.message, loading: false })),
    )
    return () => {
      cancelled = true
    }
  }, deps)

  return state
}
