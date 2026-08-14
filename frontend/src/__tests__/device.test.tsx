import { vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  initialDeviceState, reduceDeviceState, applyStatus, DeviceState,
} from '../lib/deviceState'
import DeviceIllustration from '../components/DeviceIllustration'
import DeviceView from '../views/DeviceView'

// ── reducer ──────────────────────────────────────────────────────────

const SNAPSHOT = {
  device_id: 'sim-01', type: 'heartbeat', trigger: 'periodic',
  seq: 1, uptime_s: 10,
  sensors: { temp_c: 24.5, humidity_pct: 41, light: 612, motion: false },
  actuators: { fan: false, servo_deg: 0, led: { r: 0, g: 0, b: 0 },
               buzzer: false, oled: ['hello', 'world'] },
}

test('snapshot message replaces sensors and actuators and marks online', () => {
  const s = reduceDeviceState(initialDeviceState,
    { type: 'snapshot', data: SNAPSHOT })
  expect(s.online).toBe(true)
  expect(s.sensors.temp_c).toBe(24.5)
  expect(s.actuators.oled).toEqual(['hello', 'world'])
})

test('actuator ack applies set_fan, set_servo and set_led optimistically', () => {
  let s: DeviceState = initialDeviceState
  s = reduceDeviceState(s, { type: 'actuator',
    data: { cmd_id: 'c1', ok: true, action: 'set_fan', args: { on: true } } })
  s = reduceDeviceState(s, { type: 'actuator',
    data: { cmd_id: 'c2', ok: true, action: 'set_servo', args: { angle: 45 } } })
  s = reduceDeviceState(s, { type: 'actuator',
    data: { cmd_id: 'c3', ok: true, action: 'set_led', args: { color: 'red' } } })
  expect(s.actuators.fan).toBe(true)
  expect(s.actuators.servo_deg).toBe(45)
  expect(s.actuators.led).toEqual({ r: 255, g: 0, b: 0 })
})

test('servo angle is clamped to 0-90', () => {
  const s = reduceDeviceState(initialDeviceState, { type: 'actuator',
    data: { cmd_id: 'c1', ok: true, action: 'set_servo', args: { angle: 180 } } })
  expect(s.actuators.servo_deg).toBe(90)
})

test('failed ack and unknown action leave state unchanged', () => {
  const failed = reduceDeviceState(initialDeviceState, { type: 'actuator',
    data: { cmd_id: 'c1', ok: false, action: 'set_fan', args: { on: true } } })
  expect(failed.actuators.fan).toBe(false)
  const unknown = reduceDeviceState(initialDeviceState, { type: 'actuator',
    data: { cmd_id: 'c2', ok: true, action: 'self_destruct', args: {} } })
  expect(unknown).toEqual(initialDeviceState)
})

test('buzzer action starts a transient buzz window', () => {
  const s = reduceDeviceState(initialDeviceState, { type: 'actuator',
    data: { cmd_id: 'c1', ok: true, action: 'buzzer', args: { pattern: 'short' } } },
    1000)
  expect(s.buzzerUntil).toBe(1000 + 3000)
})

test('display_text updates the oled lines', () => {
  const s = reduceDeviceState(initialDeviceState, { type: 'actuator',
    data: { cmd_id: 'c1', ok: true, action: 'display_text',
            args: { line1: 'MOTION!', line2: '02:00' } } })
  expect(s.actuators.oled).toEqual(['MOTION!', '02:00'])
})

test('applyStatus seeds state from /status response', () => {
  const s = applyStatus(initialDeviceState, {
    device: { online: true },
    sensors: { temp_c: 22, humidity_pct: 40, light: 500, motion: 0 },
    actuators: SNAPSHOT.actuators,
  })
  expect(s.online).toBe(true)
  expect(s.sensors.light).toBe(500)
  expect(s.actuators.oled).toEqual(['hello', 'world'])
})

// ── illustration ─────────────────────────────────────────────────────

const BASE: DeviceState = {
  online: true,
  sensors: { temp_c: 24.5, humidity_pct: 41, light: 612, motion: false },
  actuators: { fan: false, servo_deg: 0, led: { r: 0, g: 0, b: 0 },
               buzzer: false, oled: ['GrokGuardian', 'idle'] },
  buzzerUntil: 0,
}

function renderDevice(overrides: Partial<DeviceState> = {}) {
  const state = { ...BASE, ...overrides }
  return render(
    <DeviceIllustration sensors={state.sensors} actuators={state.actuators}
      buzzerActive={state.buzzerUntil > 0} />)
}

test('renders oled lines and sensor readouts', () => {
  renderDevice()
  expect(screen.getByTestId('oled-line1').textContent).toBe('GrokGuardian')
  expect(screen.getByTestId('oled-line2').textContent).toBe('idle')
  expect(screen.getByText(/24\.5/)).toBeTruthy()
  expect(screen.getByText(/612/)).toBeTruthy()
})

test('fan rotor is style-rotated by the momentum hook, not animate-spin', () => {
  renderDevice({ actuators: { ...BASE.actuators, fan: true } })
  const rotor = screen.getByTestId('fan-rotor')
  expect(rotor.classList.contains('animate-spin')).toBe(false)
  expect(rotor.style.transform).toContain('rotate(')
  expect(rotor.style.transformOrigin).toBe('center')
})

test('louver transform is style-based with a transition', () => {
  renderDevice({ actuators: { ...BASE.actuators, servo_deg: 45 } })
  const louver = screen.getByTestId('louver')
  expect(louver.style.transform).toContain('rotate(-45deg)')
  expect(louver.style.transition).toContain('transform')
})

test('led glows its rgb color when on', () => {
  renderDevice({ actuators: { ...BASE.actuators, led: { r: 255, g: 0, b: 0 } } })
  expect(screen.getByTestId('led').getAttribute('fill')).toBe('rgb(255,0,0)')
})

test('buzzer waves appear only while the buzz window is active', () => {
  const { unmount } = renderDevice()
  expect(screen.queryByTestId('buzzer-waves')).toBeNull()
  unmount()
  renderDevice({ buzzerUntil: Date.now() + 3000 })
  expect(screen.getByTestId('buzzer-waves')).toBeTruthy()
})

test('motion badge lights when motion is detected', () => {
  renderDevice({ sensors: { ...BASE.sensors, motion: true } })
  expect(screen.getByTestId('motion-badge').getAttribute('class'))
    .toContain('text-warning')
})

test('thermometer fill height follows tempFraction', () => {
  // 27.5°C → frac 0.5 → half of the 60px tube
  renderDevice({ sensors: { ...BASE.sensors, temp_c: 27.5 } })
  const fill = screen.getByTestId('thermo-fill')
  expect(Number(fill.getAttribute('height'))).toBeCloseTo(30)
})

test('thermometer is empty when temp is null', () => {
  renderDevice({ sensors: { ...BASE.sensors, temp_c: null } })
  expect(Number(screen.getByTestId('thermo-fill').getAttribute('height')))
    .toBe(0)
})

test('light arc sweep follows lightFraction', () => {
  renderDevice({ sensors: { ...BASE.sensors, light: 4095 } })
  const arc = screen.getByTestId('light-arc')
  expect(Number(arc.style.strokeDashoffset)).toBeCloseTo(0)
})

test('light arc is fully empty at zero or null light', () => {
  // semicircle r=24 has length ≈ 75.4, so offset 75.4 = nothing lit
  const { unmount } = renderDevice({ sensors: { ...BASE.sensors, light: 0 } })
  expect(Number(screen.getByTestId('light-arc').style.strokeDashoffset))
    .toBeCloseTo(75.4, 0)
  unmount()
  renderDevice({ sensors: { ...BASE.sensors, light: null } })
  expect(Number(screen.getByTestId('light-arc').style.strokeDashoffset))
    .toBeCloseTo(75.4, 0)
})

test('humidity droplet fill follows humidityFraction', () => {
  renderDevice({ sensors: { ...BASE.sensors, humidity_pct: 50 } })
  const fill = screen.getByTestId('humidity-fill')
  expect(Number(fill.getAttribute('height'))).toBeCloseTo(14) // 0.5 * 28px
})

test('pir ripple shows only while motion is detected', () => {
  const { unmount } = renderDevice()
  expect(screen.queryByTestId('pir-ripple')).toBeNull()
  unmount()
  renderDevice({ sensors: { ...BASE.sensors, motion: true } })
  expect(screen.getByTestId('pir-ripple')).toBeTruthy()
})

// ── view ─────────────────────────────────────────────────────────────

vi.mock('../lib/api', () => ({
  api: {
    getStatus: () => Promise.resolve({
      device: { online: true },
      sensors: { temp_c: 24.5, humidity_pct: 41, light: 612, motion: 0 },
      actuators: SNAPSHOT.actuators,
      last_seen: new Date().toISOString(),
    }),
    simScenario: vi.fn(), simEvent: vi.fn(),
  },
}))
vi.mock('../lib/ws', () => ({ useGatewayWS: () => ({ connected: true }) }))

test('device view renders illustration and sim controls', async () => {
  render(<DeviceView />)
  expect(await screen.findByText(/GrokGuardian/)).toBeTruthy()
  expect(screen.getByRole('button', { name: /heat spike/i })).toBeTruthy()
  expect(screen.getByRole('button', { name: /motion/i })).toBeTruthy()
})

test('device view feeds sensor history to the illustration sparklines', async () => {
  render(<DeviceView />)
  // sparkline strip renders (empty until WS snapshots arrive — the mocked
  // useGatewayWS never delivers messages, so just the container testids)
  expect(await screen.findByTestId('spark-temp')).toBeTruthy()
  expect(screen.getByTestId('spark-humidity')).toBeTruthy()
  expect(screen.getByTestId('spark-light')).toBeTruthy()
})
