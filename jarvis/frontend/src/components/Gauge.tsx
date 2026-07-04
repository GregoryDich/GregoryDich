/** Радиальный датчик прогресса к точке свободы — hero-элемент экрана FIRE. */
export default function Gauge({ value, label, sublabel }: {
  value: number // 0..1+
  label: string
  sublabel?: string
}) {
  const pct = Math.max(0, Math.min(value, 1))
  const R = 84
  const CIRC = Math.PI * R // полукруг
  const dash = pct * CIRC

  return (
    <div className="gauge">
      <svg viewBox="0 0 200 118" role="img" aria-label={label}>
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#8a5a00" />
            <stop offset="100%" stopColor="#f5a623" />
          </linearGradient>
        </defs>
        <path
          d={`M 16 110 A ${R} ${R} 0 0 1 184 110`}
          fill="none" stroke="var(--border)" strokeWidth="12" strokeLinecap="round"
        />
        <path
          d={`M 16 110 A ${R} ${R} 0 0 1 184 110`}
          fill="none" stroke="url(#gaugeGrad)" strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${dash} ${CIRC}`}
          style={{ transition: 'stroke-dasharray 0.9s ease-out' }}
        />
        <text x="100" y="86" textAnchor="middle" className="gauge-value">
          {(value * 100).toFixed(1)}%
        </text>
        <text x="100" y="106" textAnchor="middle" className="gauge-label">
          {label}
        </text>
      </svg>
      {sublabel && <div className="sub" style={{ textAlign: 'center' }}>{sublabel}</div>}
    </div>
  )
}
