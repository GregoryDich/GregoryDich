import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'

/** Обёртка ECharts: тёмная палитра JARVIS, авторесайз под панель Dockview. */
export default function Echart({ option, height }: { option: echarts.EChartsOption; height?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!ref.current) return
    chart.current = echarts.init(ref.current)
    const ro = new ResizeObserver(() => chart.current?.resize())
    ro.observe(ref.current)
    return () => {
      ro.disconnect()
      chart.current?.dispose()
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(
      {
        backgroundColor: 'transparent',
        textStyle: { color: '#7d8698', fontSize: 11 },
        ...option,
      },
      { notMerge: true },
    )
  }, [option])

  return <div ref={ref} style={{ width: '100%', height: height ?? '100%' }} />
}

export const axisDefaults = {
  axisLine: { lineStyle: { color: '#1e2635' } },
  axisLabel: { color: '#7d8698', fontSize: 10 },
  splitLine: { lineStyle: { color: '#141a26' } },
}
