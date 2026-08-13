import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import {
  applyStatus, initialDeviceState, reduceDeviceState, BUZZER_WINDOW_MS,
} from '../lib/deviceState'
import StatCard from '../components/StatCard'
import DeviceIllustration from '../components/DeviceIllustration'

const SCENARIOS = [
  ['heat_spike', 'Heat spike'], ['night_intruder', 'Night intruder'],
  ['quiet_afternoon', 'Quiet afternoon'], ['sensor_failure', 'Sensor failure'],
] as const
const EVENTS = [['motion', 'Motion'], ['heat', 'Heat'], ['dark', 'Dark']] as const

export default function DeviceView() {
  const [state, setState] = useState(initialDeviceState)
  const [, forceRender] = useState(0)
  const buzzTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const onMessage = useCallback((msg: GatewayMessage) => {
    setState((s) => reduceDeviceState(s, msg))
    // re-render when the transient buzzer window expires
    if (msg.type === 'actuator' && msg.data?.ok && msg.data?.action === 'buzzer') {
      if (buzzTimer.current) clearTimeout(buzzTimer.current)
      buzzTimer.current = setTimeout(
        () => forceRender((n) => n + 1), BUZZER_WINDOW_MS)
    }
  }, [])

  const { connected } = useGatewayWS(onMessage)

  useEffect(() => {
    api.getStatus()
      .then((st) => setState((s) => applyStatus(s, st)))
      .catch(() => {})
  }, [])

  const live = connected && state.online

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-sm px-2 py-1 rounded-full ${
          live ? 'bg-good/20 text-good' : 'bg-serious/20 text-serious'}`}>
          ● {live ? 'live' : 'offline'}
        </span>
        <span className="text-muted text-sm ml-2">Scenarios:</span>
        {SCENARIOS.map(([id, label]) => (
          <button key={id} onClick={() => api.simScenario(id)}
            className="px-3 py-1 rounded-md bg-card border border-cardborder
                       text-ink2 hover:text-ink text-sm">
            {label}
          </button>
        ))}
        <span className="text-muted text-sm ml-2">Events:</span>
        {EVENTS.map(([id, label]) => (
          <button key={id} onClick={() => api.simEvent(id)}
            className="px-3 py-1 rounded-md bg-card border border-cardborder
                       text-ink2 hover:text-ink text-sm">
            {label}
          </button>
        ))}
      </div>

      <StatCard title="Simulated device">
        <div className={live ? '' : 'opacity-60'}>
          <DeviceIllustration sensors={state.sensors} actuators={state.actuators}
            buzzerActive={state.buzzerUntil > Date.now()} />
        </div>
      </StatCard>
    </div>
  )
}
