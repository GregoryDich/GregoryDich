import { useEffect, useState } from 'react'
import { api, fmt, type Alert } from '../api'

/** Алерты: пороги цен → Telegram + резервный ntfy. */
export default function AlertsScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [form, setForm] = useState({ symbol: '', condition: 'above', level: '' })
  const [status, setStatus] = useState('')

  const load = () => {
    api.alerts().then((r) => setAlerts(r.alerts)).catch(console.error)
  }
  useEffect(load, [])

  const create = async () => {
    if (!form.symbol || !form.level) return
    await api.createAlert({ ...form, level: +form.level })
    setForm({ symbol: '', condition: 'above', level: '' })
    load()
  }

  return (
    <div className="screen">
      <div className="card" style={{ marginBottom: 8 }}>
        <h3>Новый алерт</h3>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <input placeholder="Тикер (SPY, BTC-USD…)" style={{ width: 150 }} value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} />
          <select value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })}>
            <option value="above">выше</option>
            <option value="below">ниже</option>
          </select>
          <input placeholder="Уровень" style={{ width: 100 }} value={form.level}
            onChange={(e) => setForm({ ...form, level: e.target.value })} />
          <button className="primary" onClick={create}>Создать</button>
          <button
            className="ghost"
            onClick={async () => {
              const r = await api.testAlert()
              setStatus(
                r.dry_run
                  ? 'Каналы не настроены — заполните TELEGRAM_BOT_TOKEN/NTFY_TOPIC в .env'
                  : `Отправлено в ${r.configured_channels} канал(а) ✅`,
              )
            }}
          >
            Тест доставки
          </button>
          <button
            className="ghost"
            onClick={async () => {
              await api.digest()
              setStatus('Дайджест собран и отправлен (см. Telegram/ntfy или лог)')
            }}
          >
            Дайджест сейчас
          </button>
        </div>
        {status && <div className="sub" style={{ marginTop: 6 }}>{status}</div>}
        <div className="sub" style={{ marginTop: 4 }}>
          Доставка: Telegram + резервный ntfy-топик — алерты переживут потерю любого одного канала.
        </div>
      </div>
      <div className="card">
        <h3>Алерты</h3>
        <table className="grid">
          <thead>
            <tr><th>Тикер</th><th>Условие</th><th>Статус</th><th>Сработал</th><th></th></tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td><b>{a.symbol}</b></td>
                <td>{a.condition === 'above' ? '≥' : '≤'} {fmt.num(a.level)}</td>
                <td>{a.active ? <span className="up">активен</span> : <span className="muted">погашен</span>}</td>
                <td className="muted">{a.last_triggered_at ?? '—'}</td>
                <td>
                  <button className="ghost" onClick={async () => { await api.deleteAlert(a.id); load() }}>✕</button>
                </td>
              </tr>
            ))}
            {alerts.length === 0 && <tr><td colSpan={5} className="muted">Алертов пока нет</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
