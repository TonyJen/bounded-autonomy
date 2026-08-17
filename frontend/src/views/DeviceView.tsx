import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import {
  applyStatus, initialDeviceState, reduceDeviceState, BUZZER_WINDOW_MS,
} from '../lib/deviceState'
import StatCard from '../components/StatCard'
import DeviceIllustration from '../components/DeviceIllustration'
import SimControls from '../components/SimControls'
import { useSensorHistory } from '../lib/useSensorHistory'

export default function DeviceView() {
  const [state, setState] = useState(initialDeviceState)
  const [, forceRender] = useState(0)
  const buzzTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { history, handleMessage } = useSensorHistory()

  const onMessage = useCallback((msg: GatewayMessage) => {
    setState((s) => reduceDeviceState(s, msg))
    handleMessage(msg)
    // re-render when the transient buzzer window expires
    if (msg.type === 'actuator' && msg.data?.ok && msg.data?.action === 'buzzer') {
      if (buzzTimer.current) clearTimeout(buzzTimer.current)
      buzzTimer.current = setTimeout(
        () => forceRender((n) => n + 1), BUZZER_WINDOW_MS)
    }
  }, [handleMessage])

  // clear the pending buzzer-expiry timer on unmount
  useEffect(() => () => {
    if (buzzTimer.current) clearTimeout(buzzTimer.current)
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
        <SimControls />
      </div>

      <StatCard title="Simulated device">
        <div className={live ? '' : 'opacity-60'}>
          <DeviceIllustration sensors={state.sensors} actuators={state.actuators}
            buzzerActive={state.buzzerUntil > Date.now()} history={history} />
        </div>
      </StatCard>
    </div>
  )
}
