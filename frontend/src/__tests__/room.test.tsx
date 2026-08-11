import { vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RoomView from '../views/RoomView'
import Gauge from '../components/Gauge'
import Sparkline from '../components/Sparkline'

// mock the API + WS hooks
vi.mock('../lib/api', () => ({
  api: {
    getStatus: () => Promise.resolve({
      device: { online: true },
      sensors: { temp_c: 24.5, humidity_pct: 41, light: 612, motion: 0 },
      last_seen: new Date().toISOString(),
    }),
    simScenario: vi.fn(), simEvent: vi.fn(),
  },
}))
vi.mock('../lib/ws', () => ({ useGatewayWS: () => ({ connected: true }) }))

test('renders sensor gauges and scenario controls', async () => {
  render(<RoomView />)
  expect(await screen.findByText(/24\.5/)).toBeTruthy()
  expect(screen.getByText(/Temperature/i)).toBeTruthy()
  expect(screen.getByText(/Humidity/i)).toBeTruthy()
  expect(screen.getByText(/Light/i)).toBeTruthy()
  expect(screen.getByRole('button', { name: /heat spike/i })).toBeTruthy()
  expect(screen.getByRole('button', { name: /motion/i })).toBeTruthy()
})

test('gauge value arc at 50% ends at top center (upper semicircle)', () => {
  const { container } = render(
    <Gauge label="t" value={20} min={0} max={40} unit="°C" color="red" />)
  const paths = container.querySelectorAll('path')
  expect(paths.length).toBe(2)
  const d = paths[1].getAttribute('d') ?? ''
  expect(d).toContain('50 10')
  expect(d).not.toContain('50 90')
})

test('sparkline renders 10%-opacity area fill under the line', () => {
  const { container } = render(<Sparkline data={[1, 2, 3]} color="red" />)
  const poly = container.querySelector('polygon')
  expect(poly).toBeTruthy()
  expect(poly?.getAttribute('fill-opacity')).toBe('0.1')
})
