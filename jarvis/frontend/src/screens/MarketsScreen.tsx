import { useEffect, useState } from 'react'
import { api, fmt, type Candle, type MarketsOverview, type Quote } from '../api'
import Echart, { axisDefaults } from '../components/Echart'
import PriceChart from '../components/PriceChart'

function QuoteRow({ q, onPick }: { q: Quote; onPick: (s: string) => void }) {
  const ch = q.change_pct ?? 0
  return (
    <tr onClick={() => onPick(q.symbol)}>
      <td>
        <b>{q.symbol}</b> <span className="muted">{q.name}</span>
      </td>
      <td>{fmt.num(q.price)}</td>
      <td className={ch >= 0 ? 'up' : 'down'}>{fmt.pct(ch, 2)}</td>
      <td className="muted">{q.source}</td>
    </tr>
  )
}

/** WEI: обзор рынков — группы котировок, теплокарта, график. */
export default function MarketsScreen() {
  const [data, setData] = useState<MarketsOverview | null>(null)
  const [watch, setWatch] = useState<Quote[]>([])
  const [heat, setHeat] = useState<{ name: string; value: number; change: number }[]>([])
  const [symbol, setSymbol] = useState('^GSPC')
  const [candles, setCandles] = useState<Candle[]>([])
  const [chartMeta, setChartMeta] = useState({ name: '', source: '' })

  const load = () => {
    api.overview().then(setData).catch(console.error)
    api.watchlist().then((r) => setWatch(r.items)).catch(console.error)
    api.heatmap()
      .then((r) =>
        setHeat(r.items.map((i) => ({ name: i.symbol, value: 1, change: i.change_pct }))),
      )
      .catch(console.error)
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 60_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    api.history(symbol, 365)
      .then((r) => {
        setCandles(r.candles)
        setChartMeta({ name: r.name, source: r.source })
      })
      .catch(console.error)
  }, [symbol])

  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: '5fr 7fr' }}>
        <div>
          {data?.groups.map((g) => (
            <div className="card" key={g.title} style={{ marginBottom: 8 }}>
              <h3>{g.title}</h3>
              <table className="grid">
                <tbody>
                  {g.quotes.map((q) => (
                    <QuoteRow key={q.symbol} q={q} onPick={setSymbol} />
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
        <div>
          <div className="card" style={{ marginBottom: 8 }}>
            <h3>
              {symbol} — {chartMeta.name}{' '}
              <span className="muted">({chartMeta.source}, дневные свечи, 1 год)</span>
            </h3>
            <div className="chart-box">
              <PriceChart candles={candles} />
            </div>
          </div>
          <div className="card" style={{ marginBottom: 8 }}>
            <h3>Акции: карта изменений за день</h3>
            <div style={{ height: 170 }}>
              <Echart
                option={{
                  tooltip: {
                    formatter: (p) => {
                      const d = p as unknown as { name: string; data: { change: number } }
                      return `${d.name}: ${fmt.pct(d.data.change, 2)}`
                    },
                  },
                  series: [
                    {
                      type: 'treemap',
                      roam: false,
                      nodeClick: false,
                      breadcrumb: { show: false },
                      label: { show: true, fontSize: 11, fontFamily: 'monospace' },
                      data: heat.map((h) => ({
                        ...h,
                        itemStyle: {
                          color: h.change >= 0
                            ? `rgba(47,191,113,${Math.min(0.25 + Math.abs(h.change) / 4, 0.95)})`
                            : `rgba(229,72,77,${Math.min(0.25 + Math.abs(h.change) / 4, 0.95)})`,
                        },
                      })),
                    },
                  ],
                  xAxis: undefined,
                  yAxis: undefined,
                  ...{ axis: axisDefaults },
                }}
              />
            </div>
          </div>
          <div className="card">
            <h3>Вотчлист</h3>
            <table className="grid">
              <thead>
                <tr><th>Тикер</th><th>Цена</th><th>Δ%</th><th>Источник</th></tr>
              </thead>
              <tbody>
                {watch.map((q) => (
                  <QuoteRow key={q.symbol} q={q} onPick={setSymbol} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
