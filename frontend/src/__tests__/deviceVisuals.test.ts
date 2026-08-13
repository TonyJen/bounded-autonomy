import {
  tempFraction, tempColor, lightFraction, humidityFraction,
} from '../lib/deviceVisuals'

test('tempFraction maps 10-45C to 0..1 and clamps', () => {
  expect(tempFraction(10)).toBe(0)
  expect(tempFraction(45)).toBe(1)
  expect(tempFraction(27.5)).toBeCloseTo(0.5)
  expect(tempFraction(-5)).toBe(0)
  expect(tempFraction(99)).toBe(1)
})

test('tempFraction returns null for null (failed read ≠ 0)', () => {
  expect(tempFraction(null)).toBeNull()
})

test('tempColor is blue at 0, amber at 0.5, red at 1', () => {
  expect(tempColor(0)).toBe('rgb(59,130,246)')
  expect(tempColor(0.5)).toBe('rgb(255,191,0)')
  expect(tempColor(1)).toBe('rgb(239,68,68)')
})

test('lightFraction uses sqrt scale over 0-4095', () => {
  expect(lightFraction(0)).toBe(0)
  expect(lightFraction(4095)).toBe(1)
  // sqrt(1023.75/4095) = 0.5 → quarter-scale input maps to half
  expect(lightFraction(1023.75)).toBeCloseTo(0.5)
  expect(lightFraction(5000)).toBe(1)
  expect(lightFraction(null)).toBeNull()
})

test('humidityFraction maps 0-100 and nulls', () => {
  expect(humidityFraction(0)).toBe(0)
  expect(humidityFraction(100)).toBe(1)
  expect(humidityFraction(41)).toBeCloseTo(0.41)
  expect(humidityFraction(null)).toBeNull()
})
