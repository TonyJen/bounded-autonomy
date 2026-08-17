import { appendSnapshot, SensorHistory } from '../lib/useSensorHistory'

const empty: SensorHistory = { t: [], h: [], l: [] }

test('appendSnapshot appends temp/humidity/light', () => {
  const h = appendSnapshot(empty, { temp_c: 24.5, humidity_pct: 41, light: 612 })
  expect(h).toEqual({ t: [24.5], h: [41], l: [612] })
})

test('null temp skips the whole sample (matches RoomView rule)', () => {
  const h = appendSnapshot(empty, { temp_c: null, humidity_pct: 41, light: 612 })
  expect(h).toBe(empty)
})

test('null humidity/light carry the previous value (no 0-dip on partial failure)', () => {
  let h = appendSnapshot(empty, { temp_c: 22, humidity_pct: 41, light: 612 })
  h = appendSnapshot(h, { temp_c: 22.1, humidity_pct: null, light: null })
  expect(h).toEqual({ t: [22, 22.1], h: [41, 41], l: [612, 612] })
})

test('null humidity/light with no history fall back to 0', () => {
  const h = appendSnapshot(empty, { temp_c: 22, humidity_pct: null, light: null })
  expect(h).toEqual({ t: [22], h: [0], l: [0] })
})

test('buffer is capped at 60 entries', () => {
  let h = empty
  for (let i = 0; i < 70; i++) {
    h = appendSnapshot(h, { temp_c: i, humidity_pct: i, light: i })
  }
  expect(h.t).toHaveLength(60)
  expect(h.t[0]).toBe(10)
  expect(h.t[59]).toBe(69)
})
