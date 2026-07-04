import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { Candle } from '../api'

/** Свечной график на TradingView lightweight-charts (Apache-2.0, атрибуция обязательна). */
export default function PriceChart({ candles }: { candles: Candle[] }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#7d8698',
        attributionLogo: true, // требование лицензии TradingView
      },
      grid: {
        vertLines: { color: '#141a26' },
        horzLines: { color: '#141a26' },
      },
      timeScale: { borderColor: '#1e2635' },
      rightPriceScale: { borderColor: '#1e2635' },
      autoSize: true,
    })
    chartRef.current = chart
    return () => chart.remove()
  }, [])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return
    // пересоздаём серию под новые данные (символ сменился)
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#2fbf71',
      downColor: '#e5484d',
      wickUpColor: '#2fbf71',
      wickDownColor: '#e5484d',
      borderVisible: false,
    })
    series.setData(
      candles.map((c) => ({
        time: (Date.parse(c.time) / 1000) as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    )
    chart.timeScale().fitContent()
    return () => chart.removeSeries(series)
  }, [candles])

  return <div ref={ref} className="fill" style={{ minHeight: 220 }} />
}
