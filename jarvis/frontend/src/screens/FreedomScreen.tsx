import { useEffect, useState } from 'react'
import { api, fmt, type FreedomSummary } from '../api'
import Gauge from '../components/Gauge'

const EXPENSE_LABELS: Record<string, string> = {
  rent: 'Аренда/жильё',
  food: 'Еда',
  clothing: 'Одежда',
  utilities_subscriptions: 'Связь/коммуналка/подписки',
  daily_free: 'Свободные траты',
}

/** FIRE: точка финансовой безубыточности — главный экран JARVIS. */
export default function FreedomScreen() {
  const [d, setD] = useState<FreedomSummary | null>(null)

  useEffect(() => {
    api.freedom().then(setD).catch(console.error)
    const t = setInterval(() => api.freedom().then(setD).catch(() => {}), 60_000)
    return () => clearInterval(t)
  }, [])

  if (!d) return <div className="screen muted">Загрузка…</div>

  return (
    <div className="screen">
      <div className="cards" style={{ gridTemplateColumns: '260px repeat(auto-fit, minmax(180px, 1fr))' }}>
        <div className="card hero" style={{ gridRow: 'span 2' }}>
          <h3>Точка безубыточности</h3>
          <Gauge
            value={d.progress}
            label="прогресс к свободе"
            sublabel={`${fmt.usd(d.current_capital)} из ${fmt.usd(d.target_capital)}`}
          />
        </div>
        <div className="card">
          <h3>Цель (правило {Math.round(d.swr * 100)}%)</h3>
          <div className="big">{fmt.usd(d.target_capital)}</div>
          <div className="sub">капитал, покрывающий базовые расходы</div>
        </div>
        <div className="card">
          <h3>Текущий капитал</h3>
          <div className="big">{fmt.usd(d.current_capital)}</div>
          <div className="sub">портфель {fmt.usd(d.portfolio_value_usd)} + кэш</div>
        </div>
        <div className="card">
          <h3>Пассивный доход</h3>
          <div className="big">{fmt.usd(d.passive_income_monthly)}<span className="sub"> /мес</span></div>
          <div className="sub">
            нужно {fmt.usd(d.monthly_expenses)} — не хватает{' '}
            <span className={d.gap_monthly > 0 ? 'down' : 'up'}>{fmt.usd(d.gap_monthly)}</span>
          </div>
        </div>
        <div className="card">
          <h3>До свободы</h3>
          <div className="big">
            {d.years_to_target_base != null ? `${d.years_to_target_base} лет` : '—'}
          </div>
          <div className="sub">
            при текущем взносе, {(d.base_nominal_return * 100).toFixed(0)}% номинальных
            (~{(d.base_real_return * 100).toFixed(1)}% сверх инфляции)
          </div>
        </div>
      </div>

      <div className="cards" style={{ gridTemplateColumns: '1fr 1fr', marginTop: 8 }}>
        <div className="card">
          <h3>
            Сценарии: взнос × номинальная доходность → лет до цели{' '}
            <span className="muted">
              (цель в сегодняшних деньгах, рост за вычетом инфляции {(d.inflation * 100).toFixed(0)}%)
            </span>
          </h3>
          <table className="grid">
            <thead>
              <tr>
                <th>Взнос/мес</th>
                {d.scenarios[0] &&
                  Object.keys(d.scenarios[0].years).map((r) => <th key={r}>{r}</th>)}
              </tr>
            </thead>
            <tbody>
              {d.scenarios.map((s) => (
                <tr key={s.contribution}>
                  <td>{fmt.usd(s.contribution)}</td>
                  {Object.entries(s.years).map(([r, y]) => (
                    <td key={r}>{y != null ? `${y} л` : '>100 л'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Базовые расходы, /мес</h3>
          <table className="grid">
            <tbody>
              {Object.entries(d.expenses_breakdown).map(([k, v]) => (
                <tr key={k}>
                  <td>{EXPENSE_LABELS[k] ?? k}</td>
                  <td>{fmt.usd(v)}</td>
                </tr>
              ))}
              <tr>
                <td><b>Итого</b></td>
                <td><b>{fmt.usd(d.monthly_expenses)}</b></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className="disclaimer">{d.disclaimer}</div>
    </div>
  )
}
