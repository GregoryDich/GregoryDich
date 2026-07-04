import type { DockviewApi, DockviewReadyEvent, IDockviewPanelProps } from 'dockview'
import { themeAbyss } from 'dockview'
import { DockviewReact } from 'dockview-react'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import Palette, { type Command } from './components/Palette'
import AlertsScreen from './screens/AlertsScreen'
import FreedomScreen from './screens/FreedomScreen'
import MacroScreen from './screens/MacroScreen'
import MarketsScreen from './screens/MarketsScreen'
import Onboarding from './screens/Onboarding'
import PortfolioScreen from './screens/PortfolioScreen'

const SCREENS: Record<string, { title: string; component: React.FC }> = {
  freedom: { title: 'FIRE · Свобода', component: FreedomScreen },
  markets: { title: 'WEI · Рынки', component: MarketsScreen },
  portfolio: { title: 'PORT · Портфель', component: PortfolioScreen },
  macro: { title: 'ECO · Макро', component: MacroScreen },
  alerts: { title: 'ALRT · Алерты', component: AlertsScreen },
}

/** Ошибка одной панели не должна ронять весь терминал. */
class PanelBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) {
    return { error }
  }
  render() {
    if (this.state.error) {
      return (
        <div className="screen">
          <div className="card">
            <h3>Панель упала</h3>
            <div className="down mono">{String(this.state.error)}</div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const panelComponents = Object.fromEntries(
  Object.entries(SCREENS).map(([id, s]) => [
    id,
    (_: IDockviewPanelProps) => {
      const C = s.component
      return (
        <PanelBoundary>
          <C />
        </PanelBoundary>
      )
    },
  ]),
)

export default function App() {
  const apiRef = useRef<DockviewApi | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [needOnboarding, setNeedOnboarding] = useState(false)
  const [dataMode, setDataMode] = useState('')
  const [clock, setClock] = useState('')

  useEffect(() => {
    api.freedom().then((f) => setNeedOnboarding(!f.onboarded)).catch(() => {})
    api.overview().then((r) => setDataMode(r.status.mode)).catch(() => {})
    const t = setInterval(
      () => setClock(new Date().toLocaleTimeString('ru-RU', { hour12: false })),
      1000,
    )
    return () => clearInterval(t)
  }, [])

  const openScreen = useCallback((id: string) => {
    const dv = apiRef.current
    if (!dv) return
    const existing = dv.getPanel(id)
    if (existing) {
      existing.api.setActive()
      return
    }
    dv.addPanel({ id, component: id, title: SCREENS[id].title })
  }, [])

  const onReady = (e: DockviewReadyEvent) => {
    apiRef.current = e.api
    // Стартовая раскладка: Свобода — главный экран, рядом рынки, ниже — портфель/макро
    e.api.addPanel({ id: 'freedom', component: 'freedom', title: SCREENS.freedom.title })
    e.api.addPanel({
      id: 'markets', component: 'markets', title: SCREENS.markets.title,
      position: { referencePanel: 'freedom', direction: 'right' },
    })
    e.api.addPanel({
      id: 'portfolio', component: 'portfolio', title: SCREENS.portfolio.title,
      position: { referencePanel: 'freedom', direction: 'below' },
    })
    e.api.addPanel({
      id: 'macro', component: 'macro', title: SCREENS.macro.title,
      position: { referencePanel: 'portfolio', direction: 'within' },
    })
    e.api.addPanel({
      id: 'alerts', component: 'alerts', title: SCREENS.alerts.title,
      position: { referencePanel: 'portfolio', direction: 'within' },
    })
    e.api.getPanel('portfolio')?.api.setActive()
    e.api.getPanel('freedom')?.api.setActive()
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const commands: Command[] = [
    { code: 'FIRE', title: 'Свобода — точка безубыточности', run: () => openScreen('freedom') },
    { code: 'WEI', title: 'Обзор рынков', run: () => openScreen('markets') },
    { code: 'PORT', title: 'Портфель и риск', run: () => openScreen('portfolio') },
    { code: 'ECO', title: 'Макроэкономика: США + Израиль', run: () => openScreen('macro') },
    { code: 'ALRT', title: 'Алерты и дайджест', run: () => openScreen('alerts') },
    {
      code: 'REFR', title: 'Обновить рыночные данные', hint: 'live → фолбэк → demo',
      run: () => { fetch('/api/markets/refresh', { method: 'POST' }); fetch('/api/macro/refresh', { method: 'POST' }) },
    },
    { code: 'DIG', title: 'Отправить дайджест сейчас', run: () => api.digest() },
  ]

  return (
    <div className="app">
      <div className="topbar">
        <div className="logo">
          ⚡ JARVIS<span>персональный экономический менеджер</span>
        </div>
        <div className="spacer" />
        {dataMode && (
          <span className={`badge ${dataMode}`} title="Источник данных: live / mixed / demo">
            {dataMode === 'demo' ? 'ДЕМО-ДАННЫЕ' : dataMode.toUpperCase()}
          </span>
        )}
        <span className="mono muted">{clock}</span>
        <span className="kbd" onClick={() => setPaletteOpen(true)}>⌘K команды</span>
      </div>
      <div className="workspace">
        <DockviewReact components={panelComponents} onReady={onReady} theme={themeAbyss} />
      </div>
      <Palette commands={commands} open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {needOnboarding && (
        <Onboarding
          onDone={() => {
            setNeedOnboarding(false)
            location.reload()
          }}
        />
      )}
    </div>
  )
}
