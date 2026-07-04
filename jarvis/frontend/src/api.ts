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

export type NavChannel = {
  key: string
  title: string
  proxy: string | null
  note: string
  data_source: string
  probabilities: { rise: number | null; flat: number | null; fall: number | null }
  windows: number | null
  expected_return_pct: number
  momentum_6m_pct: number
  ann_vol_pct: number
  max_drawdown_pct: number
  score: number
  costs: {
    fees_usd: number
    spread_usd: number
    tax_on_expected_gain_usd: number
    total_usd: number
    share_of_tranche_pct: number
  }
  reason: string
}

export type NavigatorResponse = {
  horizon_months: number
  tranche_usd: number
  available_tranches: number
  risk_profile: string
  channels: NavChannel[]
  currency_note: string
  disclaimer: string
}

export type ScreenerRow = {
  symbol: string
  name: string
  sector: string
  pe: number
  pb: number
  dividend_yield: number
  roe: number
  net_margin: number
  rev_growth: number
  source: string
  value_rank: number
  momentum_rank: number
  quality_rank: number
  composite: number
  mom6m_pct: number
}

export type TickerDeepDive = {
  symbol: string
  name: string
  sector: string
  currency: string
  country: string
  quote: { price: number; change_pct: number; source: string } | null
  stats: { high_52w?: number; low_52w?: number; ret_1y_pct?: number }
  fundamentals: ScreenerRow | null
  dividends: { date: string; amount: number; source: string }[]
}

export type CalendarEvent = {
  date: string
  kind: 'dividend' | 'earnings' | 'macro' | 'cb'
  title: string
  symbol: string | null
  importance: string
  source: string
}

export type NarrativeTheme = {
  key: string
  title: string
  source: string
  dates: string[]
  values: number[]
  r0: { r0: number | null; note?: string }
  spike: { z: number; level: string }
  query: string
}

export type StressResponse = {
  historical: {
    available: boolean
    horizon_days?: number
    positions?: { symbol: string; value_usd: number; worst_move_pct: number; loss_usd: number }[]
    total_loss_usd?: number
    total_loss_pct?: number
    note?: string
  }
  hypothetical: {
    available: boolean
    scenarios?: { key: string; title: string; assumption: string; impact_usd: number; impact_pct: number }[]
  }
}

export const api = {
  overview: () => http<MarketsOverview>('/api/markets/overview'),
  dataHealth: () => http<DataHealth>('/api/health/data'),
  navigator: (tranche = 1000, horizon = 12) =>
    http<NavigatorResponse>(`/api/navigator?tranche=${tranche}&horizon=${horizon}`),
  screener: (params: string) => http<{ rows: ScreenerRow[] }>(`/api/screener${params}`),
  ticker: (symbol: string) => http<TickerDeepDive>(`/api/ticker/${encodeURIComponent(symbol)}`),
  calendarEvents: (days = 45) => http<{ events: CalendarEvent[]; note: string }>(`/api/calendar?days=${days}`),
  narratives: () => http<{ themes: NarrativeTheme[]; method: string }>('/api/narratives'),
  stress: () => http<StressResponse>('/api/portfolio/stress'),
  rebalance: () => http<{ available: boolean; reason?: string; trades?: { symbol: string; action: string; qty: number; approx_usd: number }[]; note?: string }>('/api/portfolio/rebalance'),
  aiStatus: () => http<{ llm_enabled: boolean; model: string | null }>('/api/ai/status'),
  aiChat: (message: string, history: object[]) =>
    http<{ reply: string; used_llm: boolean }>('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    }),
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
