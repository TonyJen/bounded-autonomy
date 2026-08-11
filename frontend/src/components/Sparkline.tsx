export default function Sparkline({ data, color, height = 40 }: {
  data: number[]; color: string; height?: number
}) {
  if (data.length < 2) return <div style={{ height }} className="w-full" />
  const w = 100, h = 20
  const min = Math.min(...data), max = Math.max(...data)
  const span = max - min || 1
  const pts = data.map((v, i) =>
    `${(i / (data.length - 1)) * w},${h - ((v - min) / span) * h}`)
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
         className="w-full" style={{ height }}>
      <polyline points={pts.join(' ')} fill="none" stroke={color}
                strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}
