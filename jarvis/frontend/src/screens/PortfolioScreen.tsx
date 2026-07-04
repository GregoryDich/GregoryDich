import { useEffect, useRef, useState } from 'react'
import { api, fmt, type PortfolioPositions, type RiskMetrics } from '../api'
import Echart from '../components/Echart'

/** PORT: портфель и риск — позиции, VaR, кривая капитала, импорт сделок. */
export default function PortfolioScreen() {
  const [pos, setPos] = useState<PortfolioPositions | null>(null)
  const [risk, setRisk] = useState<RiskMetrics | null>(null)
  const [curve, setCurve] = useState<{ date: string; value: number }[]>([])
  const [form, setForm] = useState({ dt: '', symbol: '', side: 'buy', qty: '', price: '' })
  const fileRef = useRef<HTMLInputElement>(null)

  const load = () => {
    api.positions().then(setPos).catch(console.error)
    api.risk().then(setRisk).catch(console.error)
    api.equityCurve().then((r) => setCurve(r.points)).catch(console.error)
  }
  useEffect(load, [])

  const addTrade = async () => {
    if (!form.dt || !form.symbol || !form.qty || !form.price) return
    await api.addTrade({ ...form, qty: +form.qty, price: +form.price })
    setForm({ dt: '', symbol: '', side: 'buy', qty: '', price: '' })
    load()
  }

  const t = pos?.totals
  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <div className="card">
          <h3>Стоимость</h3>
          <div className="big">{t ? fmt.usd(t.value_usd) : '—'}</div>
          <div className="sub">{t ? `₪${fmt.num(t.value_ils, 0)} · курс ${fmt.num(t.usd_ils)}` : ''}</div>
        </div>
        <div className="card">
          <h3>P&L (total return)</h3>
          <div className={`big ${t && t.pnl_usd >= 0 ? 'up' : 'down'}`}>
            {t ? fmt.usd(t.pnl_usd) : '—'}
          </div>
          <div className="sub">
            {t ? `${fmt.pct(t.pnl_pct)} · дивиденды ${fmt.usd(t.dividends_usd)}` : ''}
            {t && t.realized_pnl_usd !== 0 ? ` · реализовано ${fmt.usd(t.realized_pnl_usd)}` : ''}
          </div>
        </div>
        <div className="card">
          <h3>
            VaR 95% / день{' '}
            {risk?.available && risk.reliability === 'low' && (
              <span className="badge demo" title="Меньше ~полугода истории — метрики риска ненадёжны">мало истории</span>
            )}
          </h3>
          <div className="big">{risk?.available ? fmt.pct(-risk.var95_daily * 100, 2) : '—'}</div>
          <div className="sub">
            {risk?.available && risk.var95_daily_usd ? `≈ ${fmt.usd(-risk.var95_daily_usd)}` : 'потеря, не превышаемая в 95% дней'}
          </div>
        </div>
        <div className="card">
          <h3>Волатильность (год)</h3>
          <div className="big">{risk?.available ? `${(risk.ann_vol * 100).toFixed(1)}%` : '—'}</div>
          <div className="sub">Sharpe {risk?.available ? risk.sharpe.toFixed(2) : '—'} · β SPY {risk?.available && risk.beta_spy != null ? risk.beta_spy.toFixed(2) : '—'}</div>
        </div>
        <div className="card">
          <h3>Макс. просадка</h3>
          <div className="big down">{risk?.available ? `${(risk.max_drawdown * 100).toFixed(1)}%` : '—'}</div>
          <div className="sub">CVaR95 {risk?.available ? fmt.pct(-risk.cvar95_daily * 100, 2) : '—'}</div>
        </div>
      </div>

      <div className="cards" style={{ gridTemplateColumns: '7fr 5fr', marginTop: 8 }}>
        <div className="card">
          <h3>Позиции {pos?.sources.includes('demo') && <span className="badge demo">demo-цены</span>}</h3>
          <table className="grid">
            <thead>
              <tr>
                <th>Тикер</th><th>Кол-во</th><th>Ср. цена</th><th>Цена</th>
                <th>Стоимость $</th><th>Дивид. $</th><th>P&L $</th><th>P&L %</th><th>Вес</th>
              </tr>
            </thead>
            <tbody>
              {pos?.positions.map((p) => (
                <tr key={p.symbol}>
                  <td><b>{p.symbol}</b></td>
                  <td>{fmt.num(p.qty, 4)}</td>
                  <td>{fmt.num(p.avg_cost)}</td>
                  <td>{fmt.num(p.price)}</td>
                  <td>{fmt.num(p.value_usd, 0)}</td>
                  <td>{fmt.num(p.dividends_usd, 0)}</td>
                  <td className={p.pnl_usd >= 0 ? 'up' : 'down'}>{fmt.num(p.pnl_usd, 0)}</td>
                  <td className={p.pnl_pct >= 0 ? 'up' : 'down'}>{fmt.pct(p.pnl_pct)}</td>
                  <td>{p.weight_pct.toFixed(1)}%</td>
                </tr>
              ))}
              {(!pos || pos.positions.length === 0) && (
                <tr><td colSpan={9} className="muted">Нет позиций — добавьте сделку или импортируйте CSV</td></tr>
              )}
            </tbody>
          </table>
          <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
            <input type="date" value={form.dt} onChange={(e) => setForm({ ...form, dt: e.target.value })} />
            <input placeholder="Тикер" style={{ width: 90 }} value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} />
            <select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })}>
              <option value="buy">Купить</option>
              <option value="sell">Продать</option>
            </select>
            <input placeholder="Кол-во" style={{ width: 80 }} value={form.qty}
              onChange={(e) => setForm({ ...form, qty: e.target.value })} />
            <input placeholder="Цена" style={{ width: 90 }} value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })} />
            <button className="primary" onClick={addTrade}>Добавить</button>
            <button className="ghost" onClick={() => fileRef.current?.click()}>Импорт CSV</button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              onChange={async (e) => {
                const f = e.target.files?.[0]
                if (f) {
                  await api.importTrades(f)
                  load()
                }
              }}
            />
          </div>
          <div className="sub" style={{ marginTop: 4 }}>
            CSV: date,symbol,side,qty,price[,currency,fees,note]
          </div>
        </div>
        <div>
          <div className="card" style={{ marginBottom: 8 }}>
            <h3>Аллокация</h3>
            <div style={{ height: 180 }}>
              <Echart
                option={{
                  tooltip: { formatter: '{b}: {d}%' },
                  series: [{
                    type: 'pie',
                    radius: ['45%', '75%'],
                    label: { color: '#d7dce6', fontSize: 11 },
                    data: (pos?.positions ?? []).map((p) => ({
                      name: p.symbol,
                      value: Math.round(p.value_usd),
                    })),
                  }],
                }}
              />
            </div>
          </div>
          <div className="card">
            <h3>Кривая капитала (норм.)</h3>
            <div style={{ height: 160 }}>
              <Echart
                option={{
                  grid: { left: 45, right: 10, top: 10, bottom: 20 },
                  xAxis: { type: 'category', data: curve.map((p) => p.date), axisLabel: { color: '#7d8698', fontSize: 9 } },
                  yAxis: { type: 'value', scale: true, axisLabel: { color: '#7d8698', fontSize: 9 }, splitLine: { lineStyle: { color: '#141a26' } } },
                  series: [{
                    type: 'line',
                    data: curve.map((p) => +p.value.toFixed(4)),
                    showSymbol: false,
                    lineStyle: { color: '#f5a623', width: 1.5 },
                    areaStyle: { color: 'rgba(245,166,35,0.08)' },
                  }],
                  tooltip: { trigger: 'axis' },
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
