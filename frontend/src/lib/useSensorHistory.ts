import { useCallback, useState } from 'react'
import { GatewayMessage } from './ws'

export type SensorHistory = { t: number[]; h: number[]; l: number[] }

const CAP = 60

type SnapshotSensors = {
  temp_c: number | null
  humidity_pct: number | null
  light: number | null
}

/** Pure append: null temp skips the sample (sensor-failure snapshots don't
 *  pollute the charts); null humidity/light coerce to 0. Capped at 60. */
export function appendSnapshot(
  hist: SensorHistory, s: SnapshotSensors,
): SensorHistory {
  if (s.temp_c == null) return hist
  return {
    t: [...hist.t.slice(-(CAP - 1)), s.temp_c],
    h: [...hist.h.slice(-(CAP - 1)), s.humidity_pct ?? 0],
    l: [...hist.l.slice(-(CAP - 1)), s.light ?? 0],
  }
}

/** Rolling sensor history fed from gateway WS messages. Call handleMessage
 *  from the view's existing WS handler. */
export function useSensorHistory() {
  const [history, setHistory] = useState<SensorHistory>({ t: [], h: [], l: [] })
  const handleMessage = useCallback((msg: GatewayMessage) => {
    if (msg.type !== 'snapshot') return
    const s = msg.data?.sensors
    if (!s) return
    setHistory((h) => appendSnapshot(h, s))
  }, [])
  return { history, handleMessage }
}
