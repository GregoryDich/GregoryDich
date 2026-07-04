// Тонкий клиент API. Все данные приходят с пометкой источника (live|delayed|demo).

export type Quote = {
  symbol: string
  name: string
  price: number
  change_pct: number | null
  source: string
}

export type MarketsOverview = {
  groups: { title: string; quotes: Quote[] }[]
  status: { mode: string; by_source: Record<string, number> }
}

export type Candle = {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type MacroSeriesMeta = {
  id: string
  title: string
  unit: string
  country: string
  source: string
}

export type FreedomSummary = {
  monthly_expenses: number
  expenses_breakdown: Record<string, number>
  swr: number
  inflation: number
  base_nominal_return: number
  base_real_return: number
  target_capital: number
  current_capital: number
  progress: number
  passive_income_monthly: number
  gap_monthly: number
  years_to_target_base: number | null
  scenarios: { contribution: number; years: Record<string, number | null> }[]
  portfolio_value_usd: number
  usd_ils: number | null
  onboarded: boolean
  name: string
  disclaimer: string
}

export type Position = {
  symbol: string
  qty: number
  avg_cost: number
  price: number
  price_source: string
  currency: string
  value_usd: number
  value_ils: number
  dividends_usd: number
  pnl_usd: number
  pnl_pct: number
  weight_pct: number
}

export type PortfolioPositions = {
  positions: Position[]
  totals: {
    value_usd: number
    value_ils: number
    cost_usd: number
    dividends_usd: number
    realized_pnl_usd: number
    pnl_usd: number
    pnl_pct: number
    usd_ils: number
  }
  sources: string[]
}

export type RiskMetrics = {
  available: boolean
  reason?: string
  reliability?: 'ok' | 'low'
  ann_return: number
  ann_vol: number
  sharpe: number
  sortino: number
  max_drawdown: number
  var95_daily: number
  cvar95_daily: number
  var99_daily: number
  beta_spy?: number
  var95_daily_usd?: number
  n_days: number
}

export type Alert = {
  id: number
  symbol: string
  condition: 'above' | 'below'
  level: number
  active: boolean
  note: string
  created_at: string
  last_triggered_at: string | null
}

export type OnboardingQuestion = {
  id: string
  type: string
  title: string
  hint?: string
  options?: { v: string; label: string }[]
  fields?: { k: string; label: string }[]
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init)
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`)
  return r.json() as Promise<T>
}

export type DataHealth = {
  status: { mode: string; by_source: Record<string, number> }
  sources: { kind: string; source: string; items: number; last_update: string | null }[]
}

export const api = {
  overview: () => http<MarketsOverview>('/api/markets/overview'),
  dataHealth: () => http<DataHealth>('/api/health/data'),
  watchlist: () => http<{ items: Quote[] }>('/api/markets/watchlist'),
  history: (symbol: string, days = 365) =>
    http<{ symbol: string; name: string; source: string; candles: Candle[] }>(
      `/api/markets/history/${encodeURIComponent(symbol)}?days=${days}`,
    ),
  heatmap: () =>
    http<{ items: { symbol: string; name: string; sector: string; change_pct: number }[] }>(
      '/api/markets/heatmap',
    ),
  macroSeries: () => http<{ series: MacroSeriesMeta[] }>('/api/macro/series'),
  macroData: (id: string) =>
    http<{ id: string; title: string; unit: string; source: string; points: { date: string; value: number }[] }>(
      `/api/macro/series/${encodeURIComponent(id)}`,
    ),
  yieldSpread: () => http<{ points: { date: string; value: number }[] }>('/api/macro/yield-spread'),
  freedom: () => http<FreedomSummary>('/api/freedom'),
  positions: () => http<PortfolioPositions>('/api/portfolio/positions'),
  risk: () => http<RiskMetrics>('/api/portfolio/risk'),
  equityCurve: () => http<{ points: { date: string; value: number }[] }>('/api/portfolio/equity-curve'),
  addTrade: (t: object) =>
    http('/api/portfolio/trades', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(t),
    }),
  importTrades: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return http<{ imported: number }>('/api/portfolio/trades/import', { method: 'POST', body: fd })
  },
  alerts: () => http<{ alerts: Alert[] }>('/api/alerts'),
  createAlert: (a: object) =>
    http('/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(a),
    }),
  deleteAlert: (id: number) => http(`/api/alerts/${id}`, { method: 'DELETE' }),
  testAlert: () => http<{ sent: boolean; dry_run: boolean; configured_channels: number }>('/api/alerts/test', { method: 'POST' }),
  digest: () => http<{ text: string }>('/api/alerts/digest', { method: 'POST' }),
  profile: () => http<Record<string, unknown>>('/api/profile'),
  onboarding: () => http<{ questions: OnboardingQuestion[] }>('/api/profile/onboarding'),
  saveProfile: (p: object) =>
    http('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(p),
    }),
}

// Форматтеры терпимы к null/undefined: неполные данные не должны ронять рендер
export const fmt = {
  usd: (v: number | null | undefined) =>
    v == null ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
  num: (v: number | null | undefined, digits = 2) =>
    v == null ? '—' : v.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }),
  pct: (v: number | null | undefined, digits = 1) =>
    v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`,
}
