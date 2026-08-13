/** Pure mappings from sensor values to 0..1 visual fractions (null = failed
 * read, distinct from 0) and colors. Used by DeviceIllustration widgets. */

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v))
}

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t)
}

function lerpColor(c1: number[], c2: number[], t: number): string {
  return `rgb(${lerp(c1[0], c2[0], t)},${lerp(c1[1], c2[1], t)},${lerp(c1[2], c2[2], t)})`
}

const BLUE = [59, 130, 246], AMBER = [255, 191, 0], RED = [239, 68, 68]

export function tempFraction(t: number | null): number | null {
  if (t == null) return null
  return clamp((t - 10) / 35)
}

export function tempColor(frac: number): string {
  return frac < 0.5 ? lerpColor(BLUE, AMBER, frac * 2)
                    : lerpColor(AMBER, RED, (frac - 0.5) * 2)
}

export function lightFraction(l: number | null): number | null {
  if (l == null) return null
  return Math.sqrt(clamp(l / 4095))
}

export function humidityFraction(h: number | null): number | null {
  if (h == null) return null
  return clamp(h / 100)
}
