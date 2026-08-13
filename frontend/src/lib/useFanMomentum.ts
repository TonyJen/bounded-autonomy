import { useEffect, useRef, useState } from 'react'

export type FanMotion = { angle: number; velocity: number }

export const FAN_FULL_DPS = 540 // degrees per second at full speed
const RAMP_UP_MS = 1000
const COAST_DOWN_MS = 2000

/** One physics step: velocity ramps linearly toward the target (full speed
 *  when on, 0 when off); angle accumulates and wraps at 360. */
export function stepFan(m: FanMotion, dtMs: number, on: boolean): FanMotion {
  const target = on ? FAN_FULL_DPS : 0
  const dv = (FAN_FULL_DPS / (on ? RAMP_UP_MS : COAST_DOWN_MS)) * dtMs
  const velocity = m.velocity < target
    ? Math.min(m.velocity + dv, target)
    : Math.max(m.velocity - dv, target)
  const angle = (m.angle + (velocity * dtMs) / 1000) % 360
  return { angle, velocity }
}

/** Rotor angle with momentum: spins up over ~1s, coasts down over ~2s.
 *  The rAF loop runs only while there is motion to animate. */
export function useFanMomentum(on: boolean): number {
  const [angle, setAngle] = useState(0)
  const motion = useRef<FanMotion>({ angle: 0, velocity: 0 })

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(now - last, 100) // tab-switch guard
      last = now
      motion.current = stepFan(motion.current, dt, on)
      setAngle(motion.current.angle)
      if (on || motion.current.velocity > 0.5) {
        raf = requestAnimationFrame(tick)
      }
    }
    if (on || motion.current.velocity > 0.5) {
      raf = requestAnimationFrame(tick)
    }
    return () => cancelAnimationFrame(raf)
  }, [on])

  return angle
}
