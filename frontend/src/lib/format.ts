export const fmtTemp = (v: number | null | undefined) =>
  v == null ? '—' : `${v.toFixed(1)}°C`
export const fmtPct = (v: number | null | undefined) =>
  v == null ? '—' : `${v.toFixed(0)}%`
export const fmtTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleTimeString() : '—'
