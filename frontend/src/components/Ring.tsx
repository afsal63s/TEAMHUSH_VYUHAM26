import type { ReactNode } from 'react'

// Circular progress ring with a centered label (mastery, scores).
export function Ring({
  pct,
  size,
  stroke,
  label,
  children,
}: {
  pct: number | null
  size: number
  stroke: number
  label?: string
  children?: ReactNode
}) {
  const r = (size - stroke) / 2 - 1
  const c = 2 * Math.PI * r
  const half = size / 2

  return (
    <div
      style={{ position: 'relative', width: size, height: size, flex: `0 0 ${size}px` }}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={half} cy={half} r={r} fill="none" stroke="#E4E9F0" strokeWidth={stroke} />
        {pct !== null && pct > 0 && (
          <circle
            cx={half}
            cy={half}
            r={r}
            fill="none"
            stroke="#0770C9"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${((c * pct) / 100).toFixed(1)} ${c.toFixed(1)}`}
            transform={`rotate(-90 ${half} ${half})`}
          />
        )}
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {children}
      </div>
    </div>
  )
}
