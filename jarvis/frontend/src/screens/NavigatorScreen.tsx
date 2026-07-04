import { useEffect, useState } from 'react'
import { api, fmt, type NavigatorResponse } from '../api'

function ProbBar({ rise, flat, fall }: { rise: number | null; flat: number | null; fall: number | null }) {
  if (rise == null) return <div className="sub">исходы детерминированы (ставка)</div>
  const r = (rise ?? 0) * 100, f = (flat ?? 0) * 100, d = (fall ?? 0) * 100
  return (
    <div>
      <div className="probbar">
        <div style={{ width: `${r}%`, background: 'var(--up)' }} />
        <div style={{ width: `${f}%`, background: '#5a6478' }} />
        <div style={{ width: `${d}%`, background: 'var(--down)' }} />
      </div>
      <div className="sub mono">
        рост {r.toFixed(0)}% · флэт {f.toFixed(0)}% · падение {d.toFixed(0)}%
      </div>
    </div>
  )
}

/** NAV: Навигатор аллокации — фирменный экран JARVIS. */
export default function NavigatorScreen() {
  const [data, setData] = useState<NavigatorResponse | null>(null)
  const [tranche, setTranche] = useState(1000)
  const [horizon, setHorizon] = useState(12)

  useEffect(() => {
    api.navigator(tranche, horizon).then(setData).catch(console.error)
  }, [tranche, horizon])

  if (!data) return <div className="screen muted">Считаю каналы…</div>

  return (
    <div className="screen">
      <div className="card" style={{ marginBottom: 8, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <div>
          <h3>Транш, USD</h3>
          <select value={tranche} onChange={(e) => setTranche(+e.target.value)}>
            {[500, 1000, 2000, 5000].map((v) => <option key={v} value={v}>${v}</option>)}
          </select>
        </div>
        <div>
          <h3>Горизонт</h3>
          <select value={horizon} onChange={(e) => setHorizon(+e.target.value)}>
            {[6, 12, 24, 36].map((v) => <option key={v} value={v}>{v} мес</option>)}
          </select>
        </div>
        <div>
          <h3>Доступно траншей</h3>
          <div className="big" style={{ fontSize: 20 }}>{data.available_tranches}</div>
        </div>
        <div style={{ flex: 1, minWidth: 260 }}>
          <h3>Валюта и кэш</h3>
          <div className="sub">{data.currency_note}</div>
        </div>
      </div>

      <div className="cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {data.channels.map((c, i) => (
          <div className={`card ${i === 0 ? 'hero' : ''}`} key={c.key}>
            <h3>
              #{i + 1} {c.title}{' '}
              {c.proxy && <span className="muted">({c.proxy})</span>}{' '}
              <span className={`badge ${c.data_source === 'demo' ? 'demo' : 'live'}`}>{c.data_source}</span>
            </h3>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <div className="big">{c.score}</div>
              <div className="sub">скор · медианный исход {fmt.pct(c.expected_return_pct)} за {data.horizon_months} мес</div>
            </div>
            <div style={{ margin: '8px 0' }}>
              <ProbBar {...c.probabilities} />
            </div>
            <div className="sub">{c.reason}</div>
            <table className="grid" style={{ marginTop: 8 }}>
              <tbody>
                <tr>
                  <td>Издержки транша ${data.tranche_usd}</td>
                  <td>{fmt.usd(c.costs.total_usd)} ({c.costs.share_of_tranche_pct}%)</td>
                </tr>
                <tr>
                  <td className="muted">комиссии / спред / налог 25%</td>
                  <td className="muted">
                    {fmt.usd(c.costs.fees_usd)} / {fmt.usd(c.costs.spread_usd)} / {fmt.usd(c.costs.tax_on_expected_gain_usd)}
                  </td>
                </tr>
                <tr>
                  <td className="muted">волатильность / макс. просадка</td>
                  <td className="muted">{c.ann_vol_pct}% / {c.max_drawdown_pct}%</td>
                </tr>
              </tbody>
            </table>
            <div className="sub" style={{ marginTop: 6 }}>{c.note}</div>
          </div>
        ))}
      </div>
      <div className="disclaimer">{data.disclaimer} Прогнозы записываются в журнал и будут сверены с фактом (петля самоулучшения S1).</div>
    </div>
  )
}
