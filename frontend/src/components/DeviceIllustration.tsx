import { Actuators, Sensors } from '../lib/deviceState'
import { useFanMomentum } from '../lib/useFanMomentum'

function fmt(v: number | null, suffix = ''): string {
  return v == null ? '—' : `${v}${suffix}`
}

/** SVG rendering of the simulated device: OLED, LED, buzzer, fan and
 *  servo louver on an ESP32-style board, plus sensor readouts. */
export default function DeviceIllustration({ sensors, actuators, buzzerActive }: {
  sensors: Sensors
  actuators: Actuators
  buzzerActive: boolean
}) {
  const led = actuators.led
  const ledOn = led.r > 0 || led.g > 0 || led.b > 0
  const motion = !!sensors.motion
  const deg = actuators.servo_deg
  const fanAngle = useFanMomentum(actuators.fan)

  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg viewBox="0 0 400 340" className="w-full max-w-md" role="img"
           aria-label="device illustration">
        {/* board */}
        <rect x="20" y="40" width="360" height="280" rx="14"
              fill="var(--color-bg)" stroke="var(--color-cardborder)"
              strokeWidth="2" />
        {[[38, 58], [362, 58], [38, 302], [362, 302]].map(([x, y]) => (
          <circle key={`${x},${y}`} cx={x} cy={y} r="5"
                  fill="none" stroke="var(--color-cardborder)" strokeWidth="2" />
        ))}
        <text x="200" y="66" textAnchor="middle" fontSize="12"
              fill="var(--color-muted)">GrokGuardian · sim-01</text>

        {/* OLED */}
        <rect x="50" y="84" width="170" height="66" rx="4" fill="#0B0B18"
              stroke="var(--color-cardborder)" strokeWidth="2" />
        <text data-testid="oled-line1" x="60" y="112" fontSize="15"
              fontFamily="monospace" fill="#9FD8FF">{actuators.oled[0]}</text>
        <text data-testid="oled-line2" x="60" y="136" fontSize="15"
              fontFamily="monospace" fill="#9FD8FF">{actuators.oled[1]}</text>

        {/* RGB LED */}
        {ledOn && (
          <circle cx="310" cy="110" r="20" opacity="0.25"
                  fill={`rgb(${led.r},${led.g},${led.b})`} />
        )}
        <circle data-testid="led" cx="310" cy="110" r="10"
                fill={ledOn ? `rgb(${led.r},${led.g},${led.b})`
                            : 'var(--color-cardborder)'}
                stroke="var(--color-cardborder)" strokeWidth="2" />
        <text x="310" y="140" textAnchor="middle" fontSize="10"
              fill="var(--color-muted)">LED</text>

        {/* buzzer */}
        <circle cx="310" cy="180" r="12" fill="var(--color-card)"
                stroke="var(--color-cardborder)" strokeWidth="2" />
        <circle cx="310" cy="180" r="4" fill="var(--color-cardborder)" />
        {buzzerActive && (
          <g data-testid="buzzer-waves" className="animate-pulse"
             stroke="var(--color-warning)" strokeWidth="2" fill="none">
            <path d="M328 172 a10 10 0 0 1 0 16" />
            <path d="M336 166 a18 18 0 0 1 0 28" />
            <path d="M344 160 a26 26 0 0 1 0 40" />
          </g>
        )}
        <text x="310" y="208" textAnchor="middle" fontSize="10"
              fill="var(--color-muted)">BUZZER</text>

        {/* fan */}
        <circle cx="110" cy="240" r="46" fill="var(--color-card)"
                stroke="var(--color-cardborder)" strokeWidth="2" />
        <g data-testid="fan-rotor"
           style={{ transform: `rotate(${fanAngle}deg)`,
                    transformBox: 'fill-box', transformOrigin: 'center' }}>
          {[0, 90, 180, 270].map((a) => (
            <ellipse key={a} cx="110" cy="218" rx="9" ry="22"
                     fill="var(--color-temp)" opacity="0.8"
                     transform={`rotate(${a} 110 240)`} />
          ))}
          <circle cx="110" cy="240" r="7" fill="var(--color-ink2)" />
        </g>
        <text x="110" y="302" textAnchor="middle" fontSize="10"
              fill="var(--color-muted)">FAN</text>

        {/* servo vent louver: flap hinged at left edge, 0° closed / 90° open */}
        <rect x="230" y="222" width="112" height="56" rx="4"
              fill="none" stroke="var(--color-cardborder)" strokeWidth="2" />
        <rect data-testid="louver" x="236" y="228" width="100" height="44" rx="2"
              fill="var(--color-humidity)" opacity="0.7"
              transform={`rotate(${-deg} 236 250)`} />
        <text x="286" y="302" textAnchor="middle" fontSize="10"
              fill="var(--color-muted)">VENT {deg}°</text>

        {/* PIR motion badge */}
        <circle data-testid="motion-badge" cx="352" cy="240" r="10"
                fill="currentColor"
                className={motion ? 'text-warning' : 'text-cardborder'} />
        <text x="352" y="262" textAnchor="middle" fontSize="10"
              fill="var(--color-muted)">PIR</text>
      </svg>

      {/* sensor readouts */}
      <div className="space-y-2 text-sm min-w-36">
        <div className="text-ink2">Temperature
          <div className="text-ink text-lg font-mono">
            {fmt(sensors.temp_c, ' °C')}</div></div>
        <div className="text-ink2">Humidity
          <div className="text-ink text-lg font-mono">
            {fmt(sensors.humidity_pct, ' %')}</div></div>
        <div className="text-ink2">Light
          <div className="text-ink text-lg font-mono">
            {fmt(sensors.light)}</div></div>
        <div className="text-ink2">Motion
          <div className={`text-lg font-mono ${motion ? 'text-warning' : 'text-ink'}`}>
            {sensors.motion == null ? '—' : motion ? 'detected' : 'none'}</div></div>
      </div>
    </div>
  )
}
