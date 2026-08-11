import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import { fmtTemp } from '../lib/format'
import Gauge from '../components/Gauge'
import Sparkline from '../components/Sparkline'
import StatCard from '../components/StatCard'
import ActuatorCard from '../components/ActuatorCard'

type Sensors = { temp_c: number | null; humidity_pct: number | null;
                 light: number | null; motion: number | boolean | null }

const SCENARIOS = [
  ['heat_spike', 'Heat spike'], ['night_intruder', 'Night intruder'],
  ['quiet_afternoon', 'Quiet afternoon'], ['sensor_failure', 'Sensor failure'],
] as const
const EVENTS = [['motion', 'Motion'], ['heat', 'Heat'], ['dark', 'Dark']] as const

export default function RoomView() {
  const [sensors, setSensors] = useState<Sensors | null>(null)
  const [actuators, setActuators] = useState<any>(null)
  const [online, setOnline] = useState(false)
  const histRef = useRef<{ t: number[]; h: number[]; l: number[] }>(
    { t: [], h: [], l: [] })
  const [, forceRender] = useState(0)

  const onMessage = useCallback((msg: GatewayMessage) => {
    if (msg.type === 'snapshot') {
      const s = msg.data.sensors, d = msg.data
      setSensors(s)
      setActuators(d.actuators)
      setOnline(true)
      const h = histRef.current
      if (s.temp_c != null) {
        h.t = [...h.t.slice(-59), s.temp_c]
        h.h = [...h.h.slice(-59), s.humidity_pct ?? 0]
        h.l = [...h.l.slice(-59), s.light ?? 0]
        forceRender((n) => n + 1)
      }
    }
  }, [])

  const { connected } = useGatewayWS(onMessage)

  useEffect(() => {
    api.getStatus().then((st) => {
      setOnline(st.device.online)
      setSensors(st.sensors)
    }).catch(() => setOnline(false))
  }, [])

  return (
    <div className="space-y-4">
      {/* controls row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-sm px-2 py-1 rounded-full ${
          connected && online ? 'bg-good/20 text-good' : 'bg-serious/20 text-serious'}`}>
          ● {connected && online ? 'live' : 'offline'}
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

      {/* gauges row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Temperature">
          <Gauge label="°C" value={sensors?.temp_c ?? null} min={0} max={40}
                 unit="°C" color="var(--color-temp)" />
          <Sparkline data={histRef.current.t} color="var(--color-temp)" />
        </StatCard>
        <StatCard title="Humidity">
          <Gauge label="%" value={sensors?.humidity_pct ?? null} min={0} max={100}
                 unit="%" color="var(--color-humidity)" />
          <Sparkline data={histRef.current.h} color="var(--color-humidity)" />
        </StatCard>
        <StatCard title="Light">
          <Gauge label="ADC" value={sensors?.light ?? null} min={0} max={4095}
                 unit="" color="var(--color-light)" />
          <Sparkline data={histRef.current.l} color="var(--color-light)" />
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
