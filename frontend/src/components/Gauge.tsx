type Props = {
  label: string; value: number | null; min: number; max: number
  unit: string; color: string
}

export default function Gauge({ label, value, min, max, unit, color }: Props) {
  const pct = value == null ? 0 : Math.min(1, Math.max(0, (value - min) / (max - min)))
  // semicircle from 180°→0°; radius 40, center (50,50)
  const arc = (frac: number) => {
    const start = Math.PI, end = Math.PI * (1 - frac)
    const x1 = 50 + 40 * Math.cos(start), y1 = 50 + 40 * Math.sin(start)
    const x2 = 50 + 40 * Math.cos(end), y2 = 50 + 40 * Math.sin(end)
    const large = frac > 0.5 ? 1 : 0
    return `M ${x1} ${y1} A 40 40 0 ${large} 1 ${x2} ${y2}`
  }
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 100 55" className="w-full max-w-[160px]">
        <path d={arc(1)} fill="none" stroke="var(--color-cardborder)" strokeWidth="6"
              strokeLinecap="round" />
        {value != null && (
          <path d={arc(Math.max(pct, 0.02))} fill="none" stroke={color}
                strokeWidth="6" strokeLinecap="round" />
        )}
      </svg>
      <div className="text-3xl font-semibold text-ink -mt-6">
        {value == null ? '—' : value.toFixed(1)}
        <span className="text-base text-ink2 ml-1">{unit}</span>
      </div>
      <div className="text-muted text-sm">{label}</div>
    </div>
  )
}
