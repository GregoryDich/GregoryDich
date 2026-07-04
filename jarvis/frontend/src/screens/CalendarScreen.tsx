import { useEffect, useState } from 'react'
import { api, type CalendarEvent } from '../api'

const KIND_META: Record<string, { icon: string; label: string }> = {
  dividend: { icon: '💰', label: 'Дивиденд' },
  earnings: { icon: '📊', label: 'Отчётность' },
  macro: { icon: '🌐', label: 'Макро' },
  cb: { icon: '🏦', label: 'ЦБ' },
}

/** CAL: календарь событий — отчётности, дивиденды, макро-релизы, решения ЦБ. */
export default function CalendarScreen() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [note, setNote] = useState('')
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    api.calendarEvents(45).then((r) => {
      setEvents(r.events)
      setNote(r.note)
    }).catch(console.error)
  }, [])

  const visible = events.filter((e) => filter === 'all' || e.kind === filter)
  const byDate = new Map<string, CalendarEvent[]>()
  for (const e of visible) {
    byDate.set(e.date, [...(byDate.get(e.date) ?? []), e])
  }

  return (
    <div className="screen">
      <div className="card">
        <h3>
          Календарь событий · 45 дней{' '}
          <span style={{ float: 'right', display: 'flex', gap: 6 }}>
            {['all', 'earnings', 'dividend', 'macro', 'cb'].map((k) => (
              <button key={k} className="ghost"
                style={{ color: filter === k ? 'var(--accent)' : undefined }}
                onClick={() => setFilter(k)}>
                {k === 'all' ? 'Все' : KIND_META[k].label}
              </button>
            ))}
          </span>
        </h3>
        {[...byDate.entries()].map(([date, items]) => (
          <div key={date} style={{ marginBottom: 10 }}>
            <div className="mono" style={{ color: 'var(--accent)', fontSize: 12, margin: '6px 0 4px' }}>
              {new Date(date).toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'long' })}
            </div>
            {items.map((e, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, padding: '3px 0', alignItems: 'baseline' }}>
                <span>{KIND_META[e.kind].icon}</span>
                <span style={{ fontWeight: e.importance === 'high' ? 600 : 400 }}>{e.title}</span>
                <span className="sub" style={{ marginLeft: 'auto' }}>{e.source}</span>
              </div>
            ))}
          </div>
        ))}
        {visible.length === 0 && <div className="muted">Событий нет</div>}
        <div className="disclaimer">{note}</div>
      </div>
    </div>
  )
}
