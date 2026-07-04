import { useEffect, useState } from 'react'
import { api, type MacroSeriesMeta } from '../api'
import Echart from '../components/Echart'

type Pt = { date: string; value: number }

function LineCard({ title, unit, source, points, color = '#3fb1ce' }: {
  title: string
  unit?: string
  source?: string
  points: Pt[]
  color?: string
}) {
  return (
    <div className="card" style={{ marginBottom: 8 }}>
      <h3>
        {title} {unit && <span className="muted">({unit})</span>}{' '}
        {source && <span className={`badge ${source === 'demo' ? 'demo' : 'live'}`}>{source}</span>}
      </h3>
      <div style={{ height: 150 }}>
        <Echart
          option={{
            grid: { left: 45, right: 10, top: 8, bottom: 20 },
            xAxis: { type: 'category', data: points.map((p) => p.date), axisLabel: { color: '#7d8698', fontSize: 9 } },
            yAxis: { type: 'value', scale: true, axisLabel: { color: '#7d8698', fontSize: 9 }, splitLine: { lineStyle: { color: '#141a26' } } },
            series: [{
              type: 'line',
              data: points.map((p) => +p.value.toFixed(3)),
              showSymbol: false,
              lineStyle: { color, width: 1.5 },
            }],
            tooltip: { trigger: 'axis' },
          }}
        />
      </div>
    </div>
  )
}

/** ECO: макроэкономика — США и Израиль на одном экране. */
export default function MacroScreen() {
  const [series, setSeries] = useState<MacroSeriesMeta[]>([])
  const [selected, setSelected] = useState('FRED:DGS10')
  const [data, setData] = useState<{ title: string; unit: string; source: string; points: Pt[] } | null>(null)
  const [spread, setSpread] = useState<Pt[]>([])
  const [ilsRate, setIlsRate] = useState<{ title: string; source: string; points: Pt[] } | null>(null)
  const [usdils, setUsdils] = useState<{ title: string; source: string; points: Pt[] } | null>(null)

  useEffect(() => {
    api.macroSeries().then((r) => setSeries(r.series)).catch(console.error)
    api.yieldSpread().then((r) => setSpread(r.points)).catch(console.error)
    api.macroData('BOI:POLICY').then(setIlsRate).catch(console.error)
    api.macroData('BOI:USDILS').then(setUsdils).catch(console.error)
  }, [])

  useEffect(() => {
    api.macroData(selected).then(setData).catch(console.error)
  }, [selected])

  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: '2fr 5fr 5fr' }}>
        <div className="card">
          <h3>Серии</h3>
          {['US', 'IL'].map((country) => (
            <div key={country}>
              <div className="sub" style={{ margin: '6px 0 2px' }}>
                {country === 'US' ? '🇺🇸 США' : '🇮🇱 Израиль'}
              </div>
              {series.filter((s) => s.country === country).map((s) => (
                <div
                  key={s.id}
                  className="item"
                  style={{
                    padding: '4px 6px',
                    cursor: 'pointer',
                    color: s.id === selected ? 'var(--accent)' : undefined,
                  }}
                  onClick={() => setSelected(s.id)}
                >
                  {s.title}
                </div>
              ))}
            </div>
          ))}
        </div>
        <div>
          {data && <LineCard title={data.title} unit={data.unit} source={data.source} points={data.points} color="#f5a623" />}
          <LineCard title="Спред 10Y−2Y США (индикатор рецессии)" unit="п.п." points={spread} color="#e5484d" />
        </div>
        <div>
          {ilsRate && <LineCard title={ilsRate.title} source={ilsRate.source} points={ilsRate.points} color="#2fbf71" />}
          {usdils && <LineCard title={usdils.title} source={usdils.source} points={usdils.points} />}
        </div>
      </div>
    </div>
  )
}
