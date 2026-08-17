import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import { useSensorHistory } from '../lib/useSensorHistory'
import Gauge from '../components/Gauge'
import Sparkline from '../components/Sparkline'
import StatCard from '../components/StatCard'
import ActuatorCard from '../components/ActuatorCard'
import SimControls from '../components/SimControls'

type Sensors = { temp_c: number | null; humidity_pct: number | null;
                 light: number | null; motion: number | boolean | null }

const STATUS_POLL_MS = 30_000

export default function RoomView() {
  const [sensors, setSensors] = useState<Sensors | null>(null)
  const [actuators, setActuators] = useState<any>(null)
  const [online, setOnline] = useState(false)
  const { history, handleMessage } = useSensorHistory()

  const onMessage = useCallback((msg: GatewayMessage) => {
    if (msg.type === 'snapshot') {
      const s = msg.data.sensors, d = msg.data
      setSensors(s)
      setActuators(d.actuators)
      setOnline(true)
      handleMessage(msg)
    }
  }, [handleMessage])

  const { connected } = useGatewayWS(onMessage)

  // Seed from /status on mount (including actuators, which the WS only
  // shows after the next snapshot), then re-poll slowly so a device going
  // stale flips the badge to offline without a page refresh.
  useEffect(() => {
    let stop = false
    const load = () => api.getStatus().then((st) => {
      if (stop) return
      setOnline(st.device.online)
      if (st.sensors) setSensors(st.sensors)
      if (st.actuators) setActuators(st.actuators)
    }).catch(() => { if (!stop) setOnline(false) })
    load()
    const t = setInterval(load, STATUS_POLL_MS)
    return () => { stop = true; clearInterval(t) }
  }, [])

  return (
    <div className="space-y-4">
      {/* controls row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-sm px-2 py-1 rounded-full ${
          connected && online ? 'bg-good/20 text-good' : 'bg-serious/20 text-serious'}`}>
          ● {connected && online ? 'live' : 'offline'}
        </span>
        <SimControls />
      </div>

      {/* gauges row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Temperature">
          <Gauge label="0–40 scale" value={sensors?.temp_c ?? null} min={0} max={40}
                 unit="°C" color="var(--color-temp)" />
          <Sparkline data={history.t} color="var(--color-temp)" />
        </StatCard>
        <StatCard title="Humidity">
          <Gauge label="0–100 scale" value={sensors?.humidity_pct ?? null} min={0} max={100}
                 unit="%" color="var(--color-humidity)" />
          <Sparkline data={history.h} color="var(--color-humidity)" />
        </StatCard>
        <StatCard title="Light">
          <Gauge label="0–4095 ADC" value={sensors?.light ?? null} min={0} max={4095}
                 unit="" color="var(--color-light)" />
          <Sparkline data={history.l} color="var(--color-light)" />
        </StatCard>
      </div>

      {/* bottom row: actuators + motion */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StatCard title="Actuators">
          <ActuatorCard name="Fan" icon="🌀"
            state={actuators?.fan ? 'on' : 'off'} active={!!actuators?.fan} />
          <ActuatorCard name="Vent servo" icon="🪟"
            state={`${actuators?.servo_deg ?? 0}°`}
            active={(actuators?.servo_deg ?? 0) > 0} />
          <ActuatorCard name="Status LED" icon="💡"
            state={ledText(actuators?.led)} active={ledOn(actuators?.led)} />
          <ActuatorCard name="Buzzer" icon="🔔"
            state={actuators?.buzzer ? 'sounding' : 'silent'}
            active={!!actuators?.buzzer} />
        </StatCard>
        <StatCard title="Room display (OLED)">
          <div className="font-mono bg-bg rounded-md p-3 text-center text-ink">
            <div>{actuators?.oled?.[0] ?? '—'}</div>
            <div>{actuators?.oled?.[1] ?? ''}</div>
          </div>
          <div className="mt-3 text-ink2 text-sm">
            Motion: <span className="text-ink">
              {sensors?.motion ? 'detected' : 'none'}</span>
          </div>
        </StatCard>
      </div>
    </div>
  )
}

function ledOn(led: any): boolean {
  return !!led && (led.r > 0 || led.g > 0 || led.b > 0)
}
function ledText(led: any): string {
  if (!ledOn(led)) return 'off'
  if (led.r > 200 && led.g > 200 && led.b > 200) return 'white'
  if (led.r > 200 && led.g > 150) return 'amber'
  if (led.r > 0) return 'red'
  if (led.g > 0) return 'green'
  return 'blue'
}
