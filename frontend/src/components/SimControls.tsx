import { api } from '../lib/api'

const SCENARIOS = [
  ['heat_spike', 'Heat spike'], ['night_intruder', 'Night intruder'],
  ['quiet_afternoon', 'Quiet afternoon'], ['sensor_failure', 'Sensor failure'],
] as const
const EVENTS = [['motion', 'Motion'], ['heat', 'Heat'], ['dark', 'Dark']] as const

/** Scenario + event trigger buttons shared by RoomView and DeviceView. */
export default function SimControls() {
  return (
    <>
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
    </>
  )
}
