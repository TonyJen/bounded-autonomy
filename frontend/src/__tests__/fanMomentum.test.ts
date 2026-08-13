import { stepFan, FAN_FULL_DPS } from '../lib/useFanMomentum'

test('spin-up ramps velocity linearly toward full speed', () => {
  // 540 dps over 1000ms → 270 dps after 500ms
  const m = stepFan({ angle: 0, velocity: 0 }, 500, true)
  expect(m.velocity).toBe(270)
  expect(m.angle).toBeCloseTo(135) // 270 dps * 0.5s
})

test('velocity clamps at full speed', () => {
  const m = stepFan({ angle: 0, velocity: 530 }, 500, true)
  expect(m.velocity).toBe(FAN_FULL_DPS)
})

test('coast-down takes 2000ms to stop', () => {
  const m = stepFan({ angle: 0, velocity: FAN_FULL_DPS }, 1000, false)
  expect(m.velocity).toBe(270)
  const stopped = stepFan(m, 1000, false)
  expect(stopped.velocity).toBe(0)
})

test('angle wraps at 360', () => {
  // 350° + 540 dps * 0.1s = 350 + 54 = 404 → 44
  const m = stepFan({ angle: 350, velocity: FAN_FULL_DPS }, 100, true)
  expect(m.angle).toBeGreaterThanOrEqual(0)
  expect(m.angle).toBeLessThan(360)
  expect(m.angle).toBeCloseTo(44)
})
