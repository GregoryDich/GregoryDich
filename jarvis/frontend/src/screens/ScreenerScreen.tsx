import { useEffect, useState } from 'react'
import { api, fmt, type ScreenerRow, type TickerDeepDive } from '../api'

function RankPill({ v }: { v: number }) {
  const color = v >= 70 ? 'var(--up)' : v >= 40 ? 'var(--muted)' : 'var(--down)'
  return <span className="mono" style={{ color }}>{v.toFixed(0)}</span>
}

/** EQS: скринер по локальной базе + дип-дайв FA по клику. */
export default function ScreenerScreen() {
  const [rows, setRows] = useState<ScreenerRow[]>([])
  const [maxPe, setMaxPe] = useState('')
  const [minDiv, setMinDiv] = useState('')
  const [minComposite, setMinComposite] = useState('')
  const [dive, setDive] = useState<TickerDeepDive | null>(null)

  const load = () => {
    const q = new URLSearchParams()
    if (maxPe) q.set('max_pe', maxPe)
    if (minDiv) q.set('min_div_yield', minDiv)
    if (minComposite) q.set('min_composite', minComposite)
    api.screener(q.toString() ? `?${q}` : '').then((r) => setRows(r.rows)).catch(console.error)
  }
  useEffect(load, [])

  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: dive ? '7fr 5fr' : '1fr' }}>
        <div className="card">
          <h3>Скринер · композитные ранги value / momentum / quality</h3>
          <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
            <input placeholder="Макс P/E" style={{ width: 90 }} value={maxPe}
              onChange={(e) => setMaxPe(e.target.value)} />
            <input placeholder="Мин див.дох. %" style={{ width: 110 }} value={minDiv}
              onChange={(e) => setMinDiv(e.target.value)} />
            <input placeholder="Мин композит" style={{ width: 110 }} value={minComposite}
              onChange={(e) => setMinComposite(e.target.value)} />
            <button className="primary" onClick={load}>Отфильтровать</button>
          </div>
          <table className="grid">
            <thead>
              <tr>
                <th>Тикер</th><th>P/E</th><th>P/B</th><th>Див %</th><th>ROE</th>
                <th>6м %</th><th>Val</th><th>Mom</th><th>Qual</th><th>Композит</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} onClick={() => api.ticker(r.symbol).then(setDive)}>
                  <td><b>{r.symbol}</b> <span className="muted">{r.name}</span></td>
                  <td>{fmt.num(r.pe, 1)}</td>
                  <td>{fmt.num(r.pb, 1)}</td>
                  <td>{fmt.num(r.dividend_yield, 1)}</td>
                  <td>{fmt.num(r.roe, 0)}</td>
                  <td className={r.mom6m_pct >= 0 ? 'up' : 'down'}>{fmt.pct(r.mom6m_pct)}</td>
                  <td><RankPill v={r.value_rank} /></td>
                  <td><RankPill v={r.momentum_rank} /></td>
                  <td><RankPill v={r.quality_rank} /></td>
                  <td><b><RankPill v={r.composite} /></b></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="sub" style={{ marginTop: 6 }}>
            Ранги — перцентили внутри локальной вселенной (демо-фундаментал до live-подключения).
            Клик по строке — дип-дайв.
          </div>
        </div>
        {dive && (
          <div className="card">
            <h3>
              FA · {dive.symbol} — {dive.name}{' '}
              <button className="ghost" style={{ float: 'right' }} onClick={() => setDive(null)}>✕</button>
            </h3>
            {dive.quote && (
              <div style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
                <div className="big">{fmt.num(dive.quote.price)}</div>
                <div className={dive.quote.change_pct >= 0 ? 'up' : 'down'}>
                  {fmt.pct(dive.quote.change_pct, 2)}
                </div>
                <span className={`badge ${dive.quote.source === 'demo' ? 'demo' : 'live'}`}>{dive.quote.source}</span>
              </div>
            )}
            <table className="grid" style={{ marginTop: 8 }}>
              <tbody>
                <tr><td>Сектор</td><td>{dive.sector || '—'} · {dive.country || '—'}</td></tr>
                <tr><td>52 недели</td><td>{fmt.num(dive.stats.low_52w, 0)} — {fmt.num(dive.stats.high_52w, 0)}</td></tr>
                <tr><td>Доходность 1г</td><td className={(dive.stats.ret_1y_pct ?? 0) >= 0 ? 'up' : 'down'}>{fmt.pct(dive.stats.ret_1y_pct ?? 0)}</td></tr>
                {dive.fundamentals && (
                  <>
                    <tr><td>P/E · P/B</td><td>{fmt.num(dive.fundamentals.pe, 1)} · {fmt.num(dive.fundamentals.pb, 1)}</td></tr>
                    <tr><td>ROE · маржа</td><td>{fmt.num(dive.fundamentals.roe, 0)}% · {fmt.num(dive.fundamentals.net_margin, 0)}%</td></tr>
                    <tr><td>Рост выручки</td><td>{fmt.pct(dive.fundamentals.rev_growth, 0)}</td></tr>
                    <tr><td>Ранги V/M/Q</td><td>
                      <RankPill v={dive.fundamentals.value_rank} /> / <RankPill v={dive.fundamentals.momentum_rank} /> / <RankPill v={dive.fundamentals.quality_rank} />
                    </td></tr>
                  </>
                )}
              </tbody>
            </table>
            <h3 style={{ marginTop: 10 }}>Дивиденды (история)</h3>
            <table className="grid">
              <tbody>
                {dive.dividends.slice(0, 6).map((d) => (
                  <tr key={d.date}><td>{d.date}</td><td>{fmt.num(d.amount)}</td></tr>
                ))}
                {dive.dividends.length === 0 && <tr><td className="muted" colSpan={2}>не платит</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
