import { GatewayMessage } from './ws'

export type Sensors = {
  temp_c: number | null
  humidity_pct: number | null
  light: number | null
  motion: boolean | number | null
}

export type Actuators = {
  fan: boolean
  servo_deg: number
  led: { r: number; g: number; b: number }
  buzzer: boolean
  oled: string[]
}

export type DeviceState = {
  online: boolean
  sensors: Sensors
  actuators: Actuators
  /** ms timestamp until which the buzzer animation shows; 0 = silent.
   *  The sim latches buzzer=true in snapshots, so buzzing is event-driven. */
  buzzerUntil: number
}

export const BUZZER_WINDOW_MS = 3000

// mirrors simulator/physics.py LED_COLORS
const LED_COLORS: Record<string, { r: number; g: number; b: number }> = {
  off: { r: 0, g: 0, b: 0 }, red: { r: 255, g: 0, b: 0 },
  green: { r: 0, g: 255, b: 0 }, blue: { r: 0, g: 0, b: 255 },
  white: { r: 255, g: 255, b: 255 }, amber: { r: 255, g: 191, b: 0 },
}

export const initialDeviceState: DeviceState = {
  online: false,
  sensors: { temp_c: null, humidity_pct: null, light: null, motion: null },
  actuators: { fan: false, servo_deg: 0, led: { r: 0, g: 0, b: 0 },
               buzzer: false, oled: ['', ''] },
  buzzerUntil: 0,
}

export function reduceDeviceState(
  state: DeviceState, msg: GatewayMessage, now = Date.now(),
): DeviceState {
  if (msg.type === 'snapshot') {
    const d = msg.data ?? {}
    return { ...state, online: true,
             sensors: { ...state.sensors, ...(d.sensors ?? {}) },
             actuators: { ...state.actuators, ...(d.actuators ?? {}) } }
  }
  if (msg.type === 'actuator') {
    const { ok, action, args } = msg.data ?? {}
    if (!ok) return state
    const a = state.actuators
    switch (action) {
      case 'set_fan':
        return { ...state, actuators: { ...a, fan: !!args?.on } }
      case 'set_servo':
        return { ...state, actuators: { ...a,
          servo_deg: Math.max(0, Math.min(90, Math.round(args?.angle ?? 0))) } }
      case 'set_led':
        return { ...state, actuators: { ...a,
          led: { ...(LED_COLORS[args?.color] ?? LED_COLORS.off) } } }
      case 'buzzer':
        return { ...state, buzzerUntil: now + BUZZER_WINDOW_MS }
      case 'display_text':
        return { ...state, actuators: { ...a,
          oled: [String(args?.line1 ?? '').slice(0, 16),
                 String(args?.line2 ?? '').slice(0, 16)] } }
      default:
        return state
    }
  }
  return state
}

/** Seed state from GET /status (actuators may be null pre-first-snapshot). */
export function applyStatus(state: DeviceState, status: any): DeviceState {
  return {
    ...state,
    online: !!status?.device?.online,
    sensors: { ...state.sensors, ...(status?.sensors ?? {}) },
    actuators: status?.actuators
      ? { ...state.actuators, ...status.actuators }
      : state.actuators,
  }
}
