import { useEffect, useState } from 'react'
import { api, type NarrativeTheme } from '../api'
import Echart from '../components/Echart'

/** NEWS: нарративы — интенсивность внимания + «заразность» R₀ (Hawkes-метод
 * из исследования narrative-economics). Фича, которой нет у Bloomberg. */
export default function NarrativesScreen() {
  const [themes, setThemes] = useState<NarrativeTheme[]>([])
  const [method, setMethod] = useState('')

  useEffect(() => {
    api.narratives().then((r) => {
      setThemes(r.themes)
      setMethod(r.method)
    }).catch(console.error)
  }, [])

  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
        {themes.map((t) => (
          <div className="card" key={t.key}>
            <h3>
              {t.title}{' '}
              <span className={`badge ${t.source === 'demo' ? 'demo' : 'live'}`}>{t.source}</span>
              <span style={{ float: 'right' }}>
                {t.spike.level}{' '}
                <span className="mono muted">z={t.spike.z}</span>
              </span>
            </h3>
            <div style={{ display: 'flex', gap: 16, alignItems: 'baseline', marginBottom: 4 }}>
              <div className="big" style={{ color: (t.r0.r0 ?? 0) > 1 ? 'var(--down)' : 'var(--up)' }}>
                R₀ {t.r0.r0 ?? '—'}
              </div>
              <div className="sub">
                {(t.r0.r0 ?? 0) > 1 ? 'нарратив распространяется сам' : 'нарратив затухает'}
              </div>
            </div>
            <div style={{ height: 130 }}>
              <Echart
                option={{
                  grid: { left: 35, right: 8, top: 8, bottom: 18 },
                  xAxis: { type: 'category', data: t.dates, axisLabel: { color: '#7d8698', fontSize: 9 } },
                  yAxis: { type: 'value', scale: true, axisLabel: { color: '#7d8698', fontSize: 9 }, splitLine: { lineStyle: { color: '#141a26' } } },
                  series: [{
                    type: 'line',
                    data: t.values,
                    showSymbol: false,
                    lineStyle: { color: '#3fb1ce', width: 1.2 },
                    areaStyle: { color: 'rgba(63,177,206,0.10)' },
                  }],
                  tooltip: { trigger: 'axis' },
                }}
              />
            </div>
            <div className="sub mono" style={{ marginTop: 4 }}>{t.query}</div>
          </div>
        ))}
      </div>
      <div className="disclaimer">{method}</div>
    </div>
  )
}
